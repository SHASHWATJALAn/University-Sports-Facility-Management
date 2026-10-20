import os
from flask import Flask, render_template, request, redirect, url_for, flash
from db import get_connection
from mysql.connector import IntegrityError

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "sports-facility-local-key")

@app.route("/")
def dashboard():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT COUNT(*) AS total FROM Student")
        total_students = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM Sport")
        total_sports = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM Venue")
        total_venues = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM Booking")
        total_bookings = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM Payment")
        total_payments = cursor.fetchone()["total"]

        return render_template(
            "index.html",
            total_students=total_students,
            total_sports=total_sports,
            total_venues=total_venues,
            total_bookings=total_bookings,
            total_payments=total_payments
        )
    finally:
        cursor.close()
        connection.close()


# READ: Display all students
@app.route("/students")
def students():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT StudentID, FirstName, LastName, DOB, Email,
                   Department, StudyYear
            FROM Student
            ORDER BY StudentID
        """)
        student_list = cursor.fetchall()

        return render_template("students.html", students=student_list)
    finally:
        cursor.close()
        connection.close()


# CREATE: Add a student
@app.route("/students/add", methods=["GET", "POST"])
def add_student():
    if request.method == "POST":
        student_id = request.form["StudentID"].strip()
        first_name = request.form["FirstName"].strip()
        last_name = request.form["LastName"].strip()
        dob = request.form["DOB"]
        email = request.form["Email"].strip()
        department = request.form.get("Department", "").strip() or None
        study_year = request.form.get("StudyYear", "").strip() or None

        connection = get_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("""
                INSERT INTO Student
                (StudentID, FirstName, LastName, DOB, Email, Department, StudyYear)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                student_id, first_name, last_name, dob, email,
                department, study_year
            ))
            connection.commit()
            flash("Student added successfully.", "success")
            return redirect(url_for("students"))

        except IntegrityError as error:
            connection.rollback()
            if error.errno == 1062:
                flash("Student ID or email already exists.", "danger")
            else:
                flash("Could not add student because of a database constraint.", "danger")

        finally:
            cursor.close()
            connection.close()

    return render_template("student_form.html", student=None, action="Add")


# UPDATE: Edit a student
@app.route("/students/edit/<student_id>", methods=["GET", "POST"])
def edit_student(student_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM Student WHERE StudentID = %s",
            (student_id,)
        )
        student = cursor.fetchone()

        if student is None:
            flash("Student not found.", "danger")
            return redirect(url_for("students"))

        if request.method == "POST":
            first_name = request.form["FirstName"].strip()
            last_name = request.form["LastName"].strip()
            dob = request.form["DOB"]
            email = request.form["Email"].strip()
            department = request.form.get("Department", "").strip() or None
            study_year = request.form.get("StudyYear", "").strip() or None

            cursor.execute("""
                UPDATE Student
                SET FirstName = %s, LastName = %s, DOB = %s, Email = %s,
                    Department = %s, StudyYear = %s
                WHERE StudentID = %s
            """, (
                first_name, last_name, dob, email,
                department, study_year, student_id
            ))
            connection.commit()
            flash("Student updated successfully.", "success")
            return redirect(url_for("students"))

        return render_template("student_form.html", student=student, action="Edit")

    except IntegrityError as error:
        connection.rollback()
        if error.errno == 1062:
            flash("That email address is already registered to another student.", "danger")
        else:
            flash("Could not update student because of a database constraint.", "danger")
        return redirect(url_for("students"))

    finally:
        cursor.close()
        connection.close()


# DELETE: Remove a student
@app.route("/students/delete/<student_id>", methods=["POST"])
def delete_student(student_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "DELETE FROM Student WHERE StudentID = %s",
            (student_id,)
        )
        connection.commit()

        if cursor.rowcount:
            flash("Student deleted successfully.", "success")
        else:
            flash("Student not found.", "warning")

    except IntegrityError:
        connection.rollback()
        flash(
            "Cannot delete this student because related records exist. "
            "Preserve the related booking or other records first.",
            "danger"
        )

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("students"))

# =========================
# SPORT MANAGEMENT
# =========================

