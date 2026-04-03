frappe.ui.form.on("Loan Application", {
	onload: function (frm) {
		// branch filter based on the user
		frm.set_query("branch", function () {
			return {
				query: "los.los.doctype.loan_application.loan_application.get_user_branches",
			};
		});

		// Set bank and branch from User
		frappe.call({
			method: "frappe.client.get",
			args: {
				doctype: "User",
				name: frappe.session.user,
			},
			callback: function (r) {
				let user = r.message;

				if (user.los_bank) {
					frm.set_value("bank", user.los_bank);
					frm.set_df_property("bank", "read_only", 1);
				}

				if (user.los_branch) {
					frm.set_value("branch", user.los_branch);
					frm.set_df_property("branch", "read_only", 1);
				}
			},
		});
	},

	refresh: function (frm) {
		calculate_income(frm);
		calculate_emi(frm);
		calculate_age(frm);

		if (frm.doc.workflow_state === "Sanctioned" && frappe.user.has_role("LOS Admin")) {
			frm.add_custom_button("Create Disbursement", function () {
				frappe.call({
					method: "los.los.doctype.loan_application.loan_application.create_loan_disbursement",
					args: {
						loan_application: frm.doc.name,
					},
					callback: function (r) {
						if (r.message) {
							frappe.set_route("Form", "Loan Disbursement", r.message);
						}
					},
				});
			});
		}

		// watch history button
		frm.add_custom_button("Loan History", function () {
			frappe.call({
				method: "los.los.doctype.loan_application.loan_application.get_loan_history",
				args: { loan_application: frm.doc.name },
				callback: function (r) {
					if (r.message) {
						let logs = r.message;
						// Convert each log into fields for dialog
						let fields = [];
						logs.forEach((l, idx) => {
							fields.push(
								{ fieldtype: "Section Break", label: `Entry ${idx + 1}`, bold: 1 },
								{
									fieldtype: "Data",
									fieldname: "date_" + idx,
									label: "Date",
									default: l.changed_on,
									read_only: 1,
								},
								{
									fieldtype: "Data",
									fieldname: "loan_" + idx,
									label: "Loan",
									default: l.loan_application,
									read_only: 1,
								},
								{
									fieldtype: "Data",
									fieldname: "applicant_" + idx,
									label: "Applicant",
									default: l.applicant_name,
									read_only: 1,
								},
								{
									fieldtype: "Currency",
									fieldname: "amount_" + idx,
									label: "Amount",
									default: l.loan_amount,
									read_only: 1,
								},
								{
									fieldtype: "Data",
									fieldname: "user_" + idx,
									label: "User",
									default: l.changed_by,
									read_only: 1,
								},
								{
									fieldtype: "Data",
									fieldname: "role_" + idx,
									label: "Role",
									default: l.role,
									read_only: 1,
								},
								{
									fieldtype: "Data",
									fieldname: "from_" + idx,
									label: "From",
									default: l.from_state || "",
									read_only: 1,
								},
								{
									fieldtype: "Data",
									fieldname: "to_" + idx,
									label: "To",
									default: l.to_state || "",
									read_only: 1,
								}
							);

							// Include remarks only if it exists
							if (l.remarks && l.remarks.trim() !== "") {
								fields.push({
									fieldtype: "Small Text",
									fieldname: "remarks_" + idx,
									label: "Remarks",
									default: l.remarks,
									read_only: 1,
								});
							}
						});

						let d = new frappe.ui.Dialog({
							title: "Loan Movement History",
							fields: fields,
							size: "large",
						});
						d.show();
					} else {
						frappe.msgprint(__("No loan history found"));
					}
				},
			});
		});
	},

	validate: function (frm) {
		if (!frm.doc.age || frm.doc.age <= 0) {
			frappe.throw("Invalid Date of Birth");
		}
		if (frm.doc.age < 18) {
			frappe.throw("Applicant must be at least 18 years old.");
		}

		//Aadhar Validation

		let aadhar = frm.doc.aadhar_number;
		if (aadhar) {
			if (aadhar.length !== 12) {
				frappe.throw("Aadhaar must be 12 digits");
			}

			if (!/^\d+$/.test(aadhar)) {
				frappe.throw("Aadhaar must contain only numbers.Don't enter any digits");
			}

			// Duplicate check
			return frappe
				.call({
					method: "frappe.client.get_list",
					args: {
						doctype: "Loan Application",
						filters: {
							aadhar_number: aadhar,
						},
						fields: ["name"],
					},
				})
				.then(function (r) {
					if (r.message.length > 0 && r.message[0].name !== frm.doc.name) {
						frappe.throw("This Aadhaar already exists in another Loan Application");
					}
				});
		}
	},

	// dob --> Age calculation, Validation
	date_of_birth: function (frm) {
		calculate_age(frm);
	},

	// pan uppercase
	pan_number: function (frm) {
		if (frm.doc.pan_number) {
			frm.set_value("pan_number", frm.doc.pan_number.toUpperCase());
		}
	},

	loan_product: function (frm) {
		if (frm.doc.loan_product) {
			frappe.db
				.get_value("Loan Product", frm.doc.loan_product, [
					"category",
					"interest_rate",
					"processing_fee",
				])
				.then(function (product) {
					frm.set_value("loan_category", product.message.category);
					frm.set_value("interest_rate", product.message.interest_rate);
					frm.set_value("processing_fee_amount", product.message.processing_fee);
				});
		}
	},

	// Emi triggers
	loan_amount_requested: calculate_emi,
	interest_rate: calculate_emi,
	tenure_months: calculate_emi,

	// Income triggers
	monthly_income: calculate_income,
	other_monthly_income: calculate_income,
	existing_loan_emis: calculate_income,
});

// Age calculation
function calculate_age(frm) {
	if (frm.doc.date_of_birth) {
		let dob = new Date(frm.doc.date_of_birth);
		let today = new Date();
		let age = today.getFullYear() - dob.getFullYear();
		let m = today.getMonth() - dob.getMonth();

		if (m < 0 || (m === 0 && today.getDate() < dob.getDate())) {
			age--;
		}
		frm.set_value("age", age);
		if (age <= 0) {
			frappe.msgprint("Invalid Date of Birth. Enter a valid date of birth");
			frm.set_value("date_of_birth", "");
			frm.set_value("age", "");
		}
		if (age < 18) {
			frappe.msgprint("Applicant must be at least 18 years old");
			frm.set_value("date_of_birth", "");
			frm.set_value("age", "");
		}
	}
}

// Income calculation
function calculate_income(frm) {
	let total_income = (frm.doc.monthly_income || 0) + (frm.doc.other_monthly_income || 0);
	frm.set_value("total_monthly_income", total_income);

	let net_income = total_income - (frm.doc.existing_loan_emis || 0);
	frm.set_value("net_eligible_income", net_income);
}

// EMI calculation
function calculate_emi(frm) {
	let P = frm.doc.loan_amount_requested;
	let r = frm.doc.interest_rate;
	let n = frm.doc.tenure_months;

	if (P && r && n) {
		let rate = r / (12 * 100);
		let emi = 0;

		if (rate === 0) {
			emi = P / n;
		} else {
			emi = (P * rate * Math.pow(1 + rate, n)) / (Math.pow(1 + rate, n) - 1);
		}

		emi = Math.round(emi * 100) / 100;
		frm.set_value("emi_amount", emi);

		let total_repayment = emi * n;
		frm.set_value("total_repayment_amount", Math.round(total_repayment * 100) / 100);

		let total_interest = total_repayment - P;
		frm.set_value("total_interest_payable", Math.round(total_interest * 100) / 100);
	}
}
