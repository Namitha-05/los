import re
from datetime import date, datetime

import frappe
from frappe.model.document import Document
from frappe.utils import add_months, cint, flt, getdate, now, nowdate, today


class LoanApplication(Document):
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
		# self.validate_user_branch()
		self.validate_nominee_share()
		self.calculate_financials()
		self.fetch_bank_from_branch()

	def on_update(self):
		# Update status to match the workflow_state
		self.status = self.workflow_state
		try:
			self.create_workflow_log()

		except Exception as e:
			frappe.log_error(message=str(e), title="Loan Workflow Log Error")

	def create_workflow_log(self):
		# Get previous workflow_state
		previous_doc = self.get_doc_before_save()
		previous_state = previous_doc.workflow_state if previous_doc else "Draft"
		current_state = self.workflow_state

		# Only create log if workflow_state changed
		if previous_state != current_state:
			# Get current user role
			roles = frappe.get_roles(frappe.session.user)
			role = roles[1] if len(roles) > 1 else roles[0] if roles else ""

			# Insert log
			frappe.get_doc(
				{
					"doctype": "Loan Application Log",
					"loan_application": self.name,
					"applicant_name": self.applicant_name or "",
					"loan_amount": self.loan_amount_requested or 0,
					"branch": self.branch or "",
					"from_state": previous_state,
					"to_state": current_state,
					"changed_by": frappe.session.user,
					"role": role,
					"changed_on": now(),
					"remarks": f"Workflow changed from {previous_state} -> {current_state}",
				}
			).insert(ignore_permissions=True)

	# pan validation
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
			frappe.throw(f"Active loan application already exists for the Pan {self.pan_number}")

	# aadhar validation
	def validate_aadhar(self):
		if not self.aadhar_number:
			return

		self.aadhar_number = self.aadhar_number.replace(" ", "").strip()
		if not self.aadhar_number.isdigit() or len(self.aadhar_number) != 12:
			frappe.throw("Aadhar number must have exactly 12 digits.")

		if self.aadhar_number[0] in ["0", "1"]:
			frappe.throw("Invalid aadhar number.The first number should not be in 0 or 1")

	# mobile validation
	def validate_mobile(self):
		if not self.mobile_number:
			return

		mobile = self.mobile_number.replace(" ", "").strip()
		self.mobile_number = mobile

		if not mobile.isdigit() or len(mobile) != 10:
			frappe.throw("Mobile number must be 10 digits and also only numbers ...Please check it.")

		if mobile[0] not in ["6", "7", "8", "9"]:
			frappe.throw("Invalid Indian mobile number.Check the first digit.")

	def validate_age(self):
		if self.date_of_birth:
			dob = getdate(self.date_of_birth)
			today_date = getdate(today())

			age = today_date.year - dob.year - ((today_date.month, today_date.day) < (dob.month, dob.day))

			if age < 18:
				frappe.throw("Applicant must be at least 18 years old")

	# cibil validation
	def validate_cibil(self):
		if not self.cibil_score:
			return

		score = cint(self.cibil_score)
		if score < 300 or score > 900:
			frappe.throw("Cibil Score must be between 300 and 900")

	# loan product rules validation
	def validate_product_rules(self):
		if not self.product:
			return

		if self.age:
			if self.age < self.product.minimum_age or self.age > self.product.maximum_age:
				frappe.throw("Applicant age is not eligible.It is less than the minimum eligibility age")

		if self.cibil_score:
			if cint(self.cibil_score) < cint(self.product.minimum_cibil_score):
				frappe.throw("Cibil score is below the requirement.(check it)")

		if self.loan_amount_requested:
			if self.loan_amount_requested > self.product.maximum_loan_amount:
				frappe.throw("Loan amount exceeds limit.Enter a lower amount.")

		if self.tenure_months:
			if (
				self.tenure_months < self.product.minimum_tenure_months
				or self.tenure_months > self.product.maximum_tenure_months
			):
				frappe.throw("Invalid tenure.Enter a value within the allowed range.")

	# nominee validation
	def validate_nominee_share(self):
		if not self.nominee_details:
			frappe.throw("At least one nominee is required.Please add nominee details.")

		total = sum(flt(row.share_percentage) for row in self.nominee_details)

		if abs(total - 100) > 0.01:
			frappe.throw(f"Total nominee share must be 100%. Currently it is: {total}%")

		for row in self.nominee_details:
			if getattr(row, "is_minor", 0) and not row.guardian_name:
				frappe.throw(f"Guardian is required for the {row.nominee_name}.Please enter guardian name.")

	# income calculations, repayment, total interest calculations
	def calculate_financials(self):
		self.total_monthly_income = flt(self.monthly_income) + flt(self.other_monthly_income)
		self.net_eligible_income = flt(self.total_monthly_income) - flt(self.existing_loan_emis)
		if self.loan_amount_requested and self.interest_rate and self.tenure_months:
			P = flt(self.loan_amount_requested)
			r = flt(self.interest_rate) / (12 * 100)
			n = cint(self.tenure_months)
			if r == 0:
				self.emi_amount = round(P / n, 2)
			else:
				emi = (P * r * (1 + r) ** n) / ((1 + r) ** n - 1)
				self.emi_amount = round(emi, 2)

		if self.emi_amount and self.tenure_months:
			self.total_repayment_amount = round(flt(self.emi_amount) * cint(self.tenure_months), 2)
			self.total_interest_payable = round(
				self.total_repayment_amount - flt(self.loan_amount_requested), 2
			)

	# fetch bank from branch
	def fetch_bank_from_branch(self):
		if self.branch:
			self.bank = frappe.db.get_value("Branch", self.branch, "bank")

	# workflow actions validation
	def before_workflow_action(self, action):
		if action == "Verify":
			if not self.checker_remarks:
				frappe.throw("Please enter the checker remarks.")
			self.checked_by = frappe.session.user
			self.checked_on = nowdate()

		elif action == "Reject":
			if not self.rejection_reason:
				frappe.throw("Please enter the rejection reason")
			self.rejected_by = frappe.session.user
			self.rejected_on = nowdate()

		elif action == "Sanction":
			if not self.sanctioner_remarks:
				frappe.throw("Please enter the sanctioner remarks")
			if not self.sanctioned_amount:
				frappe.throw("Please enter the sanctioned amount")
			self.sanctioned_by = frappe.session.user
			self.sanctioned_on = nowdate()

		elif action == "Disburse":
			if not self.disbursement_date:
				frappe.throw("Please enter the disbursement date")
			if not self.disbursed_amount:
				frappe.throw("Please enter the disbursed amount")
			self.generate_repayment_schedule()