# READ: Display all sports
@app.route("/sports")
def sports():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT SportID, SportName, Category
            FROM Sport
            ORDER BY SportID
        """)
        sport_list = cursor.fetchall()
        return render_template("sports.html", sports=sport_list)

    finally:
        cursor.close()
        connection.close()


# CREATE: Add a sport
@app.route("/sports/add", methods=["GET", "POST"])
def add_sport():
    if request.method == "POST":
        sport_id = request.form["SportID"].strip()
        sport_name = request.form["SportName"].strip()
        category = request.form["Category"].strip()

        connection = get_connection()
        cursor = connection.cursor()

        try:
            cursor.execute("""
                INSERT INTO Sport (SportID, SportName, Category)
                VALUES (%s, %s, %s)
            """, (sport_id, sport_name, category))

            connection.commit()
            flash("Sport added successfully.", "success")
            return redirect(url_for("sports"))

        except IntegrityError as error:
            connection.rollback()

            if error.errno == 1062:
                flash("Sport ID or sport name already exists.", "danger")
            else:
                flash("Could not add sport due to a database constraint.", "danger")

        finally:
            cursor.close()
            connection.close()

    return render_template("sport_form.html", sport=None, action="Add")


# UPDATE: Edit a sport
@app.route("/sports/edit/<sport_id>", methods=["GET", "POST"])
def edit_sport(sport_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM Sport WHERE SportID = %s",
            (sport_id,)
        )
        sport = cursor.fetchone()

        if sport is None:
            flash("Sport not found.", "danger")
            return redirect(url_for("sports"))

        if request.method == "POST":
            sport_name = request.form["SportName"].strip()
            category = request.form["Category"].strip()

            cursor.execute("""
                UPDATE Sport
                SET SportName = %s, Category = %s
                WHERE SportID = %s
            """, (sport_name, category, sport_id))

            connection.commit()
            flash("Sport updated successfully.", "success")
            return redirect(url_for("sports"))

        return render_template(
            "sport_form.html", sport=sport, action="Edit"
        )

    except IntegrityError as error:
        connection.rollback()

        if error.errno == 1062:
            flash("That sport name is already in use.", "danger")
        else:
            flash("Could not update sport due to a database constraint.", "danger")

        return redirect(url_for("sports"))

    finally:
        cursor.close()
        connection.close()


# DELETE: Remove a sport
@app.route("/sports/delete/<sport_id>", methods=["POST"])
def delete_sport(sport_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "DELETE FROM Sport WHERE SportID = %s",
            (sport_id,)
        )
        connection.commit()

        if cursor.rowcount:
            flash("Sport deleted successfully.", "success")
        else:
            flash("Sport not found.", "warning")

    except IntegrityError:
        connection.rollback()
        flash(
            "This sport cannot be deleted because another record references it.",
            "danger"
        )

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("sports"))


# =========================
# COACH MANAGEMENT
# =========================

# READ: Display all coaches
@app.route("/coaches")
def coaches():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT C.CoachID, C.CoachName, C.ExperienceYears,
                   C.Phone, C.SportID, S.SportName
            FROM Coach C
            JOIN Sport S ON C.SportID = S.SportID
            ORDER BY C.CoachID
        """)
        coach_list = cursor.fetchall()

        return render_template("coaches.html", coaches=coach_list)

    finally:
        cursor.close()
        connection.close()


# CREATE: Add a coach
@app.route("/coaches/add", methods=["GET", "POST"])
def add_coach():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        if request.method == "POST":
            coach_id = request.form["CoachID"].strip()
            coach_name = request.form["CoachName"].strip()
            experience = request.form["ExperienceYears"]
            phone = request.form.get("Phone", "").strip() or None
            sport_id = request.form["SportID"]

            cursor.execute("""
                INSERT INTO Coach
                (CoachID, CoachName, ExperienceYears, Phone, SportID)
                VALUES (%s, %s, %s, %s, %s)
            """, (coach_id, coach_name, experience, phone, sport_id))

            connection.commit()
            flash("Coach added successfully.", "success")
            return redirect(url_for("coaches"))

        cursor.execute("SELECT SportID, SportName FROM Sport ORDER BY SportName")
        sport_list = cursor.fetchall()

        return render_template(
            "coach_form.html",
            coach=None,
            sports=sport_list,
            action="Add"
        )

    except IntegrityError as error:
        connection.rollback()

        if error.errno == 1062:
            flash("That Coach ID already exists.", "danger")
        else:
            flash("Could not add coach. Check the entered details.", "danger")

        cursor.execute("SELECT SportID, SportName FROM Sport ORDER BY SportName")
        sport_list = cursor.fetchall()

        return render_template(
            "coach_form.html",
            coach=request.form,
            sports=sport_list,
            action="Add"
        )

    finally:
        cursor.close()
        connection.close()


# UPDATE: Edit a coach
@app.route("/coaches/edit/<coach_id>", methods=["GET", "POST"])
def edit_coach(coach_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM Coach WHERE CoachID = %s",
            (coach_id,)
        )
        coach = cursor.fetchone()

        if coach is None:
            flash("Coach not found.", "danger")
            return redirect(url_for("coaches"))

        if request.method == "POST":
            coach_name = request.form["CoachName"].strip()
            experience = request.form["ExperienceYears"]
            phone = request.form.get("Phone", "").strip() or None
            sport_id = request.form["SportID"]

            cursor.execute("""
                UPDATE Coach
                SET CoachName = %s,
                    ExperienceYears = %s,
                    Phone = %s,
                    SportID = %s
                WHERE CoachID = %s
            """, (coach_name, experience, phone, sport_id, coach_id))

            connection.commit()
            flash("Coach updated successfully.", "success")
            return redirect(url_for("coaches"))

        cursor.execute("SELECT SportID, SportName FROM Sport ORDER BY SportName")
        sport_list = cursor.fetchall()

        return render_template(
            "coach_form.html",
            coach=coach,
            sports=sport_list,
            action="Edit"
        )

    except IntegrityError:
        connection.rollback()
        flash("Could not update coach. Check the entered details.", "danger")
        return redirect(url_for("coaches"))

    finally:
        cursor.close()
        connection.close()


