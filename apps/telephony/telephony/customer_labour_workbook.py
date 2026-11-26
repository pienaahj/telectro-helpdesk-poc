"""Create the scoped Customer Labour Cost Analysis workbook entirely in memory."""

from collections import defaultdict
from datetime import timedelta
from io import BytesIO

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule, DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo

from telephony.booked_hours import duration_rows

HOURS_PER_US = 3_600_000_000
HEADER = 8
FIRST = HEADER + 1
TEAL = "12464A"
BLUE = "E2F0FE"
RULE = "C6DCE2"
HOURS = "#,##0.000"
RAND = '"R"#,##0.00;[Red]("R"#,##0.00);"R"0.00'
PERCENT = "0.0%;[Red](0.0%);0.0%"
RATES = "Technician Rates"
BREAKDOWN = "Customer Labour Breakdown"
SUMMARY = "Customer Financial Summary"
INTERNAL = ("Internal", "", "")
UNATTRIBUTED = ("Unattributed", "", "")


def _account(row):
    if row["work_context"] == "Internal":
        return INTERNAL
    if row["customer"]:
        return ("Listed Customer", row["customer"], "")
    if row["unlisted_customer"]:
        return ("Unlisted Customer", row["unlisted_customer"], row["company"])
    return UNATTRIBUTED


def _aggregate(bookings, start, end):
    source = [
        {
            "from_time": row["from_time"], "to_time": row["to_time"],
            "docstatus": row["docstatus"], "emergency": row["emergency"],
            "account": _account(row), "employee": row["employee"], "company": row["company"],
        }
        for row in bookings
    ]
    return duration_rows(source, start, end, group_by=("account", "company", "employee"), by_day=False)


def _text(cell, value):
    # Explicitly force a string even if OpenPyXL recognized an equals sign.
    cell.value = str(value)
    cell.data_type = "s"


def _write_row(sheet, row, values):
    for col, value in enumerate(values, 1):
        if isinstance(value, str):
            _text(sheet.cell(row, col), value)
        elif value is not None:
            sheet.cell(row, col, value)


def _band(sheet, row, columns, value, *, dark=False):
    sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=columns)
    cell = sheet.cell(row, 1)
    _text(cell, value)
    cell.fill = PatternFill("solid", fgColor=TEAL if dark else "EAF4F4")
    cell.font = Font(name="Calibri", size=19 if dark else 11, bold=True, color="FFFFFF" if dark else TEAL)
    cell.alignment = Alignment(vertical="center", indent=1)
    sheet.row_dimensions[row].height = 34 if dark else 23


def _layout(sheet, title, info, widths, headers):
    sheet.sheet_view.showGridLines = False
    sheet.freeze_panes = f"A{FIRST}"
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.sheet_properties.tabColor = TEAL
    for col, width in enumerate(widths, 1):
        sheet.column_dimensions[get_column_letter(col)].width = width
    _band(sheet, 1, len(widths), title, dark=True)
    for row, line in enumerate(info, 2):
        sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=len(widths))
        cell = sheet.cell(row, 1)
        _text(cell, line)
        cell.font = Font(name="Calibri", size=11, color="32555A", bold=row == 2)
        cell.alignment = Alignment(indent=1, wrap_text=True, vertical="center")
        sheet.row_dimensions[row].height = 30 if row == 3 else 19
    sheet.merge_cells(start_row=7, start_column=1, end_row=7, end_column=len(widths))
    notice = sheet["A7"]
    _text(notice, "CONFIDENTIAL — MANAGEMENT ONLY. Contains commercially sensitive labour cost and revenue information "
          "when populated. Financial inputs stay in this workbook and are not stored in ERPNext.")
    notice.font = Font(name="Calibri", size=10, bold=True, color="32555A")
    notice.alignment = Alignment(indent=1, wrap_text=True, vertical="center")
    sheet.row_dimensions[7].height = 30
    _headers(sheet, HEADER, headers)


def _headers(sheet, row, headers):
    _write_row(sheet, row, headers)
    for cell in sheet[row][:len(headers)]:
        cell.fill = PatternFill("solid", fgColor=TEAL)
        cell.font = Font(name="Calibri", color="FFFFFF", bold=True, size=11)
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    sheet.row_dimensions[row].height = 33


