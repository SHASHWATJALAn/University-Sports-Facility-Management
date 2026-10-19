"""
Phase 4: Security & Input Validation Tests
Sports Facility Management System

Run from the project folder:
    .venv\Scripts\python.exe test_security_validation.py

Uses Flask's test client; no separate Flask server is required.
The tests do not intentionally create valid business records.
"""

from uuid import uuid4
from urllib.parse import quote

from app import app
from db import get_connection


def report(results, name, passed, detail=""):
    results.append(bool(passed))
    print(f"{name:<52} {'PASS' if passed else 'FAIL'}"
          + (f" — {detail}" if detail else ""))


def payment_exists(payment_id):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM Payment WHERE PaymentID = %s",
            (payment_id,)
        )
        count = cursor.fetchone()[0]
        cursor.close()
        return count > 0
    finally:
        connection.close()


def main():
    app.config["TESTING"] = False
    client = app.test_client()
    results = []
    unique_id = "SEC" + uuid4().hex[:12].upper()

    print("\nPHASE 4 — SECURITY & INPUT VALIDATION")
    print("-" * 75)

    # 1. Core pages should respond without an internal server error.
    pages = [
        ("/", "Dashboard"),
        ("/students", "Students page"),
        ("/students/add", "Student form"),
        ("/sports", "Sports page"),
        ("/bookings", "Bookings page"),
        ("/payments", "Payments page"),
        ("/payments/add", "Payment form"),
    ]
    page_results = []
    for path, label in pages:
        try:
            response = client.get(path)
            ok = response.status_code < 500
            page_results.append(ok)
        except Exception:
            page_results.append(False)
    report(results, "Core pages handle requests without HTTP 500",
           all(page_results), f"{sum(page_results)}/{len(page_results)} pages")

    # 2. Missing payment fields should be rejected and not create a row.
    try:
        response = client.post("/payments/add", data={})
        ok = (response.status_code == 200
              and not payment_exists(unique_id))
        report(results, "Reject payment submission with missing fields",
               ok, f"HTTP {response.status_code}")
    except Exception as exc:
        report(results, "Reject payment submission with missing fields",
               False, type(exc).__name__)

    # 3. SQL-injection-looking text in numeric amount must be rejected.
    try:
        response = client.post("/payments/add", data={
            "PaymentID": unique_id,
            "Amount": "0 OR 1=1 --",
            "PaymentDate": "2026-10-20",
            "PaymentMode": "Cash",
            "BookingID": "NONEXISTENT_BOOKING_FOR_SECURITY_TEST",
        })
        no_record = not payment_exists(unique_id)
        ok = response.status_code == 200 and no_record
        report(results, "Reject SQL-injection text as payment amount",
               ok, f"HTTP {response.status_code}; payment row absent={no_record}")
    except Exception as exc:
        report(results, "Reject SQL-injection text as payment amount",
               False, type(exc).__name__)

    # 4. Negative payment amount must be rejected before INSERT.
    negative_id = "NEG" + uuid4().hex[:10].upper()
    try:
        response = client.post("/payments/add", data={
            "PaymentID": negative_id,
            "Amount": "-25.00",
            "PaymentDate": "2026-10-20",
            "PaymentMode": "Cash",
            "BookingID": "NONEXISTENT_BOOKING_FOR_SECURITY_TEST",
        })
        no_record = not payment_exists(negative_id)
        ok = response.status_code == 200 and no_record
        report(results, "Reject negative payment amount",
               ok, f"HTTP {response.status_code}; payment row absent={no_record}")
    except Exception as exc:
        report(results, "Reject negative payment amount",
               False, type(exc).__name__)

    # 5. Invalid calendar date must be rejected before INSERT.
    invalid_date_id = "DAT" + uuid4().hex[:10].upper()
    try:
        response = client.post("/payments/add", data={
            "PaymentID": invalid_date_id,
            "Amount": "10.00",
            "PaymentDate": "2026-02-30",
            "PaymentMode": "Cash",
            "BookingID": "NONEXISTENT_BOOKING_FOR_SECURITY_TEST",
        })
        no_record = not payment_exists(invalid_date_id)
        ok = response.status_code == 200 and no_record
        report(results, "Reject invalid calendar date",
               ok, f"HTTP {response.status_code}; payment row absent={no_record}")
    except Exception as exc:
        report(results, "Reject invalid calendar date",
               False, type(exc).__name__)

    # 6. Excessively long payment ID must be rejected before INSERT.
    long_id = "L" * 21
    try:
        response = client.post("/payments/add", data={
            "PaymentID": long_id,
            "Amount": "10.00",
            "PaymentDate": "2026-10-20",
            "PaymentMode": "Cash",
            "BookingID": "NONEXISTENT_BOOKING_FOR_SECURITY_TEST",
        })
        ok = response.status_code == 200 and not payment_exists(long_id)
        report(results, "Reject payment ID longer than 20 characters",
               ok, f"HTTP {response.status_code}")
    except Exception as exc:
        report(results, "Reject payment ID longer than 20 characters",
               False, type(exc).__name__)

    # 7. SQL-injection-looking path value must not cause a server error.
    # The URL is encoded to keep it within the single route parameter.
    try:
        payload = quote("' OR '1'='1", safe="")
        response = client.get(f"/students/edit/{payload}", follow_redirects=False)
        ok = response.status_code in (301, 302, 303, 307, 308, 400, 404)
        report(results, "SQL-injection-looking ID does not cause HTTP 500",
               ok, f"HTTP {response.status_code}")
    except Exception as exc:
        report(results, "SQL-injection-looking ID does not cause HTTP 500",
               False, type(exc).__name__)

    # 8. Confirm the app uses parameter placeholders in representative queries.
    # This is a source-code review check, not a complete security audit.
    try:
        from pathlib import Path
        source = Path(__file__).with_name("app.py").read_text(
            encoding="utf-8"
        )
        ok = (
            'WHERE StudentID = %s' in source
            and 'VALUES (%s, %s, %s, %s, %s)' in source
            and 'WHERE BookingID = %s' in source
        )
        report(results, "Representative database queries use placeholders",
               ok, "source-code spot check")
    except Exception as exc:
        report(results, "Representative database queries use placeholders",
               False, type(exc).__name__)

    print("-" * 75)
    passed = sum(results)
    print(f"RESULT: {passed}/{len(results)} checks passed.")
    if passed == len(results):
        print("Phase 4 checks passed for the cases exercised.")
    else:
        print("Review the FAIL rows and send the complete output for diagnosis.")
    print("Note: These checks do not constitute a complete security audit.")


if __name__ == "__main__":
    main()
