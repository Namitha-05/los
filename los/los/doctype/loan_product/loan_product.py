import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt


class LoanProduct(Document):
	def validate(self):
		self.validate_loan_amounts()
		self.validate_tenure()
		self.validate_age()
		self.validate_interest_rate()
		self.validate_cibil_score()
		self.validate_collateral_coverage()

	def validate_loan_amounts(self):
		minimum_amount = flt(self.minimum_loan_amount)
		maximum_amount = flt(self.maximum_loan_amount)

		if minimum_amount <= 0:
			frappe.throw("Minimum Loan Amount must be greater than 0.")

		if maximum_amount <= 0:
			frappe.throw("Maximum Loan Amount must be greater than 0.")

		if minimum_amount >= maximum_amount:
			frappe.throw(
				f"Minimum Loan Amount ₹{minimum_amount:,.0f} must be "
				f"less than Maximum Loan Amount ₹{maximum_amount:,.0f}."
			)

	def validate_tenure(self):
		minimum_tenure = cint(self.minimum_tenure_months)
		maximum_tenure = cint(self.maximum_tenure_months)

		if minimum_tenure <= 0:
			frappe.throw("Minimum Tenure must be at least 1 month.")

		if minimum_tenure >= maximum_tenure:
			frappe.throw(
				f"Minimum Tenure ({minimum_tenure} months) must be less than "
				f"Maximum Tenure ({maximum_tenure} months)."
			)

	def validate_age(self):
		minimum_age = cint(self.minimum_age)
		maximum_age = cint(self.maximum_age)

		if minimum_age < 18:
			frappe.throw("Minimum Age cannot be less than 18 years.")

		if maximum_age > 75:
			frappe.throw("Maximum Age cannot exceed 75 years.")

		if minimum_age >= maximum_age:
			frappe.throw(f"Minimum Age ({minimum_age}) must be less than Maximum Age ({maximum_age}).")

	def validate_interest_rate(self):
		interest_rate = flt(self.interest_rate)

		if interest_rate <= 0:
			frappe.throw("Interest Rate must be greater than 0.")

		if interest_rate > 50:
			frappe.throw("Interest Rate cannot exceed 50%. Please verify the rate entered.")

	def validate_cibil_score(self):
		if self.minimum_cibil_score:
			minimum_cibil_score = cint(self.minimum_cibil_score)

			if not 300 <= minimum_cibil_score <= 900:
				frappe.throw("Minimum CIBIL Score must be between 300 and 900.")

	def validate_collateral_coverage(self):
		if not self.collateral_required:
			return

		collateral_coverage = flt(self.collateral_coverage)

		if not collateral_coverage:
			frappe.throw("Collateral Coverage (%) is required since Collateral is required.")

		if collateral_coverage < 100:
			frappe.msgprint(
				"Warning: Collateral Coverage is below 100%.",
				indicator="orange",
				alert=True,
			)