# DELETE: Remove a coach
@app.route("/coaches/delete/<coach_id>", methods=["POST"])
def delete_coach(coach_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "DELETE FROM Coach WHERE CoachID = %s",
            (coach_id,)
        )
        connection.commit()

        if cursor.rowcount:
            flash("Coach deleted successfully.", "success")
        else:
            flash("Coach not found.", "warning")

    except IntegrityError:
        connection.rollback()
        flash(
            "This coach cannot be deleted because related records reference it.",
            "danger"
        )

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("coaches"))

# =========================
# VENUE MANAGEMENT
# =========================

# READ: Display all venues
@app.route("/venues")
def venues():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT V.VenueID, V.VenueName, V.Location,
                   V.Capacity, V.SportID, S.SportName
            FROM Venue V
            JOIN Sport S ON V.SportID = S.SportID
            ORDER BY V.VenueID
        """)
        venue_list = cursor.fetchall()

        return render_template("venues.html", venues=venue_list)

    finally:
        cursor.close()
        connection.close()


# CREATE: Add a venue
@app.route("/venues/add", methods=["GET", "POST"])
def add_venue():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        if request.method == "POST":
            venue_id = request.form["VenueID"].strip()
            venue_name = request.form["VenueName"].strip()
            location = request.form["Location"].strip()
            capacity = request.form["Capacity"]
            sport_id = request.form["SportID"]

            cursor.execute("""
                INSERT INTO Venue
                (VenueID, VenueName, Location, Capacity, SportID)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                venue_id, venue_name, location, capacity, sport_id
            ))

            connection.commit()
            flash("Venue added successfully.", "success")
            return redirect(url_for("venues"))

        cursor.execute("""
            SELECT SportID, SportName
            FROM Sport
            ORDER BY SportName
        """)
        sport_list = cursor.fetchall()

        return render_template(
            "venue_form.html",
            venue=None,
            sports=sport_list,
            action="Add"
        )

    except IntegrityError as error:
        connection.rollback()

        if error.errno == 1062:
            flash("That Venue ID already exists.", "danger")
        else:
            flash("Could not add venue. Check the entered details.", "danger")

        cursor.execute("""
            SELECT SportID, SportName
            FROM Sport
            ORDER BY SportName
        """)
        sport_list = cursor.fetchall()

        return render_template(
            "venue_form.html",
            venue=request.form,
            sports=sport_list,
            action="Add"
        )

    finally:
        cursor.close()
        connection.close()


# UPDATE: Edit a venue
@app.route("/venues/edit/<venue_id>", methods=["GET", "POST"])
def edit_venue(venue_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM Venue WHERE VenueID = %s",
            (venue_id,)
        )
        venue = cursor.fetchone()

        if venue is None:
            flash("Venue not found.", "danger")
            return redirect(url_for("venues"))

        if request.method == "POST":
            venue_name = request.form["VenueName"].strip()
            location = request.form["Location"].strip()
            capacity = request.form["Capacity"]
            sport_id = request.form["SportID"]

            cursor.execute("""
                UPDATE Venue
                SET VenueName = %s,
                    Location = %s,
                    Capacity = %s,
                    SportID = %s
                WHERE VenueID = %s
            """, (
                venue_name, location, capacity, sport_id, venue_id
            ))

            connection.commit()
            flash("Venue updated successfully.", "success")
            return redirect(url_for("venues"))

        cursor.execute("""
            SELECT SportID, SportName
            FROM Sport
            ORDER BY SportName
        """)
        sport_list = cursor.fetchall()

        return render_template(
            "venue_form.html",
            venue=venue,
            sports=sport_list,
            action="Edit"
        )

    except IntegrityError:
        connection.rollback()
        flash("Could not update venue. Check the entered details.", "danger")
        return redirect(url_for("venues"))

    finally:
        cursor.close()
        connection.close()


# DELETE: Remove a venue
@app.route("/venues/delete/<venue_id>", methods=["POST"])
def delete_venue(venue_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "DELETE FROM Venue WHERE VenueID = %s",
            (venue_id,)
        )
        connection.commit()

        if cursor.rowcount:
            flash("Venue deleted successfully.", "success")
        else:
            flash("Venue not found.", "warning")

    except IntegrityError:
        connection.rollback()
        flash(
            "This venue cannot be deleted because related records reference it.",
            "danger"
        )

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("venues"))

# =========================
# EQUIPMENT MANAGEMENT
# =========================

