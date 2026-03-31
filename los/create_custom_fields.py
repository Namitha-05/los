import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def create_user_fields():
	custom_fields = {
		"User": [
			# Section break
			{
				"fieldname": "los_section",
				"label": "LOS Access Details",
				"fieldtype": "Section Break",
				"insert_after": "language",
				"collapsible": 0,
			},
			# user type
			{
				"fieldname": "los_user_type",
				"label": "User Type",
				"fieldtype": "Select",
				"options": "Head Manager\nBank User\nBranch User",
				"insert_after": "los_section",
				"in_list_view": 1,
				"bold": 1,
				"description": "Head Manager = All banks + branches | Bank User = All branches of one bank | Branch User = One specific branch",
			},
			# column break
			{"fieldname": "los_col_break", "fieldtype": "Column Break", "insert_after": "los_user_type"},
			# Bank
			{
				"fieldname": "los_bank",
				"label": "Bank",
				"fieldtype": "Link",
				"options": "Bank",
				"insert_after": "los_col_break",
				"in_list_view": 1,
				"description": "Required for Bank User and Branch User",
				"depends_on": "eval:doc.los_user_type=='Bank User'||doc.los_user_type=='Branch User'",
			},
			# branch
			{
				"fieldname": "los_branch",
				"label": "Branch",
				"fieldtype": "Link",
				"options": "Branch",
				"insert_after": "los_bank",
				"in_list_view": 1,
				"description": "Required for Branch User only",
				"depends_on": "eval:doc.los_user_type=='Branch User'",
			},
		]
	}

	create_custom_fields(custom_fields, ignore_validate=True)
	frappe.db.commit()
	# print("LOS User fields created successfully")
