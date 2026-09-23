from collections import Counter
from dataclasses import dataclass

import frappe
from frappe.utils import now_datetime

from telephony.scripts.import_location_release import (
    apply_release_stages,
    verify_release_postflight,
)
from telephony.scripts.infrastructure_reconciliation import (
    LocationReconciliationPlan,
    plan_location_reconciliation,
)
from telephony.scripts.infrastructure_reconciliation_adapter import (
    LocationDatabaseReconciliationPlan,
    get_stored_location_state,
    plan_location_provenance,
)
from telephony.scripts.infrastructure_reconciliation_batch import (
    LocationBatchPlan,
)
from telephony.scripts.infrastructure_reconciliation_tree_writer import (
    apply_existing_location_parent_move,
)
from telephony.scripts.infrastructure_reconciliation_writer import (
    apply_existing_location_plan,
)


LOCATION_V2_NEW_SEMANTIC_FIELDS = (
    "custom_location_semantics",
    "custom_infrastructure_class",
    "custom_lifecycle_state",
    "custom_customer_visibility",
    "custom_ticket_selectability",
)

LOCATION_V2_PROVENANCE_FIELDS = (
    "custom_first_seen_import",
    "custom_last_seen_import",
    "custom_last_changed_import",
)

LOCATION_V2_EXISTING_DEFERRED_FIELDS = {
    "is_group",
    "location",
}


@dataclass(frozen=True)
class LocationBatchApplyResult:
    import_version: str
    committed: bool
    new_count: int
    unchanged_count: int
    changed_count: int
    missing_count: int
    verified_count: int


def _required_text(value, label):
    value = (value or "").strip()

    if not value:
        raise ValueError(
            f"{label} is required"
        )

    return value


def _desired_dict(entry):
    return dict(
        entry.desired_values
    )


def _validate_import_batch(plan):
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
            "Infrastructure Import batch does not exist: "
            f"{plan.import_version}"
        )

    if batch.get("scope_key") != plan.scope_key:
        raise ValueError(
            "Infrastructure Import scope mismatch: "
            f"batch={batch.get('scope_key')!r} "
            f"plan={plan.scope_key!r}"
        )

    if batch.get("status") != "Validated":
        raise ValueError(
            "Infrastructure Import batch must be "
            "Validated before apply: "
            f"{plan.import_version} "
            f"status={batch.get('status')!r}"
        )

    return dict(batch)


def _refresh_entry_plan(
    entry,
    import_version,
):
    stored = get_stored_location_state(
        entry.location_id
    )

    desired = _desired_dict(
        entry
    )

    reconciliation = (
        plan_location_reconciliation(
            entry.location_id,
            desired,
            stored,
        )
    )

    provenance = plan_location_provenance(
        reconciliation,
        stored,
        import_version,
    )

    fresh_plan = (
        LocationDatabaseReconciliationPlan(
            reconciliation=reconciliation,
            provenance=provenance,
        )
    )

    if fresh_plan != entry.database_plan:
        raise ValueError(
            "Location V2 batch plan is stale: "
            f"{entry.location_id}"
        )

    return (
        stored,
        fresh_plan,
    )


def _refresh_batch_plan(plan):
    refreshed = {}

    for entry in plan.entries:
        refreshed[
            entry.location_id
        ] = _refresh_entry_plan(
            entry,
            plan.import_version,
        )

    return refreshed


def _validate_apply_policy(plan):
    for entry in plan.entries:
        state = (
            entry.database_plan
            .reconciliation
            .state
        )

        desired = _desired_dict(
            entry
        )

        if state == "NEW":
            if desired.get("location") not in {
                None,
                "",
            }:
                raise ValueError(
                    "Location V2 NEW geometry is "
                    "not yet supported: "
                    f"{entry.location_id}"
                )

            continue

        if state == "UNCHANGED":
            continue

        if state != "CHANGED":
            raise ValueError(
                "Unsupported Location reconciliation "
                "state during apply: "
                f"{state}"
            )

        changed_fields = tuple(
            change.fieldname
            for change
            in entry.database_plan
            .reconciliation
            .changes
        )

        deferred = tuple(
            fieldname
            for fieldname
            in changed_fields
            if fieldname
            in LOCATION_V2_EXISTING_DEFERRED_FIELDS
        )

        if deferred:
            raise ValueError(
                "Location V2 apply does not yet "
                "support existing changes to: "
                + ", ".join(
                    deferred
                )
            )

        if "parent_location" in changed_fields:
            if changed_fields != (
                "parent_location",
            ):
                raise ValueError(
                    "Location V2 parent move must "
                    "be the only authoritative "
                    "change in this apply slice: "
                    f"{entry.location_id}"
                )

            continue

        if not changed_fields:
            raise ValueError(
                "CHANGED Location has no "
                "authoritative field changes: "
                f"{entry.location_id}"
            )


def _apply_new_v2_fields(entry):
    desired = _desired_dict(
        entry
    )

    provenance = (
        entry.database_plan
        .provenance
    )

    values = {
        fieldname:
            desired[fieldname]
        for fieldname
        in LOCATION_V2_NEW_SEMANTIC_FIELDS
    }

    values.update(
        {
            "custom_first_seen_import":
                provenance.first_seen_import,
            "custom_last_seen_import":
                provenance.last_seen_import,
            "custom_last_changed_import":
                provenance.last_changed_import,
        }
    )

    frappe.db.set_value(
        "Location",
        entry.location_id,
        values,
        update_modified=False,
    )


