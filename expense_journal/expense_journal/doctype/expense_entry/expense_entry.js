// Copyright (c) 2020, Bantoo and contributors
// For license information, please see license.txt

frappe.provide("expense_entry.expense_entry");

function update_totals(frm, cdt, cdn){
	var items = locals[cdt][cdn];
    var total = 0;
    var quantity = 0;
    frm.doc.expenses.forEach(
        function(items) { 
            total += items.amount;
            quantity +=1;
        });
    frm.set_value("total", total);
    refresh_field("total");
    frm.set_value("quantity", quantity);
    refresh_field("quantity");
}

frappe.ui.form.on('Expense Entry Item', {
    amount: function(frm, cdt, cdn) {
        update_totals(frm, cdt, cdn);
    },
    expenses_remove: function(frm, cdt, cdn){
        update_totals(frm, cdt, cdn);
    },
    expenses_add: function(frm, cdt, cdn){
        var d = locals[cdt][cdn];
        
        if((d.cost_center === "" || typeof d.cost_center == 'undefined')) { 

            if (cur_frm.doc.default_cost_center != "" || typeof cur_frm.doc.default_cost_center != 'undefined') {
                
                d.cost_center = cur_frm.doc.default_cost_center; 
                cur_frm.refresh_field("expenses");
            }
        }
        if((d.project === "" || typeof d.project == 'undefined')) { 

            if (cur_frm.doc.default_project != "" || typeof cur_frm.doc.default_project != 'undefined') {
                
                d.project = cur_frm.doc.default_project; 
                cur_frm.refresh_field("expenses");
            }
        }
    }
    
});


frappe.ui.form.on('Expense Entry', {
    before_save: function(frm) { 

        $.each(frm.doc.expenses, function(i, d) { 
            let label = "";
            
            if((d.cost_center === "" || typeof d.cost_center == 'undefined')) { 
                
                if (cur_frm.doc.default_cost_center === "" || typeof cur_frm.doc.default_cost_center == 'undefined') {
                    frappe.validated = false;
                    frappe.msgprint("Set a Default Cost Center or specify the Cost Center for expense <strong>number " 
                                    + (i + 1) + "</strong>.");
                    return false;
                }
                else {
                    d.cost_center = cur_frm.doc.default_cost_center; 
                }
            }
            if(cur_frm.doc.default_project != "" || typeof cur_frm.doc.default_project != 'undefined') {                 
                d.project = cur_frm.doc.default_project; 
            }
        }); 
        
    },
    refresh(frm) {
        //update total and qty when an item is added
        if (frm.is_new()) return;

        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Ledger Preview'), () => {
                show_ledger_preview(frm);
            }, __('Preview'));
        }

        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('General Ledger'), () => {
                frappe.set_route('query-report', 'General Ledger', {
                    voucher_type: frm.doc.doctype,
                    voucher_no: frm.doc.name
                });
            }, __('View'));
        }

    },
    onload(frm) {
        //console.log("hello");

        frm.set_query("expense_account", 'expenses', () => {
            return {
                filters: [
                    ["Account", "company", "=", frm.doc.company],
                    ["Account", "root_type", "=", "Expense"],
                    ["Account", "parent_account", "Like", "%Indirect Expenses%"],
                                ["Account", "is_group", "=", "0"]                   
                ]
            }
        });
        frm.set_query("cost_center", 'expenses', () => {
            return {
                filters: [
                    ["Cost Center", "company", "=", frm.doc.company],
                    ["Cost Center", "is_group", "=", "0"]
                ]
            }
        });
        frm.set_query("default_cost_center", () => {
            return {
                filters: [
                    ["Cost Center", "company", "=", frm.doc.company],
                    ["Cost Center", "is_group", "=", "0"]
                ]
            }
        });
        frm.set_query("project", 'expenses', () => {
            return {
                filters: [
                    ["Project", "company", "=", frm.doc.company]
                ]
            }
        });
        frm.set_query("default_project", () => {
            return {
                filters: [
                    ["Project", "company", "=", frm.doc.company]
                ]
            }
        });
        
    },
    mode_of_payment: function(frm) {
        if (frm.doc.mode_of_payment) {
            frappe.call({
                method: 'expense_journal.expense_journal.doctype.expense_entry.expense_entry.get_account_details',
                args: {
                    'mode_of_payment': frm.doc.mode_of_payment,
                    'company': frm.doc.company,
                    'date': frm.doc.posting_date,
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('show_balance', r.message.show_balance);
                        frm.set_value('account', r.message.account);
                        frm.set_value('account_balance', r.message.account_balance);
                    }
                }
            });
        }
    }
});


function show_ledger_preview(frm) {
    frappe.call({
        method: 'get_gl_preview',
        doc: frm.doc,
        callback(r) {
            if (r.message) {
                const d = new frappe.ui.Dialog({
                    title: __('Accounting Ledger Preview'),
                    size: 'large',
                    fields: [{ fieldtype: 'HTML', fieldname: 'html' }]
                });

                d.fields_dict.html.$wrapper.html(render_gl_table(r.message));
                d.show();
            }
        }
    });
}

function render_gl_table(entries) {
    let rows = entries.map(e => `
        <tr>
            <td>${e.account}</td>
            <td class="text-right">${format_currency(e.debit)}</td>
            <td class="text-right">${format_currency(e.credit)}</td>
            <td>${e.remarks || ''}</td>
        </tr>
    `).join('');

    return `
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th>Account</th>
                    <th>Debit</th>
                    <th>Credit</th>
                    <th>Remarks</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}