# READ: Display all equipment
@app.route("/equipment")
def equipment():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT E.EquipmentID, E.EquipmentName,
                   E.QuantityAvailable, E.PurchaseDate,
                   E.SportID, S.SportName
            FROM Equipment E
            JOIN Sport S ON E.SportID = S.SportID
            ORDER BY E.EquipmentID
        """)

        equipment_list = cursor.fetchall()

        return render_template(
            "equipment.html",
            equipment_list=equipment_list
        )

    finally:
        cursor.close()
        connection.close()


# CREATE: Add equipment
@app.route("/equipment/add", methods=["GET", "POST"])
def add_equipment():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        if request.method == "POST":
            equipment_id = request.form["EquipmentID"].strip()
            equipment_name = request.form["EquipmentName"].strip()
            quantity = request.form["QuantityAvailable"]
            purchase_date = request.form.get("PurchaseDate") or None
            sport_id = request.form["SportID"]

            cursor.execute("""
                INSERT INTO Equipment
                (EquipmentID, EquipmentName, QuantityAvailable,
                 PurchaseDate, SportID)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                equipment_id, equipment_name, quantity,
                purchase_date, sport_id
            ))

            connection.commit()
            flash("Equipment added successfully.", "success")
            return redirect(url_for("equipment"))

        cursor.execute("""
            SELECT SportID, SportName
            FROM Sport
            ORDER BY SportName
        """)
        sport_list = cursor.fetchall()

        return render_template(
            "equipment_form.html",
            item=None,
            sports=sport_list,
            action="Add"
        )

    except IntegrityError as error:
        connection.rollback()

        if error.errno == 1062:
            flash("That Equipment ID already exists.", "danger")
        else:
            flash("Could not add equipment. Check the entered details.", "danger")

        cursor.execute("""
            SELECT SportID, SportName
            FROM Sport
            ORDER BY SportName
        """)
        sport_list = cursor.fetchall()

        return render_template(
            "equipment_form.html",
            item=request.form,
            sports=sport_list,
            action="Add"
        )

    finally:
        cursor.close()
        connection.close()


# UPDATE: Edit equipment
@app.route("/equipment/edit/<equipment_id>", methods=["GET", "POST"])
def edit_equipment(equipment_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM Equipment WHERE EquipmentID = %s",
            (equipment_id,)
        )
        item = cursor.fetchone()

        if item is None:
            flash("Equipment not found.", "danger")
            return redirect(url_for("equipment"))

        if request.method == "POST":
            equipment_name = request.form["EquipmentName"].strip()
            quantity = request.form["QuantityAvailable"]
            purchase_date = request.form.get("PurchaseDate") or None
            sport_id = request.form["SportID"]

            cursor.execute("""
                UPDATE Equipment
                SET EquipmentName = %s,
                    QuantityAvailable = %s,
                    PurchaseDate = %s,
                    SportID = %s
                WHERE EquipmentID = %s
            """, (
                equipment_name, quantity, purchase_date,
                sport_id, equipment_id
            ))

            connection.commit()
            flash("Equipment updated successfully.", "success")
            return redirect(url_for("equipment"))

        cursor.execute("""
            SELECT SportID, SportName
            FROM Sport
            ORDER BY SportName
        """)
        sport_list = cursor.fetchall()

        return render_template(
            "equipment_form.html",
            item=item,
            sports=sport_list,
            action="Edit"
        )

    except IntegrityError:
        connection.rollback()
        flash("Could not update equipment. Check the entered details.", "danger")
        return redirect(url_for("equipment"))

    finally:
        cursor.close()
        connection.close()


# DELETE: Remove equipment
@app.route("/equipment/delete/<equipment_id>", methods=["POST"])
def delete_equipment(equipment_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "DELETE FROM Equipment WHERE EquipmentID = %s",
            (equipment_id,)
        )
        connection.commit()

        if cursor.rowcount:
            flash("Equipment deleted successfully.", "success")
        else:
            flash("Equipment not found.", "warning")

    except IntegrityError:
        connection.rollback()
        flash(
            "This equipment cannot be deleted because related records reference it.",
            "danger"
        )

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("equipment"))

# =========================
# COACH CERTIFICATION MANAGEMENT
# =========================

