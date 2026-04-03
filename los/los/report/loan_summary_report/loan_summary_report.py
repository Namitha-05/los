import frappe


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data()
	summary = get_summary_data()

	return columns, data, None, chart, summary


def get_columns():
	return [
		{
			"label": "Application No",
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Loan Application",
			"width": 150,
		},
		{"label": "Applicant Name", "fieldname": "applicant_name", "fieldtype": "Data", "width": 150},
		{"label": "Branch", "fieldname": "branch", "fieldtype": "Data", "width": 120},
		{"label": "Loan Amount", "fieldname": "loan_amount_requested", "fieldtype": "Currency", "width": 120},
		{"label": "EMI Amount", "fieldname": "emi_amount", "fieldtype": "Currency", "width": 120},
		{
			"label": "Total Repayment",
			"fieldname": "total_repayment_amount",
			"fieldtype": "Currency",
			"width": 140,
		},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
		{"label": "Application Date", "fieldname": "application_date", "fieldtype": "Date", "width": 120},
	]


def get_data(filters):
	conditions = "WHERE docstatus < 2"

	if filters:
		if filters.get("branch"):
			conditions += " AND branch = %(branch)s"
		if filters.get("status"):
			conditions += " AND status = %(status)s"
		if filters.get("from_date"):
			conditions += " AND application_date >= %(from_date)s"

	data = frappe.db.sql(
		f"""
        SELECT
            name,
            applicant_name,
            branch,
            loan_amount_requested,
            emi_amount,
            total_repayment_amount,
            status,
            application_date
        FROM `tabLoan Application`
        {conditions}
        ORDER BY application_date DESC
    """,
		filters,
		as_dict=True,
	)

	return data


# It counts how many loan applications exist for each status.
def get_chart_data():
	data = frappe.db.sql(
		"""
        SELECT
            status,
            COUNT(name) as count
        FROM `tabLoan Application`
        WHERE docstatus < 2
        GROUP BY status
    """,
		as_dict=True,
	)

	labels = []
	values = []

	for d in data:
		labels.append(d.status)
		values.append(d.count)

	chart = {
		"data": {"labels": labels, "datasets": [{"name": "Loan Status", "values": values}]},
		"type": "bar",
	}
	return chart


def get_summary_data():
	total_loan = (
		frappe.db.sql("""
        SELECT SUM(loan_amount_requested)
        FROM `tabLoan Application`
        WHERE docstatus < 2
    """)[0][0]
		or 0
	)

	total_closed = frappe.db.count("Loan Application", {"status": "Closed"})
	total_open = frappe.db.count("Loan Application", {"status": "Sanctioned"})

	summary = [
		{"label": "Total Loan Amount", "value": total_loan, "indicator": "Blue"},
		{"label": "Loans Opened", "value": total_open, "indicator": "violet"},
		{"label": "Loans Closed", "value": total_closed, "indicator": "green"},
	]

	return summary
