frappe.query_reports["Loan Summary Report"] = {
	filters: [
		{
			fieldname: "branch",
			label: "Branch",
			fieldtype: "Link",
			options: "Branch",
		},
		{
			fieldname: "status",
			label: "Status",
			fieldtype: "Select",
			options: ["", "Pending", "Sanctioned", "Rejected", "Closed"],
		},
		{
			fieldname: "from_date",
			label: "From Date",
			fieldtype: "Date",
		},
	],
};