# READ: Display all certifications
@app.route("/certifications")
def certifications():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT CC.CoachID, C.CoachName, CC.Certification
            FROM CoachCertification CC
            JOIN Coach C ON CC.CoachID = C.CoachID
            ORDER BY CC.CoachID, CC.Certification
        """)

        certification_list = cursor.fetchall()

        return render_template(
            "certifications.html",
            certifications=certification_list
        )

    finally:
        cursor.close()
        connection.close()


# CREATE: Add a certification
@app.route("/certifications/add", methods=["GET", "POST"])
def add_certification():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        if request.method == "POST":
            coach_id = request.form["CoachID"]
            certification = request.form["Certification"].strip()

            cursor.execute("""
                INSERT INTO CoachCertification (CoachID, Certification)
                VALUES (%s, %s)
            """, (coach_id, certification))

            connection.commit()
            flash("Certification added successfully.", "success")
            return redirect(url_for("certifications"))

        cursor.execute("""
            SELECT CoachID, CoachName
            FROM Coach
            ORDER BY CoachName
        """)
        coach_list = cursor.fetchall()

        return render_template(
            "certification_form.html",
            certification=None,
            coaches=coach_list,
            action="Add"
        )

    except IntegrityError as error:
        connection.rollback()

        if error.errno == 1062:
            flash(
                "This certification already exists for that coach.",
                "danger"
            )
        else:
            flash("Could not add certification. Check the entered details.", "danger")

        cursor.execute("""
            SELECT CoachID, CoachName
            FROM Coach
            ORDER BY CoachName
        """)
        coach_list = cursor.fetchall()

        return render_template(
            "certification_form.html",
            certification=request.form,
            coaches=coach_list,
            action="Add"
        )

    finally:
        cursor.close()
        connection.close()


# UPDATE: Edit a certification
@app.route(
    "/certifications/edit/<coach_id>/<path:old_certification>",
    methods=["GET", "POST"]
)
def edit_certification(coach_id, old_certification):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT CoachID, Certification
            FROM CoachCertification
            WHERE CoachID = %s AND Certification = %s
        """, (coach_id, old_certification))

        certification = cursor.fetchone()

        if certification is None:
            flash("Certification not found.", "danger")
            return redirect(url_for("certifications"))

        if request.method == "POST":
            new_certification = request.form["Certification"].strip()

            cursor.execute("""
                UPDATE CoachCertification
                SET Certification = %s
                WHERE CoachID = %s AND Certification = %s
            """, (new_certification, coach_id, old_certification))

            connection.commit()
            flash("Certification updated successfully.", "success")
            return redirect(url_for("certifications"))

        return render_template(
            "certification_form.html",
            certification=certification,
            coaches=[],
            action="Edit"
        )

    except IntegrityError as error:
        connection.rollback()

        if error.errno == 1062:
            flash(
                "That certification already exists for this coach.",
                "danger"
            )
        else:
            flash("Could not update certification.", "danger")

        return redirect(url_for("certifications"))

    finally:
        cursor.close()
        connection.close()


# DELETE: Remove a certification
@app.route(
    "/certifications/delete/<coach_id>/<path:certification>",
    methods=["POST"]
)
def delete_certification(coach_id, certification):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            DELETE FROM CoachCertification
            WHERE CoachID = %s AND Certification = %s
        """, (coach_id, certification))

        connection.commit()

        if cursor.rowcount:
            flash("Certification deleted successfully.", "success")
        else:
            flash("Certification not found.", "warning")

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("certifications"))


# =========================
# BOOKING MANAGEMENT
# =========================

from datetime import date, time
from mysql.connector import Error


ACTIVE_STATUSES = ("Pending", "Confirmed")
VALID_STATUSES = ("Pending", "Confirmed", "Cancelled", "Completed")


def get_booking_form_data(cursor):
    cursor.execute("""
        SELECT StudentID, FirstName, LastName
        FROM Student
        ORDER BY FirstName, LastName
    """)
    students_list = cursor.fetchall()

    cursor.execute("""
        SELECT SportID, SportName
        FROM Sport
        ORDER BY SportName
    """)
    sports_list = cursor.fetchall()

    cursor.execute("""
        SELECT VenueID, VenueName, SportID
        FROM Venue
        ORDER BY VenueName
    """)
    venues_list = cursor.fetchall()

    return students_list, sports_list, venues_list


def booking_conflicts(cursor, booking_date, start_time, end_time,
                      venue_id, exclude_booking_id=None):
    query = """
        SELECT BookingID
        FROM Booking
        WHERE BookingDate = %s
          AND VenueID = %s
          AND Status IN ('Pending', 'Confirmed')
          AND StartTime < %s
          AND EndTime > %s
    """
    params = [booking_date, venue_id, end_time, start_time]

    if exclude_booking_id is not None:
        query += " AND BookingID <> %s"
        params.append(exclude_booking_id)

    query += " LIMIT 1"
    cursor.execute(query, tuple(params))

    return cursor.fetchone() is not None


def render_booking_form(cursor, booking, action, error_message=None):
    students_list, sports_list, venues_list = get_booking_form_data(cursor)

    return render_template(
        "booking_form.html",
        booking=booking,
        students=students_list,
        sports=sports_list,
        venues=venues_list,
        statuses=VALID_STATUSES,
        action=action,
        error_message=error_message
    )


# READ: Display all bookings
@app.route("/bookings")
def bookings():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                B.BookingID,
                B.BookingDate,
                B.StartTime,
                B.EndTime,
                B.Status,
                B.StudentID,
                CONCAT(S.FirstName, ' ', S.LastName) AS StudentName,
                B.SportID,
                SP.SportName,
                B.VenueID,
                V.VenueName
            FROM Booking B
            JOIN Student S ON B.StudentID = S.StudentID
            JOIN Sport SP ON B.SportID = SP.SportID
            JOIN Venue V ON B.VenueID = V.VenueID
            ORDER BY B.BookingDate DESC, B.StartTime
        """)
        booking_list = cursor.fetchall()

        return render_template("bookings.html", bookings=booking_list)

    finally:
        cursor.close()
        connection.close()