def _table(sheet, name, columns, length):
    if length:
        table = Table(displayName=name, ref=f"A{HEADER}:{get_column_letter(columns)}{HEADER+length}")
        table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        sheet.add_table(table)
        for row in range(FIRST, FIRST+length):
            sheet.row_dimensions[row].height = 21


def _input(sheet, column, length):
    validate = DataValidation(type="custom", formula1=f"ISNUMBER({column}{FIRST})", allow_blank=True)
    validate.errorTitle = "Enter an amount"
    validate.error = "Enter a number or leave the cell blank. Zero is a valid entered amount."
    validate.errorStyle = "stop"
    validate.showErrorMessage = True
    if length:
        sheet.add_data_validation(validate)
        validate.add(f"{column}{FIRST}:{column}{HEADER+length}")
    for row in range(FIRST, FIRST+length):
        cell = sheet[f"{column}{row}"]
        cell.number_format = RAND
        cell.fill = PatternFill("solid", fgColor=BLUE)
        cell.font = Font(name="Calibri", bold=True, color="174B78")
        cell.border = Border(bottom=Side(style="thin", color=RULE))


def _range(sheet, field, length):
    return f"'{sheet}'!${field}${FIRST}:${field}${max(FIRST, HEADER+length)}"


def _current(field, length):
    return f"INDEX(${field}${FIRST}:${field}${HEADER+length},ROW()-{HEADER})"


def _formula(sheet, row, col, value, format_code=RAND):
    cell = sheet.cell(row, col, f"={value}")
    cell.number_format = format_code


def _cost(key, key_range, readiness, costs):
    return (
        f'IF(SUMIF({key_range},{key},{readiness})=COUNTIF({key_range},{key}),'
        f'SUMIF({key_range},{key},{costs}),"")'
    )


def _incomplete_total(cells, count):
    return f'IF(COUNT({cells})={count},SUM({cells}),"")'


