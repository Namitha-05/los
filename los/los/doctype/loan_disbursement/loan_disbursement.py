import frappe
from frappe.model.document import Document


class LoanDisbursement(Document):
	def on_submit(self):
		loan = frappe.get_doc("Loan Application", self.loan_application)

		total_disbursed = loan.disbursed_amount or 0
		total_disbursed += self.disbursed_amount

		loan.db_set("disbursed_amount", total_disbursed)

		if total_disbursed >= loan.sanctioned_amount:
			loan.db_set("status", "Disbursed")
			loan.workflow_state = "Disbursed"

		else:
			loan.db_set("status", "Partially Disbursed")
			loan.workflow_state = "Partially Disbursed"
