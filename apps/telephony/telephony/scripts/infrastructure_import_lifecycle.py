from dataclasses import dataclass

import frappe

from telephony.scripts.infrastructure_reconciliation_batch import (
    LocationBatchPlan,
)


SOURCE_TYPES = {
    "KMZ",
    "KML",
    "CSV",
    "GeoJSON",
    "Manual",
}


@dataclass(frozen=True)
class InfrastructureImportRegistration:
    import_version: str
    scope_key: str
    customer: str
    source_type: str


@dataclass(frozen=True)
class InfrastructureImportValidation:
    import_version: str
    scope_key: str
    status: str
    record_count: int
    location_count: int


def _required_text(value, label):
    value = (value or "").strip()

    if not value:
        raise ValueError(
            f"{label} is required"
        )

    return value


def _optional_text(value):
    value = (value or "").strip()
    return value or None


def register_infrastructure_import(
    import_version,
    scope_key,
    customer,
    source_type,
    *,
    source_filename=None,
    source_hash=None,
    source_received_on=None,
    importer_version=None,
    notes=None,
):
    import_version = _required_text(
        import_version,
        "Infrastructure import version",
    )

    scope_key = _required_text(
        scope_key,
        "Infrastructure scope key",
    )

    customer = _required_text(
        customer,
        "Customer",
    )

    source_type = _required_text(
        source_type,
        "Source type",
    )

    if source_type not in SOURCE_TYPES:
        raise ValueError(
            "Unsupported infrastructure source type: "
            f"{source_type}"
        )

    if frappe.db.exists(
        "TELECTRO Infrastructure Import",
        import_version,
    ):
        raise ValueError(
            "Infrastructure Import already exists: "
            f"{import_version}"
        )

    doc = frappe.get_doc(
        {
            "doctype":
                "TELECTRO Infrastructure Import",
            "import_version":
                import_version,
            "scope_key":
                scope_key,
            "customer":
                customer,
            "source_type":
                source_type,
            "source_filename":
                _optional_text(
                    source_filename
                ),
            "source_hash":
                _optional_text(
                    source_hash
                ),
            "source_received_on":
                source_received_on,
            "importer_version":
                _optional_text(
                    importer_version
                ),
            "status":
                "Draft",
            "notes":
                _optional_text(
                    notes
                ),
        }
    )

    doc.insert(
        ignore_permissions=True
    )

    return InfrastructureImportRegistration(
        import_version=doc.name,
        scope_key=doc.scope_key,
        customer=doc.customer,
        source_type=doc.source_type,
    )


def validate_infrastructure_import(
    plan,
):
    if not isinstance(
        plan,
        LocationBatchPlan,
    ):
        raise TypeError(
            "plan must be a LocationBatchPlan"
        )

    batch = frappe.db.get_value(
        "TELECTRO Infrastructure Import",
        plan.import_version,
        [
            "name",
            "scope_key",
            "status",
        ],
        as_dict=True,
    )

    if not batch:
        raise ValueError(
            "Infrastructure Import does not exist: "
            f"{plan.import_version}"
        )

    if batch.get("scope_key") != plan.scope_key:
        raise ValueError(
            "Infrastructure Import scope mismatch: "
            f"batch={batch.get('scope_key')!r} "
            f"plan={plan.scope_key!r}"
        )

    if batch.get("status") != "Draft":
        raise ValueError(
            "Infrastructure Import must be Draft "
            "before validation: "
            f"{plan.import_version} "
            f"status={batch.get('status')!r}"
        )

    count = len(
        plan.entries
    )

    frappe.db.set_value(
        "TELECTRO Infrastructure Import",
        plan.import_version,
        {
            "status": "Validated",
            "record_count": count,
            "location_count": count,
        },
        update_modified=False,
    )

    return InfrastructureImportValidation(
        import_version=plan.import_version,
        scope_key=plan.scope_key,
        status="Validated",
        record_count=count,
        location_count=count,
    )
