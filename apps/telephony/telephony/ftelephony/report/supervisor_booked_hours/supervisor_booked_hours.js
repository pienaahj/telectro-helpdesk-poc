frappe.query_reports["Supervisor Booked Hours"] = {
	onload(report) {
		frappe.telectro_booked_hours_filters?.setup(report, "Supervisor Booked Hours");
	},
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
			options: [
				"Daily Summary", "Technician Breakdown", "Customer Breakdown",
				"Work Context Breakdown", "Project / Reference Breakdown",
				"Service Area Breakdown", "Activity Breakdown", "Booking Detail",
			],
			default: "Daily Summary",
		},
		{ fieldname: "company", label: __("Company"), fieldtype: "Data" },
		{ fieldname: "employee", label: __("Technician (Employee)"), fieldtype: "Data" },
		{
			fieldname: "work_context",
			label: __("Work Context"),
			fieldtype: "Select",
			options: ["", "Helpdesk", "Project", "Customer Support", "Internal"],
		},
		{ fieldname: "service_area", label: __("Service Area"), fieldtype: "Autocomplete", ignore_validation: true },
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
		{ fieldname: "customer", label: __("Customer"), fieldtype: "Autocomplete", ignore_validation: true },
		{ fieldname: "activity_type", label: __("Activity Type"), fieldtype: "Data" },
		{
			fieldname: "customer_type",
			label: __("Customer Attribution"),
			fieldtype: "Select",
			options: ["", "Listed Customer", "Unlisted Customer", "Unattributed", "Not applicable"],
		},
		{
			fieldname: "reference_state",
			label: __("Reference Status"),
			fieldtype: "Select",
			options: ["", "Available", "Restricted reference", "Missing historical reference", "Unattributed", "Not applicable"],
		},
		{
			fieldname: "reference_kind",
			label: __("Primary Work Reference"),
			fieldtype: "Select",
			options: ["", "Snapfix", "Ticket", "Project", "Task", "No visible reference"],
		},
		{ fieldname: "ticket", label: __("Helpdesk Ticket"), fieldtype: "Data" },
		{ fieldname: "project", label: __("Project"), fieldtype: "Data" },
		{ fieldname: "task", label: __("Task"), fieldtype: "Data" },
		{ fieldname: "snapfix_reference", label: __("Snapfix Reference"), fieldtype: "Data" },
	],
	formatter(value, row, column, data, default_formatter) {
		if (column.fieldtype === "Data" && typeof value === "string") {
			value = frappe.utils.escape_html(value);
		}
		return default_formatter(value, row, column, data);
	},
};