def _provenance_only_plan(entry):
    return LocationDatabaseReconciliationPlan(
        reconciliation=(
            LocationReconciliationPlan(
                location_id=entry.location_id,
                state="UNCHANGED",
                changes=(),
            )
        ),
        provenance=(
            entry.database_plan
            .provenance
        ),
    )


def _apply_existing_entries(
    plan,
    refreshed,
):
    for entry in plan.entries:
        state = (
            entry.database_plan
            .reconciliation
            .state
        )

        if state == "NEW":
            continue

        stored, fresh_plan = refreshed[
            entry.location_id
        ]

        if state == "UNCHANGED":
            apply_existing_location_plan(
                entry.location_id,
                stored,
                fresh_plan,
            )
            continue

        changed_fields = tuple(
            change.fieldname
            for change
            in fresh_plan
            .reconciliation
            .changes
        )

        if changed_fields == (
            "parent_location",
        ):
            apply_existing_location_parent_move(
                entry.location_id,
                stored,
                fresh_plan,
            )

            apply_existing_location_plan(
                entry.location_id,
                stored,
                _provenance_only_plan(
                    entry
                ),
            )

            continue

        apply_existing_location_plan(
            entry.location_id,
            stored,
            fresh_plan,
        )


def _verify_entry(entry):
    stored = get_stored_location_state(
        entry.location_id
    )

    if stored is None:
        raise ValueError(
            "Missing Location during V2 "
            "postflight verification: "
            f"{entry.location_id}"
        )

    desired = _desired_dict(
        entry
    )

    reconciliation = (
        plan_location_reconciliation(
            entry.location_id,
            desired,
            stored,
        )
    )

    if reconciliation.state != "UNCHANGED":
        raise ValueError(
            "Location authoritative state mismatch "
            "during V2 postflight: "
            f"{entry.location_id} "
            f"state={reconciliation.state}"
        )

    provenance = (
        entry.database_plan
        .provenance
    )

    expected_provenance = {
        "custom_first_seen_import":
            provenance.first_seen_import,
        "custom_last_seen_import":
            provenance.last_seen_import,
        "custom_last_changed_import":
            provenance.last_changed_import,
    }

    for fieldname in (
        LOCATION_V2_PROVENANCE_FIELDS
    ):
        actual = stored.get(
            fieldname
        )

        expected = expected_provenance[
            fieldname
        ]

        if actual != expected:
            raise ValueError(
                "Location provenance mismatch "
                "during V2 postflight: "
                f"{entry.location_id} "
                f"{fieldname} "
                f"actual={actual!r} "
                f"expected={expected!r}"
            )


def _verify_missing_not_seen(
    plan,
):
    for location_id in (
        plan.missing_location_ids
    ):
        last_seen = frappe.db.get_value(
            "Location",
            location_id,
            "custom_last_seen_import",
        )

        if (
            last_seen
            == plan.import_version
        ):
            raise ValueError(
                "Missing Location was incorrectly "
                "marked seen in current import: "
                f"{location_id}"
            )


def _mark_import_applied(plan):
    frappe.db.set_value(
        "TELECTRO Infrastructure Import",
        plan.import_version,
        {
            "status": "Applied",
            "imported_on": now_datetime(),
            "location_count": len(
                plan.entries
            ),
        },
        update_modified=False,
    )


def run_location_batch_apply(
    plan,
    *,
    expected_site,
    commit=0,
):
    if not isinstance(
        plan,
        LocationBatchPlan,
    ):
        raise TypeError(
            "plan must be a LocationBatchPlan"
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
            "Refusing Location V2 write "
            "without commit=1"
        )

    if frappe.local.site != expected_site:
        raise ValueError(
            "Location V2 target site mismatch: "
            f"actual={frappe.local.site!r} "
            f"expected={expected_site!r}"
        )

    _validate_import_batch(
        plan
    )

    _validate_apply_policy(
        plan
    )

    refreshed = _refresh_batch_plan(
        plan
    )

    states = Counter(
        entry.database_plan
        .reconciliation
        .state
        for entry in plan.entries
    )

    try:
        inserted_count = 0

        if plan.new_stages:
            applied = apply_release_stages(
                plan.new_stages,
                external_prerequisites=set(
                    plan.external_prerequisites
                ),
                expected_site=expected_site,
            )

            inserted_count = applied[
                "inserted_count"
            ]

            for entry in plan.entries:
                if (
                    entry.database_plan
                    .reconciliation
                    .state
                    == "NEW"
                ):
                    _apply_new_v2_fields(
                        entry
                    )

        _apply_existing_entries(
            plan,
            refreshed,
        )

        if plan.new_stages:
            verify_release_postflight(
                plan.new_stages,
                external_prerequisites=set(
                    plan.external_prerequisites
                ),
            )

        for entry in plan.entries:
            _verify_entry(
                entry
            )

        _verify_missing_not_seen(
            plan
        )

        if inserted_count != states["NEW"]:
            raise ValueError(
                "Location V2 NEW insert count "
                "mismatch: "
                f"inserted={inserted_count} "
                f"planned={states['NEW']}"
            )

        _mark_import_applied(
            plan
        )

        frappe.db.commit()

        return LocationBatchApplyResult(
            import_version=plan.import_version,
            committed=True,
            new_count=states["NEW"],
            unchanged_count=(
                states["UNCHANGED"]
            ),
            changed_count=states["CHANGED"],
            missing_count=len(
                plan.missing_location_ids
            ),
            verified_count=len(
                plan.entries
            ),
        )

    except Exception:
        frappe.db.rollback()
        raise
