"""
Automated payment CRUD and business-rule tests for Sports Facility Management.

Run from the project folder:
    .venv\Scripts\python.exe test_payment_rules.py

The script:
- Uses Flask's test client (no browser clicks required).
- Creates uniquely named temporary bookings/payments.
- Checks payment creation, validation, editing, cancelled-booking restrictions,
  duplicate-payment prevention, dropdown filtering, and deletion.
- Cleans up only the temporary records it created.

Prerequisites:
- MySQL is running and db.py connects to SportsFacilityDB.
- At least one Student and one Venue exist.
- The app has the payment routes:
    /payments/add
    /payments/edit/<payment_id>
    /payments/delete/<payment_id>

NOTE: A failing test means the current app behavior did not match the expected
rule. The test script does not modify app.py.
"""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from app import app
from db import get_connection


def record(results, name, passed, detail=""):
    results.append((name, bool(passed), detail))
    status = "PASS" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"{name:<48} {status}{suffix}")


def get_fixtures():
    """Find existing parent records needed for temporary test bookings."""
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT StudentID
            FROM Student
            ORDER BY StudentID
            LIMIT 1
        """)
        student = cursor.fetchone()
        if not student:
            raise RuntimeError(
                "No students found. Add at least one Student before running tests."
            )

        cursor.execute("""
            SELECT VenueID, SportID
            FROM Venue
            ORDER BY VenueID
            LIMIT 1
        """)
        venue = cursor.fetchone()
        if not venue:
            raise RuntimeError(
                "No venues found. Add at least one Venue before running tests."
            )

        return {
            "student_id": student["StudentID"],
            "venue_id": venue["VenueID"],
            "sport_id": venue["SportID"],
        }
    finally:
        cursor.close()
        connection.close()


def main():
    fixtures = get_fixtures()
    tag = uuid4().hex[:8].upper()
    # IDs remain below common VARCHAR(20) limits.
    booking_ids = {
        "active": f"ZTB{tag}01",
        "target": f"ZTB{tag}02",
        "cancelled": f"ZTB{tag}03",
        "history": f"ZTB{tag}04",
        "delete": f"ZTB{tag}05",
        "duplicate": f"ZTB{tag}06",
    }
    payment_ids = {
        "main": f"ZTP{tag}01",
        "history": f"ZTP{tag}02",
        "delete": f"ZTP{tag}03",
        "duplicate": f"ZTP{tag}04",
        "duplicate_attempt": f"ZTP{tag}05",
        "cancelled_attempt": f"ZTP{tag}06",
    }

    created_booking_ids = []
    created_payment_ids = []
    results = []
    client = app.test_client()
    app.config["TESTING"] = True

    # A future date and distinct time slots keep the temporary fixtures simple.
    test_date = date.today() + timedelta(days=60)

    def setup_bookings():
        connection = get_connection()
        cursor = connection.cursor()
        try:
            statuses = {
                "active": "Confirmed",
                "target": "Pending",
                "cancelled": "Cancelled",
                "history": "Confirmed",
                "delete": "Confirmed",
                "duplicate": "Confirmed",
            }
            for index, key in enumerate(booking_ids):
                bid = booking_ids[key]
                start_hour = 6 + index
                end_hour = start_hour + 1
                cursor.execute("""
                    INSERT INTO Booking
                        (BookingID, BookingDate, StartTime, EndTime, Status,
                         StudentID, SportID, VenueID)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    bid,
                    test_date.isoformat(),
                    f"{start_hour:02d}:00:00",
                    f"{end_hour:02d}:00:00",
                    statuses[key],
                    fixtures["student_id"],
                    fixtures["sport_id"],
                    fixtures["venue_id"],
                ))
                created_booking_ids.append(bid)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def db_payment(payment_id):
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT PaymentID, Amount, PaymentDate, PaymentMode, BookingID "
                "FROM Payment WHERE PaymentID = %s",
                (payment_id,),
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            connection.close()

    def db_booking_status(booking_id):
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT Status FROM Booking WHERE BookingID = %s",
                (booking_id,),
            )
            row = cursor.fetchone()
            return row["Status"] if row else None
        finally:
            cursor.close()
            connection.close()

    def set_booking_status(booking_id, status):
        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                "UPDATE Booking SET Status = %s WHERE BookingID = %s",
                (status, booking_id),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def post_payment(payment_id, booking_id, amount="250.00",
                     payment_date=None, mode="UPI"):
        return client.post(
            "/payments/add",
            data={
                "PaymentID": payment_id,
                "Amount": amount,
                "PaymentDate": payment_date or date.today().isoformat(),
                "PaymentMode": mode,
                "BookingID": booking_id,
            },
            follow_redirects=True,
        )

    def post_edit(payment_id, booking_id, amount="275.00",
                  payment_date=None, mode="Card"):
        return client.post(
            f"/payments/edit/{payment_id}",
            data={
                "Amount": amount,
                "PaymentDate": payment_date or date.today().isoformat(),
                "PaymentMode": mode,
                "BookingID": booking_id,
            },
            follow_redirects=True,
        )

    def flash_or_response_contains(response, text):
        return text.lower().encode() in response.data.lower()

    print("\n" + "=" * 88)
    print(" AUTOMATED PAYMENT TESTS")
    print("=" * 88)
    print("Only uniquely named temporary records are created; cleanup runs at the end.\n")

    try:
        setup_bookings()

        # T1: Add a payment to an active booking.
        response = post_payment(payment_ids["main"], booking_ids["active"])
        row = db_payment(payment_ids["main"])
        if row:
            created_payment_ids.append(payment_ids["main"])
        record(
            results,
            "T1 Add payment to active booking",
            row is not None and row["BookingID"] == booking_ids["active"],
            "payment row exists" if row else "payment row was not created",
        )

        # T2: Cancelled booking should not be listed in the Add Payment form.
        response = client.get("/payments/add")
        cancelled_option = (
            f'<option value="{booking_ids["cancelled"]}"'
        ).encode()

        record(
            results,
            "T2 Hide cancelled booking in Add dropdown",
            cancelled_option not in response.data,
            "cancelled booking should not be an available dropdown option",
        )

        # T3: Server-side protection: direct POST for a cancelled booking.
        response = post_payment(
            payment_ids["cancelled_attempt"], booking_ids["cancelled"]
        )
        row = db_payment(payment_ids["cancelled_attempt"])
        if row:
            created_payment_ids.append(payment_ids["cancelled_attempt"])
        record(
            results,
            "T3 Reject payment for cancelled booking",
            row is None and flash_or_response_contains(
                response, "cancelled booking"
            ),
            "must reject the POST and create no payment",
        )

        # T4: Edit amount/date/mode while keeping the same active booking.
        response = post_edit(
            payment_ids["main"],
            booking_ids["active"],
            amount="310.50",
            payment_date=(date.today() - timedelta(days=1)).isoformat(),
            mode="Card",
        )
        row = db_payment(payment_ids["main"])
        record(
            results,
            "T4 Edit existing payment fields",
            row is not None
            and Decimal(str(row["Amount"])) == Decimal("310.50")
            and str(row["PaymentMode"]) == "Card",
            "amount and mode should reflect the update",
        )

        # T5: Reassign the existing payment to a different cancelled booking.
        response = post_edit(
            payment_ids["main"], booking_ids["cancelled"], amount="320.00"
        )
        row = db_payment(payment_ids["main"])
        record(
            results,
            "T5 Reject reassignment to cancelled booking",
            row is not None
            and row["BookingID"] == booking_ids["active"]
            and flash_or_response_contains(response, "cancelled booking"),
            "payment should remain attached to its original booking",
        )

        # T6: Existing payment can still be edited if its booking is cancelled later.
        response = post_payment(payment_ids["history"], booking_ids["history"])
        history_row = db_payment(payment_ids["history"])
        if history_row:
            created_payment_ids.append(payment_ids["history"])
            set_booking_status(booking_ids["history"], "Cancelled")
            response = post_edit(
                payment_ids["history"],
                booking_ids["history"],
                amount="499.00",
                mode="Bank Transfer",
            )
            row = db_payment(payment_ids["history"])
            record(
                results,
                "T6 Edit payment after booking later cancelled",
                row is not None
                and row["BookingID"] == booking_ids["history"]
                and Decimal(str(row["Amount"])) == Decimal("499.00"),
                "historical payment fields should remain editable",
            )
        else:
            record(
                results,
                "T6 Edit payment after booking later cancelled",
                False,
                "setup payment could not be created",
            )

        # T7: Duplicate payment for a booking should be rejected.
        response = post_payment(payment_ids["duplicate"], booking_ids["duplicate"])
        row = db_payment(payment_ids["duplicate"])
        if row:
            created_payment_ids.append(payment_ids["duplicate"])
        response = post_payment(
            payment_ids["duplicate_attempt"], booking_ids["duplicate"]
        )
        duplicate_attempt = db_payment(payment_ids["duplicate_attempt"])
        if duplicate_attempt:
            created_payment_ids.append(payment_ids["duplicate_attempt"])
        record(
            results,
            "T7 Prevent two payments for one booking",
            row is not None
            and duplicate_attempt is None
            and flash_or_response_contains(response, "already has a payment"),
            "second payment for the same booking should be rejected",
        )

        # T8: Invalid amount should not create a payment.
        invalid_id = f"ZTP{tag}07"
        response = post_payment(
            invalid_id, booking_ids["target"], amount="-1.00"
        )
        invalid_row = db_payment(invalid_id)
        if invalid_row:
            created_payment_ids.append(invalid_id)
        record(
            results,
            "T8 Reject non-positive payment amount",
            invalid_row is None
            and flash_or_response_contains(response, "valid positive amount"),
            "negative amount should be rejected",
        )

        # T9: Delete payment without deleting its booking.
        response = post_payment(payment_ids["delete"], booking_ids["delete"])
        delete_row = db_payment(payment_ids["delete"])
        if delete_row:
            created_payment_ids.append(payment_ids["delete"])
            response = client.post(
                f"/payments/delete/{payment_ids['delete']}",
                follow_redirects=True,
            )
        payment_after_delete = db_payment(payment_ids["delete"])
        booking_status_after_delete = db_booking_status(booking_ids["delete"])
        record(
            results,
            "T9 Delete payment keeps booking intact",
            delete_row is not None
            and payment_after_delete is None
            and booking_status_after_delete == "Confirmed",
            "payment should be deleted; booking should remain",
        )

        # T10: A payment may be moved to another active booking.
        # Use the main payment and target booking; target must not have a payment.
        response = post_edit(
            payment_ids["main"], booking_ids["target"], amount="333.00"
        )
        row = db_payment(payment_ids["main"])
        record(
            results,
            "T10 Reassign payment to active booking",
            row is not None and row["BookingID"] == booking_ids["target"],
            "active target booking should be accepted",
        )

    except Exception as error:
        print(f"\nTEST RUN ERROR: {type(error).__name__}: {error}")
        print("Cleanup will still be attempted.")
        results.append(("TEST RUN COMPLETED WITHOUT EXCEPTION", False, str(error)))

    finally:
        # Delete only test payment IDs, then test booking IDs.
        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor()
            if created_payment_ids:
                placeholders = ", ".join(["%s"] * len(set(created_payment_ids)))
                cursor.execute(
                    f"DELETE FROM Payment WHERE PaymentID IN ({placeholders})",
                    tuple(set(created_payment_ids)),
                )
            if created_booking_ids:
                placeholders = ", ".join(["%s"] * len(set(created_booking_ids)))
                cursor.execute(
                    f"DELETE FROM Booking WHERE BookingID IN ({placeholders})",
                    tuple(set(created_booking_ids)),
                )
            connection.commit()
            print("\nCleanup: temporary payment and booking records removed.")
        except Exception as cleanup_error:
            if connection:
                connection.rollback()
            print(
                "\nCLEANUP WARNING: automatic cleanup failed: "
                f"{type(cleanup_error).__name__}: {cleanup_error}"
            )
            print("Check these temporary ID prefixes in MySQL: ZTP and ZTB.")
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    print("\n" + "-" * 88)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed
    print(f"RESULT: {passed} passed, {failed} failed, {len(results)} total")
    print("-" * 88)
    if failed:
        print("Review each FAIL above. The test script reports behavior; it does not edit app.py.")
    else:
        print("All payment tests passed.")


if __name__ == "__main__":
    main()