# permission query conditions
def get_permission_query_conditions(user):
	if not user:
		user = frappe.session.user

	user_type = frappe.db.get_value("User", user, "los_user_type")

	# Head Manager
	if user_type == "Head Manager":
		return ""

	# Bank User
	elif user_type == "Bank User":
		bank = frappe.db.get_value("User", user, "los_bank")
		if bank:
			return f"`tabLoan Application`.bank = '{bank}'"

	# Branch User
	elif user_type == "Branch User":
		branch = frappe.db.get_value("User", user, "los_branch")
		if branch:
			return f"`tabLoan Application`.branch = '{branch}'"

	return ""


# whitelist functions
@frappe.whitelist()
def create_loan_disbursement(loan_application):
	loan = frappe.get_doc("Loan Application", loan_application)
	doc = frappe.new_doc("Loan Disbursement")
	doc.loan_application = loan.name
	doc.customer_name = loan.applicant_name
	doc.sanctioned_amount = loan.sanctioned_amount
	doc.branch = loan.branch
	doc.bank_account = loan.bank
	doc.disbursement_date = today()
	doc.disbursed_amount = loan.disbursed_amount
	doc.insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def get_user_branches(doctype, txt, searchfield, start, page_len, filters):
	user = frappe.session.user
	user_type = frappe.db.get_value("User", user, "los_user_type")

	if user_type == "Head Manager":
		# Head manager see all branches
		return frappe.db.sql(
			"""
            SELECT name FROM `tabBranch`
            WHERE name LIKE %(txt)s
        """,
			{"txt": f"%{txt}%"},
		)

	elif user_type == "Bank User":
		bank = frappe.db.get_value("User", user, "los_bank")
		# show only branches belongs to that bank
		return frappe.db.sql(
			"""
            SELECT name FROM `tabBranch`
            WHERE bank = %(bank)s
            AND name LIKE %(txt)s
        """,
			{"bank": bank, "txt": f"%{txt}%"},
		)

	elif user_type == "Branch User":
		branch = frappe.db.get_value("User", user, "los_branch")
		# show only their own branch
		return frappe.db.sql(
			"""
            SELECT name FROM `tabBranch`
            WHERE name = %(branch)s
        """,
			{"branch": branch},
		)

	return []


@frappe.whitelist()
def get_loan_history(loan_application):
	logs = frappe.get_all(
		"Loan Application Log",
		filters={"loan_application": loan_application},
		fields=[
			"loan_application",
			"applicant_name",
			"loan_amount",
			"changed_by",
			"role",
			"from_state",
			"to_state",
			"changed_on",
			"remarks",
		],
		order_by="changed_on desc",
		limit_page_length=1,
	)
	return logs
