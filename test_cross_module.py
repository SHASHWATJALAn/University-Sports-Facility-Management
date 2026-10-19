"""
Cross-module integration tests for SportsFacilityPython.

Run:
    .venv\Scripts\python.exe test_cross_module.py

Uses Flask's test client; no separate server is required.
Creates uniquely identified test records and deletes only those records.
"""

from datetime import date, timedelta
from uuid import uuid4

from app import app
from db import get_connection


def report(results, name, passed, detail=""):
    results.append((name, bool(passed), detail))
    print(f"{name:<48} {'PASS' if passed else 'FAIL'}" +
          (f" — {detail}" if detail else ""))


def query_one(sql, params=()):
    """Use a fresh DB connection so route commits are visible immediately."""
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql, params)
        row = cursor.fetchone()
        cursor.close()
        return row
    finally:
        connection.close()


def query_all(sql, params=()):
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()
        return rows
    finally:
        connection.close()


def cleanup(student_id, booking_id, payment_id):
    """Delete only records bearing this run's generated IDs, child first."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM Payment WHERE PaymentID = %s", (payment_id,))
        cursor.execute("DELETE FROM Booking WHERE BookingID = %s", (booking_id,))
        cursor.execute("DELETE FROM StudentPhone WHERE StudentID = %s", (student_id,))
        cursor.execute("DELETE FROM Student WHERE StudentID = %s", (student_id,))
        connection.commit()
        cursor.close()
    finally:
        connection.close()

    left = query_one("""
        SELECT
          (SELECT COUNT(*) FROM Payment WHERE PaymentID = %s) AS payments_left,
          (SELECT COUNT(*) FROM Booking WHERE BookingID = %s) AS bookings_left,
          (SELECT COUNT(*) FROM Student WHERE StudentID = %s) AS students_left
    """, (payment_id, booking_id, student_id))
    return (
        left["payments_left"] == 0
        and left["bookings_left"] == 0
        and left["students_left"] == 0,
        left,
    )


def main():
    app.config["TESTING"] = True
    client = app.test_client()
    token = uuid4().hex[:8].upper()

    student_id = f"ZT{token}"
    email = f"zt{token.lower()}@example.test"
    booking_id = f"ZB{token}"
    payment_id = f"ZP{token}"

    results = []
    print("\n" + "=" * 84)
    print("AUTOMATED CROSS-MODULE INTEGRATION TESTS")
    print("Student Management -> Booking Management -> Payment Management")
    print("=" * 84)

    try:
        venue = query_one("""
            SELECT VenueID, SportID FROM Venue ORDER BY VenueID LIMIT 1
        """)
        report(results, "Fixture: venue/sport pair exists", venue is not None)
        if venue is None:
            return

        chosen_date = None
        for offset in range(30, 395):
            candidate = date.today() + timedelta(days=offset)
            conflict = query_one("""
                SELECT COUNT(*) AS n FROM Booking
                WHERE VenueID = %s AND BookingDate = %s
                  AND Status IN ('Pending', 'Confirmed')
            """, (venue["VenueID"], candidate))
            if conflict["n"] == 0:
                chosen_date = candidate
                break

        report(results, "Fixture: free future date", chosen_date is not None,
               chosen_date.isoformat() if chosen_date else "No free date in next year")
        if chosen_date is None:
            return

        # IT1: Student route returns a redirect on success; independently
        # verify committed data using a new DB connection.
        response = client.post("/students/add", data={
            "StudentID": student_id,
            "FirstName": "Integration",
            "LastName": "Test",
            "DOB": "2004-01-15",
            "Email": email,
            "Department": "CSE",
            "StudyYear": "2",
        }, follow_redirects=False)
        student = query_one(
            "SELECT StudentID FROM Student WHERE StudentID = %s", (student_id,)
        )
        report(results, "IT1 Create student through Student Management",
               response.status_code == 302 and student is not None,
               f"HTTP {response.status_code}; DB record "
               f"{'found' if student else 'not found'}")

        response = client.get("/bookings/add")
        student_visible = (
            response.status_code == 200 and student_id.encode() in response.data
        )
        report(results, "IT2 Student appears in Booking form", student_visible,
               f"HTTP {response.status_code}")

        if student is not None:
            # BookingID is REQUIRED by the app route; include it in the POST.
            response = client.post("/bookings/add", data={
                "BookingID": booking_id,
                "BookingDate": chosen_date.isoformat(),
                "StartTime": "10:00",
                "EndTime": "11:00",
                "Status": "Pending",
                "StudentID": student_id,
                "SportID": str(venue["SportID"]),
                "VenueID": str(venue["VenueID"]),
            }, follow_redirects=False)

            booking = query_one("""
                SELECT BookingID, StudentID, SportID, VenueID
                FROM Booking WHERE BookingID = %s
            """, (booking_id,))
            report(results, "IT3 Create booking for new student",
                   response.status_code == 302 and booking is not None,
                   f"HTTP {response.status_code}; DB record "
                   f"{'found' if booking else 'not found'}")

            report(results, "IT4 Booking stores correct StudentID",
                   booking is not None and str(booking["StudentID"]) == student_id,
                   f"StudentID={booking['StudentID'] if booking else 'not found'}")

            if booking is not None:
                response = client.get("/payments/add")
                booking_visible = (
                    response.status_code == 200
                    and booking_id.encode() in response.data
                )
                report(results, "IT5 Booking appears in Payment form",
                       booking_visible, f"HTTP {response.status_code}")

                response = client.post("/payments/add", data={
                    "PaymentID": payment_id,
                    "Amount": "125.00",
                    "PaymentDate": date.today().isoformat(),
                    "PaymentMode": "Test",
                    "BookingID": booking_id,
                }, follow_redirects=False)
                payment = query_one("""
                    SELECT PaymentID, BookingID, Amount
                    FROM Payment WHERE PaymentID = %s
                """, (payment_id,))
                report(results, "IT6 Create payment for test booking",
                       response.status_code == 302 and payment is not None,
                       f"HTTP {response.status_code}; DB record "
                       f"{'found' if payment else 'not found'}")
                report(results, "IT7 Payment stores correct BookingID",
                       payment is not None
                       and str(payment["BookingID"]) == booking_id,
                       f"BookingID={payment['BookingID'] if payment else 'not found'}")
            else:
                report(results, "IT5 Booking appears in Payment form", False,
                       "Skipped: booking creation failed.")
                report(results, "IT6 Create payment for test booking", False,
                       "Skipped: booking creation failed.")
                report(results, "IT7 Payment stores correct BookingID", False,
                       "Skipped: booking creation failed.")
        else:
            for name in (
                "IT3 Create booking for new student",
                "IT4 Booking stores correct StudentID",
                "IT5 Booking appears in Payment form",
                "IT6 Create payment for test booking",
                "IT7 Payment stores correct BookingID",
            ):
                report(results, name, False, "Skipped: student creation failed.")

        response = client.get("/")
        report(results, "IT8 Dashboard loads", response.status_code == 200,
               f"HTTP {response.status_code}")

    except Exception as exc:
        report(results, "Unexpected test error", False,
               f"{type(exc).__name__}: {exc}")

    finally:
        try:
            clean, remaining = cleanup(student_id, booking_id, payment_id)
            report(results, "Cleanup: temporary records removed", clean,
                   f"remaining Payment={remaining['payments_left']}, "
                   f"Booking={remaining['bookings_left']}, "
                   f"Student={remaining['students_left']}")
        except Exception as exc:
            report(results, "Cleanup: temporary records removed", False,
                   f"{type(exc).__name__}: {exc}")

    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed
    print("\n" + "-" * 84)
    print(f"RESULT: {passed}/{len(results)} checks passed; {failed} failed.")
    print("-" * 84)


if __name__ == "__main__":
    main()
