from apps.core.tabular_imports import parse_tabular_upload

REQUIRED_HEADERS = {"received_at", "channel", "person_name", "subject", "message"}
ALLOWED_HEADERS = REQUIRED_HEADERS | {
    "source_reference",
    "company_name",
    "email",
    "phone",
    "priority",
    "assigned_to_id",
}


def parse_historical_enquiries(upload):
    rows = parse_tabular_upload(
        upload,
        required_headers=REQUIRED_HEADERS,
        allowed_headers=ALLOWED_HEADERS,
        label="enquiries",
    )
    for row in rows:
        row["channel"] = row.get("channel", "").upper().replace(" ", "_")
        row["priority"] = row.get("priority", "NORMAL").upper() or "NORMAL"
    return rows
