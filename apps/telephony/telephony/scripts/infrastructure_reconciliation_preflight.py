from dataclasses import dataclass

import frappe

from telephony.scripts.infrastructure_import_lifecycle import (
    register_infrastructure_import,
    validate_infrastructure_import,
)
from telephony.scripts.infrastructure_reconciliation_batch import (
    LocationBatchPlan,
)


@dataclass(frozen=True)
class LocationBatchPreflightResult:
    import_version: str
    committed: bool
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


def run_location_batch_preflight(
    plan,
    *,
    customer,
    source_type,
    expected_site,
    source_filename=None,
    source_hash=None,
    source_received_on=None,
    importer_version=None,
    notes=None,
    commit=0,
):
    if not isinstance(
        plan,
        LocationBatchPlan,
    ):
        raise TypeError(
            "plan must be a LocationBatchPlan"
        )

    customer = _required_text(
        customer,
        "Customer",
    )

    source_type = _required_text(
        source_type,
        "Source type",
    )

    expected_site = _required_text(
        expected_site,
        "Expected site",
    )

    commit = bool(
        int(commit)
    )

    if not commit:
        raise ValueError(
            "Refusing Location V2 preflight "
            "without commit=1"
        )

    if frappe.local.site != expected_site:
        raise ValueError(
            "Location V2 preflight target site mismatch: "
            f"actual={frappe.local.site!r} "
            f"expected={expected_site!r}"
        )

    try:
        register_infrastructure_import(
            plan.import_version,
            plan.scope_key,
            customer,
            source_type,
            source_filename=source_filename,
            source_hash=source_hash,
            source_received_on=source_received_on,
            importer_version=importer_version,
            notes=notes,
        )

        validate_infrastructure_import(
            plan
        )

        batch = frappe.db.get_value(
            "TELECTRO Infrastructure Import",
            plan.import_version,
            [
                "name",
                "scope_key",
                "customer",
                "source_type",
                "source_filename",
                "source_hash",
                "importer_version",
                "status",
                "record_count",
                "location_count",
            ],
            as_dict=True,
        )

        if not batch:
            raise ValueError(
                "Validated Infrastructure Import "
                "could not be re-read: "
                f"{plan.import_version}"
            )

        expected_count = len(
            plan.entries
        )

        expected = {
            "name": plan.import_version,
            "scope_key": plan.scope_key,
            "customer": customer,
            "source_type": source_type,
            "source_filename": source_filename,
            "source_hash": source_hash,
            "importer_version": importer_version,
            "status": "Validated",
            "record_count": expected_count,
            "location_count": expected_count,
        }

        for fieldname, expected_value in (
            expected.items()
        ):
            actual_value = batch.get(
                fieldname
            )

            if actual_value != expected_value:
                raise ValueError(
                    "Location V2 preflight verification "
                    "failed: "
                    f"{fieldname} "
                    f"actual={actual_value!r} "
                    f"expected={expected_value!r}"
                )

        frappe.db.commit()

        return LocationBatchPreflightResult(
            import_version=plan.import_version,
            committed=True,
            status="Validated",
            record_count=expected_count,
            location_count=expected_count,
        )

    except Exception:
        frappe.db.rollback()
        raise