# CREATE: Add a booking
@app.route("/bookings/add", methods=["GET", "POST"])
def add_booking():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        if request.method == "GET":
            return render_booking_form(cursor, None, "Add")
          
        booking_id = request.form["BookingID"].strip()
        booking_date = request.form["BookingDate"]
        start_time = request.form["StartTime"]
        end_time = request.form["EndTime"]
        status = request.form.get("Status", "Pending")
        student_id = request.form["StudentID"]
        sport_id = request.form["SportID"]
        venue_id = request.form["VenueID"]

        if status not in VALID_STATUSES:
            return render_booking_form(
                cursor, request.form, "Add", "Invalid booking status."
            )

        if start_time >= end_time:
            return render_booking_form(
                cursor, request.form, "Add",
                "End time must be later than start time."
            )

        if status in ACTIVE_STATUSES:
            # Lock the venue row so concurrent booking requests for this
            # venue serialize before checking availability.
            connection.start_transaction()

            cursor.execute(
                "SELECT VenueID FROM Venue WHERE VenueID = %s FOR UPDATE",
                (venue_id,)
            )
            venue = cursor.fetchone()

            if venue is None:
                connection.rollback()
                return render_booking_form(
                    cursor, request.form, "Add", "Selected venue does not exist."
                )

            cursor.execute(
                "SELECT SportID FROM Venue WHERE VenueID = %s",
                (venue_id,)
            )
            venue_sport = cursor.fetchone()["SportID"]

            if venue_sport != sport_id:
                connection.rollback()
                return render_booking_form(
                    cursor, request.form, "Add",
                    "The selected venue does not belong to that sport."
                )

            if booking_conflicts(
                cursor, booking_date, start_time, end_time, venue_id
            ):
                connection.rollback()
                return render_booking_form(
                    cursor, request.form, "Add",
                    "This venue already has an active booking during that time."
                )

        else:
            # A cancelled or completed booking does not block availability,
            # but its venue and sport must still match.
            cursor.execute(
                "SELECT SportID FROM Venue WHERE VenueID = %s",
                (venue_id,)
            )
            venue = cursor.fetchone()

            if venue is None or venue["SportID"] != sport_id:
                return render_booking_form(
                    cursor, request.form, "Add",
                    "Select a venue that belongs to the selected sport."
                )

        cursor.execute("""
            INSERT INTO Booking
            (BookingID, BookingDate, StartTime, EndTime, Status,
             StudentID, SportID, VenueID)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            booking_id, booking_date, start_time, end_time, status,
            student_id, sport_id, venue_id
        ))

        connection.commit()
        flash("Booking created successfully.", "success")
        return redirect(url_for("bookings"))

    except IntegrityError as error:
        connection.rollback()

        if error.errno == 1062:
            message = "That Booking ID already exists."
        else:
            message = "A database constraint prevented this booking."

        return render_booking_form(
            cursor, request.form, "Add", message
        )

    except (ValueError, TypeError):
        connection.rollback()
        return render_booking_form(
            cursor, request.form, "Add", "Invalid date, time, or numeric value."
        )

    except Error:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


# UPDATE: Edit a booking
@app.route("/bookings/edit/<booking_id>", methods=["GET", "POST"])
def edit_booking(booking_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM Booking WHERE BookingID = %s",
            (booking_id,)
        )
        booking = cursor.fetchone()
        connection.commit()

        if booking is None:
            flash("Booking not found.", "danger")
            return redirect(url_for("bookings"))

        if request.method == "GET":
            return render_booking_form(cursor, booking, "Edit")

        booking_date = request.form["BookingDate"]
        start_time = request.form["StartTime"]
        end_time = request.form["EndTime"]
        status = request.form["Status"]
        student_id = request.form["StudentID"]
        sport_id = request.form["SportID"]
        venue_id = request.form["VenueID"]

        if status not in VALID_STATUSES:
            return render_booking_form(
                cursor, request.form, "Edit", "Invalid booking status."
            )

        if start_time >= end_time:
            return render_booking_form(
                cursor, request.form, "Edit",
                "End time must be later than start time."
            )

        if status in ACTIVE_STATUSES:
            connection.start_transaction()

            cursor.execute(
                "SELECT VenueID FROM Venue WHERE VenueID = %s FOR UPDATE",
                (venue_id,)
            )
            venue = cursor.fetchone()

            if venue is None:
                connection.rollback()
                return render_booking_form(
                    cursor, request.form, "Edit", "Selected venue does not exist."
                )

            cursor.execute(
                "SELECT SportID FROM Venue WHERE VenueID = %s",
                (venue_id,)
            )
            venue_sport = cursor.fetchone()["SportID"]

            if venue_sport != sport_id:
                connection.rollback()
                return render_booking_form(
                    cursor, request.form, "Edit",
                    "The selected venue does not belong to that sport."
                )

            if booking_conflicts(
                cursor, booking_date, start_time, end_time,
                venue_id, exclude_booking_id=booking_id
            ):
                connection.rollback()
                return render_booking_form(
                    cursor, request.form, "Edit",
                    "This venue already has an active booking during that time."
                )

        else:
            cursor.execute(
                "SELECT SportID FROM Venue WHERE VenueID = %s",
                (venue_id,)
            )
            venue = cursor.fetchone()

            if venue is None or venue["SportID"] != sport_id:
                return render_booking_form(
                    cursor, request.form, "Edit",
                    "Select a venue that belongs to the selected sport."
                )

        cursor.execute("""
            UPDATE Booking
            SET BookingDate = %s,
                StartTime = %s,
                EndTime = %s,
                Status = %s,
                StudentID = %s,
                SportID = %s,
                VenueID = %s
            WHERE BookingID = %s
        """, (
            booking_date, start_time, end_time, status,
            student_id, sport_id, venue_id, booking_id
        ))

        connection.commit()
        flash("Booking updated successfully.", "success")
        return redirect(url_for("bookings"))

    except IntegrityError:
        connection.rollback()
        return render_booking_form(
            cursor, request.form, "Edit",
            "A database constraint prevented this update."
        )

    except (ValueError, TypeError):
        connection.rollback()
        return render_booking_form(
            cursor, request.form, "Edit", "Invalid date or time value."
        )

    except Error:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


# CANCEL: Preserve the booking record
@app.route("/bookings/cancel/<booking_id>", methods=["POST"])
def cancel_booking(booking_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE Booking
            SET Status = 'Cancelled'
            WHERE BookingID = %s
              AND Status IN ('Pending', 'Confirmed')
        """, (booking_id,))

        connection.commit()

        if cursor.rowcount:
            flash("Booking cancelled successfully.", "success")
        else:
            flash(
                "Booking was not found or is already cancelled/completed.",
                "warning"
            )

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("bookings"))


