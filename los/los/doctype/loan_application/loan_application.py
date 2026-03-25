import re
from datetime import date, datetime

import frappe
from frappe.model.document import Document
from frappe.utils import cint


class LoanApplication(Document):
	# For reducing repeated database hits
	def validate(self):
		self.product = None
		if self.loan_product:
			self.product = frappe.get_cached_doc("Loan Product", self.loan_product)

		self.validate_pan()
		self.validate_aadhar()
		self.validate_mobile()
		self.validate_age()
		self.validate_cibil()
		self.validate_product_rules()

	def validate_pan(self):
		if not self.pan_number:
			return

		self.pan_number = self.pan_number.upper().strip()
		pattern = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"

		if not re.match(pattern, self.pan_number):
			frappe.throw("Invalid PAN Number format (ABCDE1234F).")

		existing = frappe.db.exists(
			"Loan Application",
			{
				"pan_number": self.pan_number,
				"name": ("!=", self.name),
				"workflow_state": ("not in", ["Rejected", "Closed"]),
			},
		)
		if existing:
			frappe.throw(f"Active Loan Application already exists for PAN {self.pan_number}")

	def validate_aadhar(self):
		if not self.aadhar_number:
			return

		self.aadhar_number = self.aadhar_number.replace(" ", "").strip()
		if not self.aadhar_number.isdigit() or len(self.aadhar_number) != 12:
			frappe.throw("Aadhar Number must have exactly 12 digits.")

		if self.aadhar_number[0] in ["0", "1"]:
			frappe.throw("Invalid Aadhar Number.")

	def validate_mobile(self):
		if not self.mobile_number:
			return

		mobile = self.mobile_number.replace(" ", "").strip()
		self.mobile_number = mobile
		if not mobile.isdigit() or len(mobile) != 10:
			frappe.throw("Mobile number must be 10 digits.")

		if mobile[0] not in ["6", "7", "8", "9"]:
			frappe.throw("Invalid Indian mobile number.")

	def validate_age(self):
		if self.date_of_birth:
			if isinstance(self.date_of_birth, str):
				dob = datetime.strptime(self.date_of_birth, "%Y-%m-%d").date()
			else:
				dob = self.date_of_birth

			today = date.today()
			age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
			self.age = age

	def validate_cibil(self):
		if not self.cibil_score:
			return
		score = cint(self.cibil_score)
		if score < 300 or score > 900:
			frappe.throw("CIBIL Score must be between 300 and 900.")

	def validate_product_rules(self):
		if not self.product:
			return

		if self.age:
			if self.age < self.product.minimum_age or self.age > self.product.maximum_age:
				frappe.throw("Applicant age not eligible for this Loan Product.")

		if self.cibil_score:
			if cint(self.cibil_score) < cint(self.product.minimum_cibil_score):
				frappe.throw("CIBIL score below minimum requirement.")

		if self.loan_amount_requested:
			if self.loan_amount_requested > self.product.maximum_loan_amount:
				frappe.throw("Loan amount exceeds product limit.")

		if self.tenure_months:
			if (
				self.tenure_months < self.product.minimum_tenure_months
				or self.tenure_months > self.product.maximum_tenure_months
			):
				frappe.throw("Tenure not allowed for this product.")
