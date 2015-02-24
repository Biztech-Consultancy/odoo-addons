# -*- coding: utf-8 -*-
{
    'name': 'Custom Search',
    'version': '1.1',
    'author': 'Biztech Consultancy',
    'website': 'http://www.biztechconsultancy.com',
    'category': 'General',
    'description': """
Manage search.
====================================

This module allows us to search some of the fields of one2many relational fields for specific objects i.e. Customer Invoice, Customer Refund, 
Supplier Invoice, Supplier Refund, Purchase Orders, Purchase Receipts.
    """,
    'depends' : ['purchase', 'account','account_voucher'],
    'data': [
             'custom_search_view.xml',
              ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
