import frappe


def set_user_access_permissions(doc, method=None):
	print("FUNCTION TRIGGERED")
	"""
    Enforces LOS access permissions based on user type.
    This should be called in the User DocType's `after_save` hook.
    """

	user = doc.name
	user_type = doc.get("los_user_type")

	# Skip system users
	if user in ["Administrator", "Guest"]:
		return

	# Skip if no user type assigned
	if not user_type:
		return

	# Clear old permissions first
	clear_los_permissions(user)

	# Head Manager = full access
	if user_type == "Head Manager":
		frappe.msgprint("Head Manager: Full access granted to all banks and branches.")

	# Bank User = restrict to bank only
	elif user_type == "Bank User":
		bank = doc.get("los_bank")
		if not bank:
			frappe.throw("Please assign a Bank for Bank User.")
		add_user_permission(user, "Bank", bank)
		frappe.msgprint(f"Bank User: Access granted to all branches of {bank}.")

	# Branch User = restrict to branch + bank
	elif user_type == "Branch User":
		bank = doc.get("los_bank")
		branch = doc.get("los_branch")
		if not bank:
			frappe.throw("Please assign a Bank for Branch User.")
		if not branch:
			frappe.throw("Please assign a Branch for Branch User.")

		# Check branch belongs to bank
		branch_bank = frappe.db.get_value("Branch", branch, "bank")
		if branch_bank != bank:
			frappe.throw(f"Branch '{branch}' does not belong to Bank '{bank}'.")

		add_user_permission(user, "Bank", bank)
		add_user_permission(user, "Branch", branch)
		frappe.msgprint(f"Branch User: Access restricted to {branch} of {bank}.")


def add_user_permission(user, doctype, value):
	"""
	Adds a User Permission record
	"""
	if frappe.db.exists("User Permission", {"user": user, "allow": doctype, "for_value": value}):
		return

	frappe.get_doc(
		{
			"doctype": "User Permission",
			"user": user,
			"allow": doctype,
			"for_value": value,
			"apply_to_all_doctypes": 1,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()


def clear_los_permissions(user):
	"""
	Clears old User Permissions for Bank & Branch
	"""
	frappe.db.delete("User Permission", {"user": user, "allow": ("in", ["Bank", "Branch"])})
	frappe.db.commit()
