"""
Phase 5: Final Regression Checks
University Sports Facility Management System

Run from the project folder:
    .venv\Scripts\python.exe test_final_regression.py

This is a read-only regression smoke test: it does not create, edit, or delete
business records. It checks the main pages, database connectivity, schema
presence, and key invariants in the current database.
"""

from app import app
from db import get_connection


EXPECTED_TABLES = {
    "Student", "StudentPhone", "Sport", "Coach", "CoachCertification",
    "Venue", "Equipment", "Booking", "Payment"
}

PAGES = [
    ("/", "Dashboard"),
    ("/students", "Student Management"),
    ("/sports", "Sports Management"),
    ("/coaches", "Coach Management"),
    ("/venues", "Venue Management"),
    ("/equipment", "Equipment Management"),
    ("/certifications", "Coach Certification Management"),
    ("/bookings", "Booking Management"),
    ("/payments", "Payment Management"),
]


def check(results, label, passed, detail=""):
    results.append(bool(passed))
    print(f"{label:<54} {'PASS' if passed else 'FAIL'}"
          + (f" — {detail}" if detail else ""))


def db_scalar(query, params=None):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(query, params or ())
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else None
    finally:
        connection.close()


def main():
    results = []
    app.config["TESTING"] = False
    client = app.test_client()

    print("\nPHASE 5 — FINAL REGRESSION CHECKS")
    print("=" * 86)

    # A. Route smoke tests: check expected pages return a non-server-error response.
    route_results = []
    route_codes = []
    for path, label in PAGES:
        try:
            response = client.get(path, follow_redirects=False)
            ok = response.status_code < 500
            route_results.append(ok)
            route_codes.append(f"{label}: HTTP {response.status_code}")
        except Exception as exc:
            route_results.append(False)
            route_codes.append(f"{label}: {type(exc).__name__}")
    check(results, "All main module pages avoid HTTP 500",
          all(route_results),
          f"{sum(route_results)}/{len(route_results)} pages; " +
          "; ".join(route_codes))

    # B. Verify the app can connect to its configured database.
    try:
        db_name = db_scalar("SELECT DATABASE()")
        check(results, "Database connection is available",
              db_name is not None and str(db_name).lower() == "sportsfacilitydb",
              f"database={db_name!r}")
    except Exception as exc:
        check(results, "Database connection is available", False,
              type(exc).__name__)

    # C. Verify expected application tables exist (case-insensitive).
    try:
        tables = db_scalar(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE LOWER(table_schema) = LOWER(DATABASE()) "
            "AND LOWER(table_name) IN "
            "('student','studentphone','sport','coach','coachcertification',"
            "'venue','equipment','booking','payment')"
        )
        check(results, "All 9 expected database tables exist",
              tables == len(EXPECTED_TABLES), f"{tables}/9 found")
    except Exception as exc:
        check(results, "All 9 expected database tables exist", False,
              type(exc).__name__)

    # D. Invariant checks: these should be zero in a consistent database.
    invariants = [
        (
            "No bookings reference missing students",
            "SELECT COUNT(*) FROM Booking b LEFT JOIN Student s "
            "ON b.StudentID=s.StudentID WHERE s.StudentID IS NULL"
        ),
        (
            "No bookings reference missing venues",
            "SELECT COUNT(*) FROM Booking b LEFT JOIN Venue v "
            "ON b.VenueID=v.VenueID WHERE v.VenueID IS NULL"
        ),
        (
            "No bookings reference missing sports",
            "SELECT COUNT(*) FROM Booking b LEFT JOIN Sport s "
            "ON b.SportID=s.SportID WHERE s.SportID IS NULL"
        ),
        (
            "No payments reference missing bookings",
            "SELECT COUNT(*) FROM Payment p LEFT JOIN Booking b "
            "ON p.BookingID=b.BookingID WHERE b.BookingID IS NULL"
        ),
        (
            "No duplicate payments per booking",
            "SELECT COUNT(*) FROM (SELECT BookingID FROM Payment "
            "GROUP BY BookingID HAVING COUNT(*) > 1) duplicates_found"
        ),
        (
            "No booking sport/venue mismatches",
            "SELECT COUNT(*) FROM Booking b JOIN Venue v "
            "ON b.VenueID=v.VenueID WHERE b.SportID <> v.SportID"
        ),
    ]
    for label, query in invariants:
        try:
            count = db_scalar(query)
            check(results, label, count == 0, f"violations={count}")
        except Exception as exc:
            check(results, label, False, type(exc).__name__)

    print("=" * 86)
    passed = sum(results)
    print(f"RESULT: {passed}/{len(results)} regression checks passed.")
    if passed == len(results):
        print("Final read-only regression checks passed.")
    else:
        print("One or more checks failed. Send the complete CMD output for diagnosis.")
    print("This script does not modify database records.")
    print("Note: HTTP responses below 500 are smoke checks, not proof every form action works.")


if __name__ == "__main__":
    main()