def make_workbook(bookings, start, end, employee_labels, companies, *, dev_test=False):
    rows = _aggregate(bookings, start, end)
    work = defaultdict(int)
    account_hours = defaultdict(int)
    context_hours = defaultdict(int)
    company_account_hours = defaultdict(int)
    for row in rows:
        identity = (row["employee"], row["company"])
        account, amount = row["account"], row["booked_us"]
        work[identity] += amount
        account_hours[account] += amount
        context_hours[account if account in (INTERNAL, UNATTRIBUTED) else "customer"] += amount
        if account not in (INTERNAL, UNATTRIBUTED):
            company_account_hours[account, row["company"]] += amount

    identities = sorted(work, key=lambda key: (employee_labels.get(key[0], "").casefold(), key))
    rate_keys = {key: index for index, key in enumerate(identities, 1)}
    accounts = sorted((key for key in account_hours if key not in (INTERNAL, UNATTRIBUTED)),
                      key=lambda key: (key[1].casefold(), key))
    keys = {key: i for i, key in enumerate(accounts, 1)} | {INTERNAL: -1, UNATTRIBUTED: -2}
    company_keys = {key: i for i, key in enumerate(sorted(company_account_hours), 1)}
    display = lambda account: account[1] or account[0]
    label = lambda employee: employee_labels.get(employee, "Technician")
    period = f"{start:%d %b %Y} – {end.date() - timedelta(days=1):%d %b %Y} (site dates)"
    company_scope = ", ".join(sorted(companies)) if companies else "No Company in the current grant"
    # Scope plus all authorized company names remain available without wrapping an unbounded title.
    if len(company_scope) > 180:
        company_scope = f"{len(companies)} Companies in the current grant · contributing Companies are listed in the data"
    scope_label = "Controlled DEV test scope" if dev_test else "Reporting grant scope"
    base = (
        period,
        f"{scope_label} · {company_scope}. Includes Draft and Submitted work.",
    )

    wb = Workbook()
    rates = wb.active
    rates.title = RATES
    breakdown = wb.create_sheet(BREAKDOWN)
    summary = wb.create_sheet(SUMMARY)
    wb.active = summary

    _layout(rates, "Technician Rates", (*base,
            "Enter a fully loaded hourly cost in each blue cell. Leave unknown rates blank. Enter 0 only for a zero rate."),
            (28, 22, 27, 17, 26),
            ("Technician", "Employee", "Company", "Booked hours", "Hourly labour cost (R)"))
    _text(rates["F8"], "Rate key")
    rates.column_dimensions["F"].hidden = True
    for row, identity in enumerate(identities, FIRST):
        employee, company = identity
        _write_row(rates, row, (label(employee), employee, company, work[identity]/HOURS_PER_US,
                                None, rate_keys[identity]))
        rates[f"D{row}"].number_format = HOURS
    _table(rates, "TechnicianRates", 6, len(identities))
    _input(rates, "E", len(identities))

    _layout(breakdown, "Customer Labour Breakdown", (*base,
            "Technician rates link to the Rates sheet. Internal and unattributed hours stay outside Customer labour."),
            (28, 22, 26, 19, 25, 15, 19, 20),
            ("Customer / work", "Attribution", "Technician", "Employee", "Company",
             "Booked hours", "Linked rate (R)", "Labour cost (R)"))
    for col, title in zip("IJKL", ("Rate key", "Account key", "Cost ready", "Company account key")):
        _text(breakdown[f"{col}{HEADER}"], title)
        breakdown.column_dimensions[col].hidden = True
    data = sorted(rows, key=lambda row: (row["account"] in (INTERNAL, UNATTRIBUTED),
                                        display(row["account"]).casefold(), row["account"],
                                        row["company"], label(row["employee"]), row["employee"]))
    rate_range, rate_ids = (_range(RATES, field, len(identities)) for field in ("E", "F"))
    for i, row in enumerate(data, FIRST):
        account, employee, company = row["account"], row["employee"], row["company"]
        _write_row(breakdown, i, (display(account), account[0], label(employee), employee,
                                  company, row["booked_us"]/HOURS_PER_US, None, None,
                                  rate_keys[employee, company], keys[account], None,
                                  company_keys.get((account, company))))
        breakdown[f"F{i}"].number_format = HOURS
        key = _current("I", len(data))
        _formula(breakdown, i, 7, f'IF(COUNTIFS({rate_ids},{key},{rate_range},"<>",{rate_range},">=0")+'
                                  f'COUNTIFS({rate_ids},{key},{rate_range},"<0")=1,'
                                  f'SUMIF({rate_ids},{key},{rate_range}),"")')
        linked = _current("G", len(data))
        _formula(breakdown, i, 8, f'IF(ISNUMBER({linked}),{_current("F",len(data))}*{linked},"")')
        _formula(breakdown, i, 11, f"--ISNUMBER({_current('H', len(data))})", "0")
    _table(breakdown, "CustomerLabour", 12, len(data))

    _layout(summary, "Customer Financial Summary", (*base,
            "1  Enter Technician rates on Technician Rates.   2  Enter Customer revenue excluding VAT in the blue cells below.",
            "Blank financial values are unknown. Enter zero explicitly where applicable.",
            "Labour contribution excludes other costs and overheads. Only accounts with authorized recorded work are included."),
            (29, 27, 21, 14, 17, 18, 18, 17, 15, 18),
            ("Customer", "Company scope", "Attribution", "Booked hours", "Labour cost (R)",
             "Revenue excl. VAT (R)", "Labour Contribution (R)", "Labour Contribution Margin",
             "Labour cost %", "Revenue per hour (R)"))
    _text(summary["K8"], "Account key")
    summary.column_dimensions["K"].hidden = True
    key_range, costs, readiness, company_range = (_range(BREAKDOWN, col, len(data)) for col in "JHKL")
    n = len(accounts)
    for i, account in enumerate(accounts, FIRST):
        scope = sorted(company for key, company in company_account_hours if key == account)
        scope_label = scope[0] if len(scope) == 1 else f"{len(scope)} Companies · see breakdown below"
        _write_row(summary, i, (display(account), scope_label, account[0],
                                account_hours[account]/HOURS_PER_US, None, None, None, None, None, None, keys[account]))
        summary[f"D{i}"].number_format = HOURS
        cost = _current("E", n)
        revenue = _current("F", n)
        hours = _current("D", n)
        both = f'COUNT({cost},{revenue})=2'
        _formula(summary, i, 5, _cost(_current("K", n), key_range, readiness, costs))
        _formula(summary, i, 7, f'IF({both},{revenue}-{cost},"")')
        _formula(summary, i, 8, f'IF(AND({both},{revenue}<>0),({revenue}-{cost})/{revenue},"")', PERCENT)
        _formula(summary, i, 9, f'IF(AND({both},{revenue}<>0),{cost}/{revenue},"")', PERCENT)
        _formula(summary, i, 10, f'IF(AND(COUNT({revenue})=1,{hours}<>0),{revenue}/{hours},"")')
    _table(summary, "AccountComparison", 11, n)
    _input(summary, "F", n)
    if n:
        summary.conditional_formatting.add(f"D{FIRST}:D{HEADER+n}", DataBarRule(
            start_type="num", start_value=0, end_type="max", color="93CBC5"))
        summary.conditional_formatting.add(f"G{FIRST}:G{HEADER+n}", CellIsRule(
            operator="lessThan", formula=["0"], fill=PatternFill("solid", fgColor="FCE8E5")))
    else:
        _text(summary[f"A{FIRST}"], "No Customer-attributed bookings in this scope and period.")

    total = max(FIRST, HEADER+n) + 1
    _write_row(summary, total, ("Customer totals", None, None, context_hours["customer"]/HOURS_PER_US))
    summary[f"D{total}"].number_format = HOURS
    if n:
        for col, field in ((5, "E"), (6, "F")):
            _formula(summary, total, col, _incomplete_total(f"{field}{FIRST}:{field}{HEADER+n}", n))
        cost, revenue, hours = (f"{field}{total}" for field in "EFD")
        both = f"COUNT({cost},{revenue})=2"
        _formula(summary, total, 7, f'IF({both},{revenue}-{cost},"")')
        _formula(summary, total, 8, f'IF(AND({both},{revenue}<>0),({revenue}-{cost})/{revenue},"")', PERCENT)
        _formula(summary, total, 9, f'IF(AND({both},{revenue}<>0),{cost}/{revenue},"")', PERCENT)
        _formula(summary, total, 10, f'IF(AND(COUNT({revenue})=1,{hours}<>0),{revenue}/{hours},"")')
    for cell in summary[total][:10]:
        cell.font = Font(name="Calibri", bold=True, color=TEAL)
        cell.fill = PatternFill("solid", fgColor="EAF4F4")

    _band(summary, total+3, 5, "Authorized time and labour reconciliation")
    _headers(summary, total+4, ("Work category", "Booked hours", "Labour cost (R)"))
    for i, account in enumerate(("customer", INTERNAL, UNATTRIBUTED, "total"), total+5):
        captions = {"customer": "Customer-attributed", "total": "Total authorized"}
        amount = sum(work.values()) if account == "total" else context_hours[account]
        _write_row(summary, i, (captions.get(account, account[0] if isinstance(account, tuple) else account),
                                amount/HOURS_PER_US))
        summary[f"B{i}"].number_format = HOURS
        if account == "total":
            value = _incomplete_total(f"C{total+5}:C{total+7}", 3)
        elif account == "customer":
            value = f'IF(COUNT(E{total})=1,E{total},"")' if n else "0"
        else:
            value = _cost(keys[account], key_range, readiness, costs)
        _formula(summary, i, 3, value)

    # Account revenue is entered once. Companies have their own hours and costs.
    if any(sum(1 for item in company_account_hours if item[0] == account) > 1 for account in accounts):
        _band(summary, total+11, 5, "Customer hours and labour cost by Company")
        _headers(summary, total+12, ("Customer", "Company", "Attribution", "Booked hours", "Labour cost (R)"))
        for i, (account, company) in enumerate(sorted(company_account_hours), total+13):
            _write_row(summary, i, (display(account), company, account[0],
                                    company_account_hours[account, company]/HOURS_PER_US))
            summary[f"D{i}"].number_format = HOURS
            _formula(summary, i, 5, _cost(company_keys[account, company], company_range, readiness, costs))

    stream = BytesIO()
    wb.save(stream)
    return stream.getvalue()
