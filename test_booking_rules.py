"""Booking business-rule tests for SportsFacilityPython.

Run from the project folder:
    .venv\Scripts\python.exe test_booking_rules.py

Uses Flask's test client. Creates only uniquely named bookings and deletes those
bookings at the end. It does not create, edit, or delete existing user records.
"""
from datetime import date, timedelta
from uuid import uuid4

from app import app
from db import get_connection


def db_one(sql, params=()):
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        return cur.fetchone()
    finally:
        conn.close()


def report(results, name, passed, detail=""):
    results.append((name, bool(passed), detail))
    print(f"{name:<54} {'PASS' if passed else 'FAIL'}" + (f" — {detail}" if detail else ""))


def post_booking(client, booking_id, student_id, sport_id, venue_id,
                 booking_date, start, end, status="Pending"):
    return client.post("/bookings/add", data={
        "BookingID": booking_id,
        "BookingDate": booking_date.isoformat(),
        "StartTime": start,
        "EndTime": end,
        "Status": status,
        "StudentID": str(student_id),
        "SportID": str(sport_id),
        "VenueID": str(venue_id),
    }, follow_redirects=False)


def booking_exists(booking_id):
    return db_one("SELECT BookingID, Status FROM Booking WHERE BookingID = %s", (booking_id,))


