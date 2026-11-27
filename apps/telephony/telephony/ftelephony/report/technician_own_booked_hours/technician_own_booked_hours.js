frappe.query_reports["Technician Own Booked Hours"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -6),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "view",
			label: __("View"),
			fieldtype: "Select",
			options: ["Daily Summary", "Booking Detail"],
			default: "Daily Summary",
		},
		{
			fieldname: "work_context",
			label: __("Work Context"),
			fieldtype: "Select",
			options: ["", "Helpdesk", "Project", "Customer Support", "Internal"],
		},
		{ fieldname: "service_area", label: __("Service Area"), fieldtype: "Data" },
		{
			fieldname: "work_origin",
			label: __("Work Origin"),
			fieldtype: "Select",
			options: ["", "Direct / Ad-hoc", "Snapfix", "Other", "Not applicable"],
		},
		{
			fieldname: "emergency",
			label: __("Emergency / Unplanned"),
			fieldtype: "Select",
			options: ["", "Yes", "No"],
		},
		{ fieldname: "customer", label: __("Customer"), fieldtype: "Data" },
		{ fieldname: "project", label: __("Project"), fieldtype: "Data" },
		{ fieldname: "task", label: __("Task"), fieldtype: "Data" },
		{ fieldname: "ticket", label: __("Helpdesk Ticket"), fieldtype: "Data" },
		{ fieldname: "snapfix_reference", label: __("Snapfix Reference"), fieldtype: "Data" },
	],
	formatter(value, row, column, data, default_formatter) {
		if (column.fieldtype === "Data" && typeof value === "string") {
			value = frappe.utils.escape_html(value);
		}
		return default_formatter(value, row, column, data);
	},
};
