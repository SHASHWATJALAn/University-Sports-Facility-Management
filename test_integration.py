"""
Read-only integration tests for the Sports Facility Management System.

Run from the project folder:
    .venv\Scripts\python.exe test_integration.py

This first integration suite is intentionally READ-ONLY:
- It opens the dashboard and each module's list/add page through Flask's test client.
- It inspects MySQL foreign-key metadata and checks for orphaned references.
- It checks the special Booking-to-Venue sport consistency rule.
- It does not insert, update, or delete any records.

Prerequisites:
- MySQL Server is running.
- db.py connects to the SportsFacilityDB database.
- app.py and the templates folder are in the current project directory.
"""

from app import app
from db import get_connection


def report(results, name, passed, detail=""):
    results.append((name, bool(passed), detail))
    label = "PASS" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"{name:<58} {label}{suffix}")


def run_page_checks(client, results):
    pages = [
        ("Dashboard", "/"),
        ("Student list", "/students"),
        ("Add Student form", "/students/add"),
        ("Sport list", "/sports"),
        ("Add Sport form", "/sports/add"),
        ("Coach list", "/coaches"),
        ("Add Coach form", "/coaches/add"),
        ("Venue list", "/venues"),
        ("Add Venue form", "/venues/add"),
        ("Equipment list", "/equipment"),
        ("Add Equipment form", "/equipment/add"),
        ("Coach Certification list", "/certifications"),
        ("Add Certification form", "/certifications/add"),
        ("Booking list", "/bookings"),
        ("Add Booking form", "/bookings/add"),
        ("Payment list", "/payments"),
        ("Add Payment form", "/payments/add"),
    ]

    for name, path in pages:
        try:
            response = client.get(path, follow_redirects=False)
            passed = response.status_code == 200
            detail = f"HTTP {response.status_code}"
            if not passed and response.status_code in (301, 302, 303, 307, 308):
                detail += f", redirected to {response.headers.get('Location', '?')}"
            report(results, f"Page integration: {name}", passed, detail)
        except Exception as error:
            report(
                results,
                f"Page integration: {name}",
                False,
                f"{type(error).__name__}: {error}",
            )


def run_foreign_key_checks(results):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT DATABASE() AS db_name")
        db_name = cursor.fetchone()["db_name"]
        report(
            results,
            "Connected to expected database",
            db_name == "sportsfacilitydb",
            f"database={db_name}",
        )

        cursor.execute("""
            SELECT
                TABLE_NAME,
                COLUMN_NAME,
                REFERENCED_TABLE_NAME,
                REFERENCED_COLUMN_NAME,
                CONSTRAINT_NAME,
                ORDINAL_POSITION
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND REFERENCED_TABLE_NAME IS NOT NULL
            ORDER BY TABLE_NAME, CONSTRAINT_NAME, ORDINAL_POSITION
        """)
        foreign_keys = cursor.fetchall()

        if not foreign_keys:
            report(
                results,
                "Database foreign-key metadata available",
                False,
                "No foreign keys were found in the current database.",
            )
            return

        report(
            results,
            "Database foreign-key metadata available",
            True,
            f"{len(foreign_keys)} foreign-key column mapping(s) found",
        )

        # Group columns by FK constraint so composite foreign keys are checked
        # together rather than as separate, weaker column checks.
        groups = {}
        for fk in foreign_keys:
            key = (
                fk["TABLE_NAME"],
                fk["CONSTRAINT_NAME"],
                fk["REFERENCED_TABLE_NAME"],
            )
            groups.setdefault(key, []).append(fk)

        for (child_table, constraint_name, parent_table), columns in groups.items():
            columns.sort(key=lambda item: item["ORDINAL_POSITION"])
            child_cols = [item["COLUMN_NAME"] for item in columns]
            parent_cols = [item["REFERENCED_COLUMN_NAME"] for item in columns]

            # Identifiers are read from MySQL metadata, then escaped with
            # backticks. Values are not user input.
            child_join = " AND ".join(
                f"c.`{child_col}` = p.`{parent_col}`"
                for child_col, parent_col in zip(child_cols, parent_cols)
            )
            child_nonnull = " AND ".join(
                f"c.`{child_col}` IS NOT NULL" for child_col in child_cols
            )
            sql = f"""
                SELECT COUNT(*) AS orphan_count
                FROM `{child_table}` c
                WHERE {child_nonnull}
                  AND NOT EXISTS (
                      SELECT 1
                      FROM `{parent_table}` p
                      WHERE {child_join}
                  )
            """
            cursor.execute(sql)
            orphan_count = cursor.fetchone()["orphan_count"]
            label = (
                f"Foreign key: {child_table}.{','.join(child_cols)}"
                f" → {parent_table}.{','.join(parent_cols)}"
            )
            report(
                results,
                label,
                orphan_count == 0,
                f"{orphan_count} orphaned row(s); constraint={constraint_name}",
            )

        # The application also enforces that a Booking's SportID matches the
        # SportID of its selected Venue. This may be implemented by a composite
        # FK or application-level validation, so test it explicitly.
        cursor.execute("""
            SELECT COUNT(*) AS mismatch_count
            FROM Booking B
            JOIN Venue V ON V.VenueID = B.VenueID
            WHERE B.SportID <> V.SportID
        """)
        mismatch_count = cursor.fetchone()["mismatch_count"]
        report(
            results,
            "Booking sport matches selected venue sport",
            mismatch_count == 0,
            f"{mismatch_count} mismatched booking(s)",
        )

        # A booking must not have more than one payment.
        cursor.execute("""
            SELECT COUNT(*) AS duplicate_groups
            FROM (
                SELECT BookingID
                FROM Payment
                GROUP BY BookingID
                HAVING COUNT(*) > 1
            ) duplicates
        """)
        duplicate_groups = cursor.fetchone()["duplicate_groups"]
        report(
            results,
            "At most one payment per booking",
            duplicate_groups == 0,
            f"{duplicate_groups} booking(s) have multiple payments",
        )

    finally:
        cursor.close()
        connection.close()


def main():
    app.config["TESTING"] = True
    client = app.test_client()
    results = []

    print("\n" + "=" * 100)
    print(" SPORTS FACILITY MANAGEMENT — READ-ONLY INTEGRATION TESTS")
    print("=" * 100)
    print("No records will be inserted, updated, or deleted.\n")

    run_page_checks(client, results)

    try:
        run_foreign_key_checks(results)
    except Exception as error:
        report(
            results,
            "Database relationship checks completed",
            False,
            f"{type(error).__name__}: {error}",
        )

    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed

    print("\n" + "-" * 100)
    print(f"RESULT: {passed} passed, {failed} failed, {len(results)} total")
    print("-" * 100)

    if failed:
        print("Review the FAIL entries above. This script is read-only.")
    else:
        print("All read-only integration checks passed.")


if __name__ == "__main__":
    main()