def main():
    app.config["TESTING"] = True
    client = app.test_client()
    token = uuid4().hex[:9].upper()
    ids = {
        "base": f"BRB{token}A",
        "adjacent": f"BRB{token}B",
        "after_cancel": f"BRB{token}C",
        "bad_fk": f"BRB{token}D",
    }
    results = []
    print("\n" + "=" * 100)
    print("BOOKING BUSINESS-RULE & EDGE-CASE TESTS")
    print("=" * 100)

    try:
        student = db_one("SELECT StudentID FROM Student ORDER BY StudentID LIMIT 1")
        venues = []
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT VenueID, SportID FROM Venue ORDER BY VenueID")
            venues = cur.fetchall()
        finally:
            conn.close()

        if not student or not venues:
            report(results, "Fixtures: at least one student and venue exist", False,
                   "Add at least one student and venue, then rerun.")
            return
        report(results, "Fixtures: student and venue exist", True)

        primary = venues[0]
        other_sport = db_one(
            "SELECT SportID FROM Sport WHERE SportID <> %s ORDER BY SportID LIMIT 1",
            (primary["SportID"],)
        )
        mismatch_available = other_sport is not None
        report(results, "Fixture: a different sport exists for mismatch test",
               mismatch_available, "Mismatch test will be skipped if no second sport exists.")

        chosen_date = None
        for offset in range(30, 396):
            candidate = date.today() + timedelta(days=offset)
            active = db_one("""
                SELECT COUNT(*) AS n FROM Booking
                WHERE VenueID = %s AND BookingDate = %s
                  AND Status IN ('Pending', 'Confirmed')
            """, (primary["VenueID"], candidate))
            if active and active["n"] == 0:
                chosen_date = candidate
                break
        if chosen_date is None:
            report(results, "Fixture: free date found", False,
                   "No free date for selected venue in the next 13 months.")
            return
        report(results, "Fixture: free date found", True, chosen_date.isoformat())

        # BR1: create a valid active booking as the conflict fixture.
        response = post_booking(client, ids["base"], student["StudentID"],
                                primary["SportID"], primary["VenueID"],
                                chosen_date, "10:00", "11:00")
        base = booking_exists(ids["base"])
        report(results, "BR1 Create baseline active booking",
               response.status_code == 302 and base is not None,
               f"HTTP {response.status_code}; record {'found' if base else 'not found'}")

        if base:
            # BR2: partially overlapping interval must be rejected.
            response = post_booking(client, f"BRB{token}X", student["StudentID"],
                                    primary["SportID"], primary["VenueID"],
                                    chosen_date, "10:30", "11:30")
            rejected = response.status_code == 200 and b"already has an active booking" in response.data
            report(results, "BR2 Reject overlapping active booking", rejected,
                   f"HTTP {response.status_code}; conflict message {'shown' if rejected else 'not detected'}")

            # BR3: end time equal to another booking's start is permitted.
            response = post_booking(client, ids["adjacent"], student["StudentID"],
                                    primary["SportID"], primary["VenueID"],
                                    chosen_date, "11:00", "12:00")
            adjacent = booking_exists(ids["adjacent"])
            report(results, "BR3 Allow adjacent booking (11:00–12:00)",
                   response.status_code == 302 and adjacent is not None,
                   f"HTTP {response.status_code}; record {'found' if adjacent else 'not found'}")

            # BR4: venue and selected sport must match.
            if mismatch_available:
                response = post_booking(client, f"BRB{token}Y", student["StudentID"],
                                        other_sport["SportID"], primary["VenueID"],
                                        chosen_date, "13:00", "14:00")
                mismatch_rejected = (
                    response.status_code == 200
                    and (b"does not belong" in response.data or b"belongs to that sport" in response.data)
                )
                report(results, "BR4 Reject venue/sport mismatch", mismatch_rejected,
                       f"HTTP {response.status_code}")
            else:
                report(results, "BR4 Reject venue/sport mismatch", False,
                       "SKIPPED: database has no second sport to test against.")

            # BR5: start time must be strictly earlier than end time.
            response = post_booking(client, f"BRB{token}Z", student["StudentID"],
                                    primary["SportID"], primary["VenueID"],
                                    chosen_date, "14:00", "13:00")
            bad_time_rejected = (
                response.status_code == 200 and b"End time must be later" in response.data
            )
            report(results, "BR5 Reject end time earlier than start time",
                   bad_time_rejected, f"HTTP {response.status_code}")

            # BR6: cancellation should free the slot without deleting the record.
            cancel_response = client.post(f"/bookings/cancel/{ids['base']}", follow_redirects=False)
            cancelled = booking_exists(ids["base"])
            cancel_ok = cancel_response.status_code == 302 and cancelled is not None and cancelled["Status"] == "Cancelled"
            report(results, "BR6 Cancel baseline booking and preserve record", cancel_ok,
                   f"HTTP {cancel_response.status_code}; status={cancelled['Status'] if cancelled else 'missing'}")

            response = post_booking(client, ids["after_cancel"], student["StudentID"],
                                    primary["SportID"], primary["VenueID"],
                                    chosen_date, "10:00", "11:00")
            after_cancel = booking_exists(ids["after_cancel"])
            report(results, "BR7 Reuse slot after original booking is cancelled",
                   response.status_code == 302 and after_cancel is not None,
                   f"HTTP {response.status_code}; record {'found' if after_cancel else 'not found'}")

            # BR8: invalid StudentID should be rejected by the database FK.
            response = post_booking(client, ids["bad_fk"], f"NO_STUDENT_{token}",
                                    primary["SportID"], primary["VenueID"],
                                    chosen_date, "15:00", "16:00")
            bad_fk = booking_exists(ids["bad_fk"])
            fk_rejected = bad_fk is None and response.status_code == 200
            report(results, "BR8 Reject booking with nonexistent StudentID", fk_rejected,
                   f"HTTP {response.status_code}; invalid booking {'not inserted' if bad_fk is None else 'WAS inserted'}")
        else:
            for name in [
                "BR2 Reject overlapping active booking",
                "BR3 Allow adjacent booking (11:00–12:00)",
                "BR4 Reject venue/sport mismatch",
                "BR5 Reject end time earlier than start time",
                "BR6 Cancel baseline booking and preserve record",
                "BR7 Reuse slot after original booking is cancelled",
                "BR8 Reject booking with nonexistent StudentID",
            ]:
                report(results, name, False, "Skipped because baseline booking could not be created.")

    except Exception as exc:
        report(results, "Unexpected test error", False, f"{type(exc).__name__}: {exc}")

    finally:
        # Only delete this run's uniquely generated IDs; child dependencies first.
        try:
            conn = get_connection()
            try:
                cur = conn.cursor()
                for booking_id in ids.values():
                    cur.execute("DELETE FROM Payment WHERE BookingID = %s", (booking_id,))
                for booking_id in ids.values():
                    cur.execute("DELETE FROM Booking WHERE BookingID = %s", (booking_id,))
                conn.commit()
            finally:
                conn.close()
            remaining = 0
            for booking_id in ids.values():
                row = db_one("SELECT COUNT(*) AS n FROM Booking WHERE BookingID = %s", (booking_id,))
                remaining += row["n"] if row else 0
            report(results, "Cleanup: generated bookings removed", remaining == 0,
                   f"{remaining} generated booking(s) remain")
        except Exception as exc:
            report(results, "Cleanup: generated bookings removed", False,
                   f"{type(exc).__name__}: {exc}")

    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed
    print("\n" + "-" * 100)
    print(f"RESULT: {passed}/{len(results)} checks passed; {failed} failed.")
    print("=" * 100)


if __name__ == "__main__":
    main()