# =========================
# PAYMENT MANAGEMENT
# =========================

from decimal import Decimal, InvalidOperation
from datetime import date


# Display all payments
@app.route("/payments")
def payments():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                P.PaymentID,
                P.Amount,
                P.PaymentDate,
                P.PaymentMode,
                P.BookingID,
                B.BookingDate,
                B.StartTime,
                B.EndTime,
                B.Status AS BookingStatus,
                CONCAT(S.FirstName, ' ', S.LastName) AS StudentName,
                V.VenueName
            FROM Payment P
            JOIN Booking B ON P.BookingID = B.BookingID
            JOIN Student S ON B.StudentID = S.StudentID
            JOIN Venue V ON B.VenueID = V.VenueID
            ORDER BY P.PaymentDate DESC, P.PaymentID
        """)

        payment_list = cursor.fetchall()

        return render_template(
            "payments.html",
            payments=payment_list
        )

    finally:
        cursor.close()
        connection.close()


# Get bookings that do not already have a payment
def get_available_payment_bookings(cursor, current_payment_id=None):

    query = """
        SELECT
            B.BookingID,
            B.BookingDate,
            B.StartTime,
            B.EndTime,
            B.Status,
            CONCAT(S.FirstName, ' ', S.LastName) AS StudentName,
            V.VenueName
        FROM Booking B
        JOIN Student S ON B.StudentID = S.StudentID
        JOIN Venue V ON B.VenueID = V.VenueID
        WHERE B.Status <> 'Cancelled'
          AND NOT EXISTS (
            SELECT 1
            FROM Payment P
            WHERE P.BookingID = B.BookingID 
    """

    params = []

    if current_payment_id:
        query += " AND P.PaymentID <> %s"
        params.append(current_payment_id)

    query += """
        )
        ORDER BY B.BookingDate DESC, B.StartTime
    """

    cursor.execute(query, tuple(params))
    return cursor.fetchall()


# Add a payment
@app.route("/payments/add", methods=["GET", "POST"])
def add_payment():

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        bookings_list = get_available_payment_bookings(cursor)

        if request.method == "POST":

            payment_id = request.form.get("PaymentID", "").strip()
            amount_text = request.form.get("Amount", "").strip()
            payment_date = request.form.get("PaymentDate", "").strip()
            payment_mode = request.form.get("PaymentMode", "").strip()
            booking_id = request.form.get("BookingID", "").strip()

            if not all([
                payment_id,
                amount_text,
                payment_date,
                payment_mode,
                booking_id
            ]):
                flash("All fields are required.", "danger")

            else:
                try:
                    amount = Decimal(amount_text)

                    if (
                        not amount.is_finite()
                        or amount <= 0
                        or amount.as_tuple().exponent < -2
                    ):
                        raise InvalidOperation

                    date.fromisoformat(payment_date)

                    if len(payment_id) > 20:
                        raise ValueError("Payment ID is too long.")

                    if len(payment_mode) > 30:
                        raise ValueError("Payment mode is too long.")

                except (InvalidOperation, ValueError):
                    flash(
                        "Enter a valid positive amount, date, Payment ID, "
                        "and payment mode. Amounts may have at most "
                        "two decimal places.",
                        "danger"
                    )
                else:
                    # Check whether the selected booking exists and is active
                    cursor.execute(
                        "SELECT Status FROM Booking WHERE BookingID = %s",
                        (booking_id,)
                    )

                    booking = cursor.fetchone()

                    if booking is None:
                        flash(
                            "The selected booking does not exist.",
                            "danger"
                        )

                    elif booking["Status"] == "Cancelled":
                        flash(
                            "A payment cannot be added to a cancelled booking.",
                            "danger"
                        )

                    else:
                        try:
                            cursor.execute("""
                                INSERT INTO Payment
                                    (PaymentID, Amount, PaymentDate,
                                     PaymentMode, BookingID)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (
                                payment_id,
                                amount,
                                payment_date,
                                payment_mode,
                                booking_id
                            ))

                            connection.commit()

                            flash(
                                "Payment added successfully.",
                                "success"
                            )
                            return redirect(url_for("payments"))

                        except IntegrityError as error:
                            connection.rollback()

                            if error.errno == 1062:
                                flash(
                                    "Payment ID already exists or this booking "
                                    "already has a payment.",
                                    "danger"
                                )
                            elif error.errno == 1452:
                                flash(
                                    "The selected booking does not exist.",
                                    "danger"
                                )
                            else:
                                flash(
                                    "Could not add payment because of a "
                                    "database constraint.",
                                    "danger"
                                )

            # Refresh available bookings after validation/database errors
            bookings_list = get_available_payment_bookings(cursor)

            return render_template(
                "payment_form.html",
                payment=request.form,
                bookings=bookings_list,
                action="Add"
            )

        return render_template(
            "payment_form.html",
            payment=None,
            bookings=bookings_list,
            action="Add"
        )

    finally:
        cursor.close()
        connection.close()


