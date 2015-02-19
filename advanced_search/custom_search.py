# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _

class custom_search(osv.osv_memory):
    _name = "custom.search"
    _description = "Custom Search"
    
    _columns = {
        'object': fields.selection([('account.invoice.line','Supplier Invoice'),('purchase.order.line','Purchase Orders'),
                                    ('account.voucher.line','Purchase Receipt'),('account.invoice.out','Customer Invoice'),
                                    ('customer.refund','Customer Refund'),('supplier.refund','Supplier Refund')
                                    ], 'Model'),
        'field' : fields.many2one('ir.model.fields', 'Field'),
        'search_val': fields.char('Search Value For'),
        'is_val': fields.selection([('and','AND'),('or','OR')], 'Add a Condition'),
        'field_and' : fields.many2one('ir.model.fields', 'Field'),
        'search_val_and': fields.char('Search Value For'),         
    }
    
    _defaults = {
        'is_val': False,
    }
    
    def onchange_object(self, cr, uid, ids, obj, context):
        if context is None:
            context = {}
        f_list = []
        field_list = []
        sub_obj = ''
        if obj == 'account.invoice.line' or obj == 'supplier.refund': # Supplier Invoice
            sub_obj = 'account.invoice.line'
            f_list = ['product_id','name','account_id','quantity','price_unit', 'price_subtotal']
        elif obj == 'purchase.order.line': # Purchase Order
            sub_obj = 'purchase.order.line'            
            f_list = ['product_id','name','product_qty','price_unit']
        elif obj == 'account.voucher.line': # Purchase Receipt
            sub_obj = 'account.voucher.line'            
            f_list = ['name','account_id','amount']            
        elif obj == 'account.invoice.out' or obj == 'customer.refund': # Customer Refund and Customer Invoice
            sub_obj = 'account.invoice.line'
            f_list = ['product_id','name','account_id','quantity','price_unit']
        f_name_list = []   
        fields = self.pool.get('ir.model.fields').search(cr, uid, [('model_id','=',sub_obj)])
        for f_id in self.pool.get('ir.model.fields').browse(cr, uid, fields):
            if f_id.name in f_list:
                field_list.append(f_id.id)
                f_name_list.append(f_id.name)
        return {'domain':{'field':[('id','in',field_list)], 'field_and':[('id','in',field_list)]}}
    
    def onchange_search_val(self, cr, uid, ids, search_val, context):
        if search_val:
            return {'value': {'is_val': True}}
        else:
            return {'value': {'is_val': False}} 

    def custom_search(self, cr, uid, ids, context=None):
        """ Changes the Product Quantity by making a Physical Inventory.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        @return:
        """
        if context is None:
            context = {}
           
        search_obj = self.browse(cr, uid, ids)[0]
        if not search_obj.object or not search_obj.field or not search_obj.search_val:
            raise osv.except_osv(_('Warning!'), _('Please provide proper search values!.'))
        name = dict(self._columns['object'].selection).get(search_obj.object)
        val1 = str('%')+search_obj.search_val+str('%')
        
        # Supplier Invoice OR Supplier Refund
        if search_obj.object == 'account.invoice.line' or search_obj.object == 'supplier.refund':
            model = 'account.invoice'
            if search_obj.field.name in ['quantity','price_unit','price_subtotal']:
                val1 = search_obj.search_val
            b_id = []
            if search_obj.field.name == 'product_id':
                cr.execute('select id from product_template where name LIKE %s',(val1,))
                b_id = cr.fetchall()
            elif search_obj.field.name == 'account_id':
                cr.execute('select id from account_account where name LIKE %s',(val1,))
                b_id = cr.fetchall()  
            if search_obj.field.name in ['product_id','account_id']:
                inv_ids = [] 
                for bid in b_id:
                    field = (search_obj.field.name).encode('ascii','ignore')
                    cr.execute("select distinct(account_invoice.id) from account_invoice INNER JOIN account_invoice_line \
                    ON account_invoice.id=account_invoice_line.invoice_id where account_invoice_line."+field+"=%s", (bid[0],))
                    i_ids = cr.fetchall()
                    for i_id in i_ids:
                        inv_ids.append(i_id[0])
            else:
                field = (search_obj.field.name).encode('ascii','ignore')
                val1 = (val1).encode('ascii','ignore')
                if field == 'name':
                    cr.execute("select distinct(account_invoice.id) from account_invoice INNER JOIN account_invoice_line \
                        ON account_invoice.id=account_invoice_line.invoice_id where account_invoice_line."+field+" LIKE %s", (val1,))
                    inv_ids = cr.fetchall()
                else:
                    if search_obj.object == 'account.invoice.line':
                        cr.execute("select distinct(account_invoice.id) from account_invoice INNER JOIN account_invoice_line \
                        ON account_invoice.id=account_invoice_line.invoice_id where account_invoice.type='in_invoice' and account_invoice_line."+field+"=%s", (val1,))
                        inv_ids = cr.fetchall()
                    else:
                        cr.execute("select distinct(account_invoice.id) from account_invoice INNER JOIN account_invoice_line \
                        ON account_invoice.id=account_invoice_line.invoice_id where account_invoice.type='in_refund' and account_invoice_line."+field+"=%s", (val1,))
                        inv_ids = cr.fetchall()                    
            inv_list = []
            i_list = []
            for i_id in inv_ids:
                inv_list.append(i_id)
            if search_obj.is_val:
                val2 = search_obj.search_val_and and str('%')+search_obj.search_val_and+str('%') or ''
                if search_obj.field_and.name in ['quantity','price_unit','price_subtotal']:
                    val2 = search_obj.search_val_and
                b_ids = []
                if search_obj.field_and.name == 'product_id':
                    cr.execute('select id from product_template where name LIKE %s',(val2,))
                    b_ids = cr.fetchall()
                elif search_obj.field_and.name == 'account_id':
                    cr.execute('select id from account_account where name LIKE %s',(val2,))
                    b_ids = cr.fetchall()  
                if search_obj.field_and.name in ['product_id','account_id']:
                    inv_ids = [] 
                    for bid in b_ids:
                        field = (search_obj.field.name).encode('ascii','ignore')
                        cr.execute("select distinct(account_invoice.id) from account_invoice INNER JOIN account_invoice_line \
                        ON account_invoice.id=account_invoice_line.invoice_id where account_invoice_line."+field+"=%s", (bid[0],))
                        i_ids = cr.fetchall()
                        for i_id in i_ids:
                            inv_ids.append(i_id[0])
                else:
                    field_and = (search_obj.field_and.name).encode('ascii','ignore')
                    val1 = (val1).encode('ascii','ignore')
                    if field_and == 'name':
                        cr.execute("select distinct(account_invoice.id) from account_invoice INNER JOIN account_invoice_line \
                            ON account_invoice.id=account_invoice_line.invoice_id where account_invoice_line."+field_and+" LIKE %s", (val1,))
                        i_ids = cr.fetchall()
                    else:
                        if search_obj.object == 'account.invoice.line':
                            cr.execute("select distinct(account_invoice.id) from account_invoice INNER JOIN account_invoice_line \
                            ON account_invoice.id=account_invoice_line.invoice_id where account_invoice.type='in_invoice' and account_invoice_line."+field_and+"=%s", (val1,))
                            i_ids = cr.fetchall()
                        else:
                            cr.execute("select distinct(account_invoice.id) from account_invoice INNER JOIN account_invoice_line \
                            ON account_invoice.id=account_invoice_line.invoice_id where account_invoice.type='in_refund' and account_invoice_line."+field_and+"=%s", (val1,))
                            i_ids = cr.fetchall()
                for inv_id in i_ids:
                    i_list.append(inv_id[0])
            invoice_list = []
            if search_obj.is_val == 'and':
                invoice_list = list(set(inv_list) & set(i_list))
            elif search_obj.is_val == 'or':
                invoice_list = list(set(inv_list) | set(i_list))
            else:
                invoice_list = inv_list                

            domain = []
            ctx = {}     
            if search_obj.object == 'account.invoice.line':
                domain.append(('id','in',invoice_list))
                domain.append(('type','=','in_invoice'))
                ctx = {'default_type': 'in_invoice', 'type': 'in_invoice', 'journal_type': 'purchase'}
                view = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account', 'invoice_supplier_form')
                view1 = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account', 'invoice_tree')   
                
            elif search_obj.object == 'supplier.refund':
                domain.append(('id','in',invoice_list))
                domain.append(('type','=','in_refund'))
                ctx = {'default_type': 'in_refund', 'type': 'in_refund', 'journal_type': 'purchase_refund'}
                view = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account', 'invoice_form')
                view1 = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account', 'invoice_tree') 
            return {
                'type': 'ir.actions.act_window',
                'name': name,
                'view_mode': 'tree,form',
                'view_type': 'form',
                'views': [(view1 and view1[1] or False,'tree'),(view and view[1] or False,'form')],
                'res_model': model,
                'domain': domain,
                'context': ctx,
                }   
            
        # Purchase Order                  
        elif search_obj.object == 'purchase.order.line':
            model = 'purchase.order'
            if search_obj.field.name in ['product_qty','price_unit','price_subtotal']:
                val1 = search_obj.search_val
            b_id = []
            if search_obj.field.name == 'product_id':
                cr.execute('select id from product_template where name LIKE %s',(val1,))
                b_id = cr.fetchall()
            if search_obj.field.name in ['product_id']:
                if b_id and b_id[0] and b_id[0][0]:
                    field = (search_obj.field.name).encode('ascii','ignore')
                    cr.execute("select distinct(purchase_order.id) from purchase_order INNER JOIN purchase_order_line \
                        ON purchase_order.id=purchase_order_line.order_id where purchase_order_line."+field+"=%s", (b_id[0][0],))
                    inv_ids = cr.fetchall()
                else:
                    inv_ids = [] 
            else:
                field = (search_obj.field.name).encode('ascii','ignore')
                val1 = (val1).encode('ascii','ignore')
                if field == 'name':
                    cr.execute("select distinct(purchase_order.id) from purchase_order INNER JOIN purchase_order_line \
                        ON purchase_order.id=purchase_order_line.order_id where purchase_order_line."+field+" LIKE %s", (val1,))
                    inv_ids = cr.fetchall()
                else:
                    cr.execute("select distinct(purchase_order.id) from purchase_order INNER JOIN purchase_order_line \
                        ON purchase_order.id=purchase_order_line.order_id where purchase_order_line."+field+"=%s", (val1,))
                    inv_ids = cr.fetchall() 

            inv_list = []
            pur_list = []
            for i_id in inv_ids:
                inv_list.append(i_id[0])

            if search_obj.is_val:
                val2 = search_obj.search_val_and and str('%')+search_obj.search_val_and+str('%') or ''
                if search_obj.field_and.name in ['product_qty','price_unit','price_subtotal']:
                    val2 = search_obj.search_val
                p_ids = []
                if search_obj.field_and.name == 'product_id':
                    cr.execute('select id from product_template where name LIKE %s',(val2,))
                    p_ids = cr.fetchall()
                if search_obj.field_and.name in ['product_id']:
                    if p_ids and p_ids[0] and p_ids[0][0]:
                        p_field = (search_obj.field_and.name).encode('ascii','ignore')
                        cr.execute("select distinct(purchase_order.id) from purchase_order INNER JOIN purchase_order_line \
                            ON purchase_order.id=purchase_order_line.order_id where purchase_order_line."+p_field+"=%s", (p_ids[0][0],))
                        inv_ids = cr.fetchall()
                    else:
                        inv_ids = [] 
                else:
                    p_field = (search_obj.field_and.name).encode('ascii','ignore')
                    val2 = (val2).encode('ascii','ignore')
                    if p_field == 'name':
                        cr.execute("select distinct(purchase_order.id) from purchase_order INNER JOIN purchase_order_line \
                            ON purchase_order.id=purchase_order_line.order_id where purchase_order_line."+p_field+" LIKE %s", (val2,))
                        pur_ids = cr.fetchall()
                    else:
                        cr.execute("select distinct(purchase_order.id) from purchase_order INNER JOIN purchase_order_line \
                            ON purchase_order.id=purchase_order_line.order_id where purchase_order_line."+p_field+"=%s", (val2,))
                        pur_ids = cr.fetchall() 
                    for pur_id in pur_ids:
                        pur_list.append(pur_id[0])
            purchase_list = []
            if search_obj.is_val == 'and':
                purchase_list = list(set(inv_list) & set(pur_list))
            elif search_obj.is_val == 'or':
                purchase_list = list(set(inv_list) | set(pur_list))
            else:
                purchase_list = inv_list
            return {
                'type': 'ir.actions.act_window',
                'name': name,
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': model,
                'nodestroy': True,
                'domain': [('id','in',purchase_list)],
                }  
            
        # Purchase Receipt
        elif search_obj.object == 'account.voucher.line':
            b_id = False
            val1 = str('%')+str(search_obj.search_val)+str('%')
            model = 'account.voucher'
            if search_obj.field.name == 'account_id':
                cr.execute("select id from account_account where name LIKE '%"+search_obj.search_val+"%' or code like '%"+search_obj.search_val+"%'")
                b_id = cr.fetchall()
            elif search_obj.field.name in ['name']:
                cr.execute("select distinct(voucher_id) from account_voucher_line where "+search_obj.field.name+" LIKE %s",(val1,))
                b_id = cr.fetchall()
            elif search_obj.field.name in ['amount']:
                cr.execute("select distinct(voucher_id) from account_voucher_line where "+search_obj.field.name+" =%s",(search_obj.search_val,))
                b_id = cr.fetchall() 
            field = (search_obj.field.name).encode('ascii','ignore')
            inv_list = []
            if b_id:
                inv_ids = False
                if search_obj.field.name in['name','amount']:
                    cr.execute("select distinct(account_voucher.id) from account_voucher INNER JOIN account_voucher_line \
                                ON account_voucher.id=account_voucher_line.voucher_id where account_voucher.type='purchase' and account_voucher_line.voucher_id in %s", (tuple(b_id),))
                    inv_ids = cr.fetchall()
                else:
                    cr.execute("select distinct(account_voucher.id) from account_voucher INNER JOIN account_voucher_line \
                                ON account_voucher.id=account_voucher_line.voucher_id where account_voucher.type='purchase' and account_voucher_line."+search_obj.field.name+" in %s", (tuple(b_id),))
                    inv_ids = cr.fetchall()                
                for i_id in inv_ids:
                    inv_list.append(i_id[0])
                    
            recept_ids = []      
            if search_obj.is_val:
                val2 = str('%')+str(search_obj.search_val_and)+str('%')
                rec_ids = []
                if search_obj.field.name == 'account_id':
                    cr.execute("select id from account_account where name LIKE '%"+search_obj.search_val_and+"%' or code like '%"+search_obj.search_val_and+"%'")
                    rec_ids = cr.fetchall()
                elif search_obj.field.name in['name']:
                    cr.execute("select distinct(voucher_id) from account_voucher_line where "+search_obj.field.name+" LIKE %s",(val2,))
                    rec_ids = cr.fetchall()
                elif search_obj.field.name in ['amount']:
                    cr.execute("select distinct(voucher_id) from account_voucher_line where "+search_obj.field.name+" =%s",(search_obj.search_val_and,))
                    rec_ids = cr.fetchall() 
                field_and = (search_obj.field_and.name).encode('ascii','ignore')
                if rec_ids:
                    rec_list=False
                    if search_obj.field_and.name in['name', 'amount']:
                        cr.execute("select distinct(account_voucher.id) from account_voucher INNER JOIN account_voucher_line \
                                    ON account_voucher.id=account_voucher_line.voucher_id where account_voucher.type='purchase' and account_voucher_line.voucher_id in %s", (tuple(rec_ids),))
                        rec_list = cr.fetchall()
                    else:
                        cr.execute("select distinct(account_voucher.id) from account_voucher INNER JOIN account_voucher_line \
                                    ON account_voucher.id=account_voucher_line.voucher_id where account_voucher.type='purchase' and account_voucher_line."+search_obj.field_and.name+" in %s", (tuple(rec_ids),))
                        rec_list = cr.fetchall()                
                    for i_id in rec_list:
                        recept_ids.append(i_id[0])
            rcpt_list = []
            if search_obj.is_val == 'and':
                rcpt_list = list(set(inv_list) & set(recept_ids))
            elif search_obj.is_val == 'or':
                rcpt_list = list(set(inv_list) | set(recept_ids))
            else:
                rcpt_list = inv_list                    
            view = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_voucher', 'view_purchase_receipt_form')
            view1 = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_voucher', 'view_voucher_tree')
            return {
                'type': 'ir.actions.act_window',
                'name': name,
                'view_id' : view or False,
                'view_mode': 'tree,form',
                'view_type': 'form',
                'views': [(view1 and view1[1] or False,'tree'),(view and view[1] or False,'form')],
                'res_model': model,
                'nodestroy': True,
                'domain': [('id','in',rcpt_list),('type','=','purchase')],
                } 
            
        # Customer Invoice OR Customer Refund 
        elif search_obj.object == 'account.invoice.out' or search_obj.object == 'customer.refund':
            model = 'account.invoice'
            if search_obj.field.name in ['quantity','price_unit']:
                val1 = search_obj.search_val
            b_ids = []
            if search_obj.field.name == 'product_id':
                cr.execute('select id from product_template where name LIKE %s',(val1,))
                b_ids = cr.fetchall()
            elif search_obj.field.name == 'account_id':
                cr.execute('select id from account_account where name LIKE %s',(val1,))
                b_ids = cr.fetchall()  
            if search_obj.field.name in ['product_id','account_id']:
                inv_ids = [] 
                for b_id in b_ids:
                    field = (search_obj.field.name).encode('ascii','ignore')
                    if search_obj.object == 'account.invoice.out':
                        cr.execute("select distinct(account_invoice.id) from account_invoice INNER JOIN account_invoice_line \
                                ON account_invoice.id=account_invoice_line.invoice_id where account_invoice.type='out_invoice' and account_invoice_line."+field+"=%s", (b_id[0],))
                        i_ids = cr.fetchall()
                        for i_id in i_ids:
                            inv_ids.append(i_id[0])
                    else:
                        cr.execute("select distinct(account_invoice.id) from account_invoice INNER JOIN account_invoice_line \
                                ON account_invoice.id=account_invoice_line.invoice_id where account_invoice.type='out_refund' and account_invoice_line."+field+"=%s", (b_id[0],))
                        i_ids = cr.fetchall()
                        for i_id in i_ids:
                            inv_ids.append(i_id[0])                        
            else:
                field = (search_obj.field.name).encode('ascii','ignore')
                val1 = (val1).encode('ascii','ignore')
                if field == 'name':
                    if search_obj.object == 'account.invoice.out':
                        cr.execute("select distinct(account_invoice.id) from account_invoice INNER JOIN account_invoice_line \
                            ON account_invoice.id=account_invoice_line.invoice_id where account_invoice.type='out_invoice' and account_invoice_line."+field+" LIKE %s", (val1,))
                        inv_ids = cr.fetchall()
                    else:
                        cr.execute("select distinct(account_invoice.id) from account_invoice INNER JOIN account_invoice_line \
                            ON account_invoice.id=account_invoice_line.invoice_id where account_invoice.type='out_refund' and account_invoice_line."+field+" LIKE %s", (val1,))
                        inv_ids = cr.fetchall()
                else:
                    if search_obj.object == 'account.invoice.out':
                        cr.execute("select distinct(account_invoice.id) from account_invoice INNER JOIN account_invoice_line \
                            ON account_invoice.id=account_invoice_line.invoice_id where account_invoice.type='out_invoice' and account_invoice_line."+field+"=%s", (val1,))
                        inv_ids = cr.fetchall()  
                    else:
                        cr.execute("select distinct(account_invoice.id) from account_invoice INNER JOIN account_invoice_line \
                            ON account_invoice.id=account_invoice_line.invoice_id where account_invoice.type='out_refund' and account_invoice_line."+field+"=%s", (val1,))
                        inv_ids = cr.fetchall()                              
                    
            inv_list = []
            i_list = []
            for i_id in inv_ids:
                inv_list.append(i_id)
            if search_obj.is_val:
                val2 = search_obj.search_val_and and str('%')+search_obj.search_val_and+str('%') or ''
                if search_obj.field_and.name in ['quantity','price_unit']:
                    val2 = search_obj.search_val_and
                c_ids = []
                if search_obj.field_and.name == 'product_id':
                    cr.execute('select id from product_template where name LIKE %s',(val2,))
                    c_ids = cr.fetchall()
                elif search_obj.field_and.name == 'account_id':
                    cr.execute('select id from account_account where name LIKE %s',(val2,))
                    c_ids = cr.fetchall()  
                if search_obj.field_and.name in ['product_id','account_id']:
                    inv_ids = [] 
                    for c_id in c_ids:
                        field = (search_obj.field.name).encode('ascii','ignore')
                        if search_obj.object == 'account.invoice.out':
                            cr.execute("select distinct(account_invoice.id) from account_invoice INNER JOIN account_invoice_line \
                                    ON account_invoice.id=account_invoice_line.invoice_id where account_invoice.type='out_invoice' and account_invoice_line."+field+"=%s", (c_id[0],))
                            i_ids = cr.fetchall()
                        else:
                            cr.execute("select distinct(account_invoice.id) from account_invoice INNER JOIN account_invoice_line \
                                    ON account_invoice.id=account_invoice_line.invoice_id where account_invoice.type='out_refund' and account_invoice_line."+field+"=%s", (c_id[0],))
                            i_ids = cr.fetchall()
                        for i_id in i_ids:
                            i_list.append(i_id[0])                                                       
                else:
                    field_and = (search_obj.field_and.name).encode('ascii','ignore')
                    val2 = (val2).encode('ascii','ignore')
                    if field == 'name':
                        if search_obj.object == 'account.invoice.out':
                            cr.execute("select distinct(account_invoice.id) from account_invoice INNER JOIN account_invoice_line \
                                ON account_invoice.id=account_invoice_line.invoice_id where account_invoice.type='out_invoice' and account_invoice_line."+field+" LIKE %s", (val2,))
                            i_ids = cr.fetchall()
                        else:
                            cr.execute("select distinct(account_invoice.id) from account_invoice INNER JOIN account_invoice_line \
                                ON account_invoice.id=account_invoice_line.invoice_id where account_invoice.type='out_refund' and account_invoice_line."+field+" LIKE %s", (val2,))
                            i_ids = cr.fetchall()
                    else:
                        if search_obj.object == 'account.invoice.out':
                            cr.execute("select distinct(account_invoice.id) from account_invoice INNER JOIN account_invoice_line \
                                ON account_invoice.id=account_invoice_line.invoice_id where account_invoice.type='out_invoice' and account_invoice_line."+field+"=%s", (val2,))
                            i_ids = cr.fetchall()  
                        else:
                            cr.execute("select distinct(account_invoice.id) from account_invoice INNER JOIN account_invoice_line \
                                ON account_invoice.id=account_invoice_line.invoice_id where account_invoice.type='out_refund' and account_invoice_line."+field+"=%s", (val2,))
                            i_ids = cr.fetchall()   
                    for inv_id in i_ids:
                        i_list.append(inv_id[0])                            
            invoice_list = []
            if search_obj.is_val == 'and':
                invoice_list = list(set(inv_list) & set(i_list))
            elif search_obj.is_val == 'or':
                invoice_list = list(set(inv_list) | set(i_list))
            else:
                invoice_list = inv_list   
            domain = []
            ctx = {}
            if search_obj.object == 'account.invoice.out':
                domain.append(('id','in',invoice_list))
                domain.append(('type','=','out_invoice'))                
                ctx = {'default_type':'out_invoice', 'type':'out_invoice', 'journal_type': 'sale'}
                view = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account', 'invoice_form')
                view1 = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account', 'invoice_tree')     
            if search_obj.object == 'customer.refund':
                domain.append(('id','in',invoice_list))
                domain.append(('type','=','out_refund'))                 
                ctx = {'default_type':'out_refund', 'type':'out_refund', 'journal_type': 'sale_refund'}
                view = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account', 'invoice_form')
                view1 = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account', 'invoice_tree')     
                
            return {
                'type': 'ir.actions.act_window',
                'name': name,
                'view_mode': 'tree,form',
                'view_type': 'form',
                'views': [(view1 and view1[1] or False,'tree'),(view and view[1] or False,'form')],
                'res_model': model,
                'nodestroy': True,
                'domain': domain,
                'context': ctx,
                }    

custom_search()
   
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: