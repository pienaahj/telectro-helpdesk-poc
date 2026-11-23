"""Bounded, read-only reference selection for the Technician booking form."""

import json

from telephony.time_booking_project_grant import (
    ProjectBookingGrantError,
    _project_grant_periods,
    _stored_time,
    covers_project_booking,
)


PAGE_SIZE = 20
MAX_PAGE = 4
_CANDIDATE_LIMIT = PAGE_SIZE * (MAX_PAGE + 1)
_HISTORY_LIMIT = 256

_PROJECTS = """
    SELECT p.name, p.project_name AS label, p.company, p.creation
      FROM `tabProject` p
     WHERE p.company = %(company)s
       AND (%(name)s IS NULL OR p.name = %(name)s)
       AND (%(term)s = '' OR LOCATE(%(term)s, p.name) OR LOCATE(%(term)s, p.project_name))
       AND EXISTS (
           SELECT 1 FROM `tabTELECTRO Project Booking Grant` g
            WHERE g.project = p.name AND g.project_created_at = p.creation
              AND g.technician_user = %(user)s AND g.employee = %(employee)s
              AND g.company = %(company)s AND g.effective_start <= %(start)s
              AND (g.effective_end IS NULL OR g.effective_end > %(start)s)
       )
     ORDER BY p.name <> %(term)s, p.name
     LIMIT %(limit)s
"""

_TASKS = """
    SELECT t.name, t.subject AS label, t.project, t.creation
      FROM `tabTask` t
      JOIN JSON_TABLE(%(ids)s, '$[*]' COLUMNS (task_id VARCHAR(140) PATH '$')) permitted
        ON BINARY permitted.task_id = BINARY t.name
     WHERE t.project = %(project)s
       AND (%(name)s IS NULL OR t.name = %(name)s)
       AND (%(term)s = '' OR LOCATE(%(term)s, t.name) OR LOCATE(%(term)s, t.subject))
     ORDER BY t.name <> %(term)s, t.name
     LIMIT %(limit)s
"""


def _eligible_interval(identity, project, start, end, evaluated_at):
    project_created_at = _stored_time(project.creation)
    periods = _project_grant_periods(
        identity, project.name, project_created_at, limit=_HISTORY_LIMIT,
    )
    coverage = dict(
        identity=identity, project=project.name, project_company=project.company,
        project_created_at=project_created_at, start=start, end=end,
        periods=periods, evaluated_at=evaluated_at,
    )
    return coverage if covers_project_booking(**coverage) else None


def _page(rows, page):
    first = page * PAGE_SIZE
    for index, row in enumerate(rows):
        if index >= first:
            yield {"id": row.name, "label": row.label or row.name}
        if index + 1 == first + PAGE_SIZE:
            return


def project_options(*, identity, start, end, evaluated_at, term, page, name):
    import frappe

    rows = frappe.db.sql(
        _PROJECTS, {
            "user": identity.user, "employee": identity.employee, "company": identity.company,
            "start": start, "term": term, "name": name, "limit": 1 if name else _CANDIDATE_LIMIT,
        },
        as_dict=True,
    )

    def eligible():
        for project in rows:
            if name is not None and project.name != name:
                continue
            try:
                if _eligible_interval(identity, project, start, end, evaluated_at):
                    yield project
            except ProjectBookingGrantError:
                continue

    return list(_page(eligible(), page))


def task_options(*, identity, project_name, start, end, evaluated_at, term, page, name):
    import frappe

    project = frappe.db.get_value(
        "Project", project_name, ["name", "company", "creation"], as_dict=True,
    )
    if not project or project.name != project_name or project.company != identity.company:
        return []
    try:
        coverage = _eligible_interval(identity, project, start, end, evaluated_at)
    except ProjectBookingGrantError:
        return []
    if not coverage:
        return []

    # Full coverage was checked above. A permitted Task must occur in the
    # period containing the beginning of the work, even if the interval spans
    # several adjacent periods. The same policy checks its complete coverage.
    initial = next(
        period for period in coverage["periods"]
        if period.effective_start <= start
        and (period.effective_end is None or start < period.effective_end)
    )
    task_ids = sorted(task for task, _ in initial.permitted_tasks if name is None or task == name)
    if not task_ids:
        return []
    rows = frappe.db.sql(
        _TASKS, {
            "project": project_name, "ids": json.dumps(task_ids), "term": term,
            "name": name, "limit": 1 if name else _CANDIDATE_LIMIT,
        },
        as_dict=True,
    )

    def eligible():
        for task in rows:
            if name is not None and task.name != name:
                continue
            try:
                if covers_project_booking(
                    **coverage, task=task.name, task_project=task.project,
                    task_created_at=_stored_time(task.creation),
                ):
                    yield task
            except ProjectBookingGrantError:
                continue

    return list(_page(eligible(), page))