# Edit a payment
@app.route("/payments/edit/<payment_id>", methods=["GET", "POST"])
def edit_payment(payment_id):

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM Payment WHERE PaymentID = %s",
            (payment_id,)
        )
        payment = cursor.fetchone()

        if payment is None:
            flash("Payment not found.", "danger")
            return redirect(url_for("payments"))

        if request.method == "POST":

            amount_text = request.form.get("Amount", "").strip()
            payment_date = request.form.get("PaymentDate", "").strip()
            payment_mode = request.form.get("PaymentMode", "").strip()
            booking_id = request.form.get("BookingID", "").strip()

            if not all([
                amount_text,
                payment_date,
                payment_mode,
                booking_id
            ]):
                flash("All fields are required.", "danger")

            else:
                try:
                    amount = Decimal(amount_text)

                    if (
                        not amount.is_finite()
                        or amount <= 0
                        or amount.as_tuple().exponent < -2
                    ):
                        raise InvalidOperation

                    date.fromisoformat(payment_date)

                    if len(payment_mode) > 30:
                        raise ValueError("Payment mode is too long.")

                except (InvalidOperation, ValueError):
                    flash(
                        "Enter a valid positive amount, date, and "
                        "payment mode. Amounts may have at most "
                        "two decimal places.",
                        "danger"
                    )
                else:
                    # Check whether the selected booking exists
                    cursor.execute(
                        "SELECT Status FROM Booking WHERE BookingID = %s",
                        (booking_id,)
                    )
                    selected_booking = cursor.fetchone()

                    if selected_booking is None:
                        flash(
                            "The selected booking does not exist.",
                            "danger"
                        )

                    elif (
                        selected_booking["Status"] == "Cancelled"
                        and str(booking_id) != str(payment["BookingID"])
                    ):
                        flash(
                            "A payment cannot be reassigned to a cancelled booking.",
                            "danger"
                        )

                    else:
                        try:
                            cursor.execute("""
                                UPDATE Payment
                                SET Amount = %s,
                                    PaymentDate = %s,
                                    PaymentMode = %s,
                                    BookingID = %s
                                WHERE PaymentID = %s
                            """, (
                                amount,
                                payment_date,
                                payment_mode,
                                booking_id,
                                payment_id
                            ))

                            connection.commit()

                            flash(
                                "Payment updated successfully.",
                                "success"
                            )
                            return redirect(url_for("payments"))

                        except IntegrityError as error:
                            connection.rollback()

                            if error.errno == 1062:
                                flash(
                                    "Another payment already uses this booking.",
                                    "danger"
                                )
                            elif error.errno == 1452:
                                flash(
                                    "The selected booking does not exist.",
                                    "danger"
                                )
                            else:
                                flash(
                                    "Could not update payment because of a "
                                    "database constraint.",
                                    "danger"
                                )

            # Preserve entered values after an error
            payment.update(request.form)

        bookings_list = get_available_payment_bookings(
            cursor,
            current_payment_id=payment_id
        )

        return render_template(
            "payment_form.html",
            payment=payment,
            bookings=bookings_list,
            action="Edit"
        )

    finally:
        cursor.close()
        connection.close()


# Delete a payment without deleting its booking
@app.route("/payments/delete/<payment_id>", methods=["POST"])
def delete_payment(payment_id):

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "DELETE FROM Payment WHERE PaymentID = %s",
            (payment_id,)
        )

        connection.commit()

        if cursor.rowcount:
            flash(
                "Payment deleted successfully. The booking remains intact.",
                "success"
            )
        else:
            flash("Payment not found.", "warning")

    except IntegrityError:
        connection.rollback()
        flash(
            "The payment could not be deleted because of a database constraint.",
            "danger"
        )

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("payments"))








if __name__ == "__main__":
    app.run(debug=True)


