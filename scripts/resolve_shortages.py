
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import get_connection


connection = get_connection()
cursor = connection.cursor()

try:
    # Start one transaction for all shortage resolutions.
    cursor.execute("BEGIN IMMEDIATE")

    cursor.execute("""
        SELECT
            sh.shortage_id,
            sh.demand_quantity,
            sh.shortage_quantity,
            sh.status AS shortage_status,

            i.on_hand_quantity - i.reserved_quantity
                AS current_available,

            po.status AS po_status,
            ib.inbound_id,
            ib.received_quantity,
            ib.status AS inbound_status,
            ib.actual_arrival_date,

            (
                SELECT COUNT(*)
                FROM shortage_event se
                WHERE se.shortage_id = sh.shortage_id
                  AND se.event_type = 'SHORTAGE_RESOLVED'
            ) AS existing_resolution_events

        FROM shortage sh

        LEFT JOIN inventory i
            ON sh.sku_id = i.sku_id
            AND sh.location_id = i.location_id

        LEFT JOIN purchase_order_line pol
            ON sh.sku_id = pol.sku_id
            AND sh.location_id = pol.location_id

        LEFT JOIN purchase_order po
            ON pol.po_id = po.po_id

        LEFT JOIN inbound_order ib
            ON pol.po_line_id = ib.po_line_id

        ORDER BY sh.shortage_id
    """)

    records = cursor.fetchall()

    if not records:
        raise Exception("No shortage records found.")

    # Validate that each shortage has exactly one matching record.
    shortage_ids = [row["shortage_id"] for row in records]

    if len(shortage_ids) != len(set(shortage_ids)):
        raise Exception(
            "Duplicate shortage relationships found. No changes made."
        )

    eligible_records = []

    for row in records:
        checks = [
            row["shortage_status"] == "OPEN",
            row["current_available"] is not None,
            row["po_status"] == "RECEIVED",
            row["inbound_id"] is not None,
            row["inbound_status"] == "RECEIVED",
            row["actual_arrival_date"] is not None,
            row["received_quantity"] is not None,
            row["received_quantity"] >= row["shortage_quantity"],
            row["current_available"] >= row["demand_quantity"],
            row["existing_resolution_events"] == 0
        ]

        if not all(checks):
            raise Exception(
                f"Validation failed for {row['shortage_id']}. "
                "No shortages were modified."
            )

        eligible_records.append(row)

    print("=" * 75)
    print("SHORTAGE RESOLUTION")
    print("=" * 75)

    for row in eligible_records:
        event_id = (
            f"SEVT-{row['shortage_id']}-RES-01"
        )

        reason = (
            f"Inbound receipt {row['inbound_id']} was fully received; "
            "current available inventory covers recorded demand."
        )

        cursor.execute("""
            INSERT INTO shortage_event (
                shortage_event_id,
                shortage_id,
                event_type,
                event_date,
                resolved_quantity,
                source_ref,
                reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            row["shortage_id"],
            "SHORTAGE_RESOLVED",
            row["actual_arrival_date"],
            row["shortage_quantity"],
            row["inbound_id"],
            reason
        ))

        cursor.execute("""
            UPDATE shortage
            SET status = 'RESOLVED'
            WHERE shortage_id = ?
              AND status = 'OPEN'
        """, (row["shortage_id"],))

        if cursor.rowcount != 1:
            raise Exception(
                f"Could not update {row['shortage_id']}."
            )

        print("\nShortage ID:", row["shortage_id"])
        print("Event ID:", event_id)
        print("Resolved quantity:", row["shortage_quantity"])
        print("Source inbound ID:", row["inbound_id"])
        print("Resolution date:", row["actual_arrival_date"])
        print("New status: RESOLVED")

    connection.commit()

    print("\n" + "=" * 75)
    print("SHORTAGE RESOLUTION COMPLETED SUCCESSFULLY")
    print("Total shortages resolved:", len(eligible_records))
    print("Resolution events inserted:", len(eligible_records))
    print("Inventory quantities were not changed.")
    print("=" * 75)

except Exception as error:
    connection.rollback()

    print("\nSHORTAGE RESOLUTION FAILED")
    print("Reason:", error)
    print("All changes were rolled back.")

finally:
    connection.close()
