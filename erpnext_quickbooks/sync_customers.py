from __future__ import unicode_literals
import frappe
from frappe import _
import requests.exceptions
from .utils import make_quickbooks_log


def sync_customers(quickbooks_obj):
	"""Fetch Customer data from QuickBooks"""
	quickbooks_customer_list = []
	customer_query = """SELECT * FROM  Customer""" 
	qb_customer = quickbooks_obj.query(customer_query)
	get_qb_customer =  qb_customer['QueryResponse']['Customer']
	sync_qb_customers(get_qb_customer,quickbooks_customer_list)
	
def sync_qb_customers(get_qb_customer, quickbooks_customer_list):
	for qb_customer in get_qb_customer:
		if not frappe.db.get_value("Customer", {"quickbooks_cust_id": qb_customer.get('id')}, "name"):
			create_customer(qb_customer, quickbooks_customer_list)


def create_customer(qb_customer, quickbooks_customer_list):
	""" store Customer data in ERPNEXT """ 
	customer = None
	try:	
		customer = frappe.new_doc("Customer")
		customer.quickbooks_cust_id = str(qb_customer.get('Id')) if qb_customer.get('Id')  else str(qb_customer.get('value'))
		customer.customer_name = str(qb_customer.get('DisplayName')) if qb_customer.get('DisplayName')  else str(qb_customer.get('name'))
		customer.customer_type = _("Individual")
		customer.customer_group =_("Commercial")
		customer.default_currency =qb_customer['CurrencyRef'].get('value','') if qb_customer.get('CurrencyRef') else ''
		customer.territory = _("All Territories")
		customer.flags.ignore_mandatory = True
		customer.insert()

		if customer and qb_customer.get('BillAddr'):
			create_customer_address(customer, qb_customer.get("BillAddr"))
		frappe.db.commit()
		quickbooks_customer_list.append(customer.quickbooks_cust_id)

	except Exception, e:
		if e.args[0] and e.args[0].startswith("402"):
			raise e
		else:
			make_quickbooks_log(title=e.message, status="Error", method="create_customer", message=frappe.get_traceback(),
				request_data=qb_customer, exception=True)
	
	return quickbooks_customer_list


def create_customer_address(customer, address):
	address_title, address_type = get_address_title_and_type(customer.customer_name)
	try :
		frappe.get_doc({
			"doctype": "Address",
			"quickbooks_address_id": address.get("Id"),
			"address_title": address_title,
			"address_type": address_type,
			"address_line1": address.get("Line1"),
			"city": address.get("City"),
			"state": address.get("CountrySubDivisionCode"),
			"pincode": address.get("PostalCode"),
			"country": frappe.db.get_value("Country",{"code":address.get("CountrySubDivisionCode")},"name"),
			"email_id": address.get("PrimaryEmailAddr"),
			"customer": customer.name,
			"customer_name":  customer.customer_name
		}).insert()
			
	except Exception, e:
		make_quickbooks_log(title=e.message, status="Error", method="create_customer_address", message=frappe.get_traceback(),
				request_data=address, exception=True)
		raise e
	
def get_address_title_and_type(customer_name):
	address_type = _("Billing")
	address_title = customer_name
	if frappe.db.get_value("Address", "{0}-{1}".format(customer_name.strip(), address_type)):
		address_title = "{0}".format(customer_name.strip())
		
	return address_title, address_type 
