"""Private top-level boundary for one dedicated technician booking POST."""

from contextlib import contextmanager
from contextvars import ContextVar


_active_booking = ContextVar("_active_booking_transaction", default=False)


class BookingTransactionDenied(PermissionError):
    def __init__(self):
        super().__init__("Technician booking is not available.")


class BookingTransactionCleanupError(RuntimeError):
    def __init__(self):
        super().__init__("Technician booking transaction cleanup failed.")


@contextmanager
def _top_level_booking_transaction(*, expected_command):
    """Own failure rollback; leave successful request commit to Frappe."""
    if _active_booking.get():
        raise BookingTransactionDenied()
    try:
        import frappe

        local = frappe.local
        request = local.request
        form_dict = local.form_dict
        user = frappe.session.user
        db = local.db
        if (
            type(expected_command) is not str
            or not expected_command
            or request.method != "POST"
            or request.path != "/api/method/" + expected_command
            or form_dict.cmd != expected_command
            or type(user) is not str
            or not user.strip()
            or user in ("Guest", "Administrator")
        ):
            raise BookingTransactionDenied()
    except BookingTransactionDenied:
        raise
    except Exception as exc:
        raise BookingTransactionDenied() from exc

    token = _active_booking.set(True)
    try:
        try:
            yield
        except BaseException:
            try:
                db.rollback()
            except BaseException as cleanup_error:
                raise BookingTransactionCleanupError() from cleanup_error
            raise
    finally:
        _active_booking.reset(token)
