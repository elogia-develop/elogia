# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime

import logging
_logger = logging.getLogger(__name__)

MONTHS = ("Enero",
          "Febrero",
          "Marzo",
          "Abril",
          "Mayo",
          "Junio",
          "Julio",
          "Agosto",
          "Septiembre",
          "Octubre",
          "Noviembre",
          "Diciembre")


class SaleOrderWizard(models.Model):
    _name = 'sale.order.wizard'
    _description = 'Sale Order Wizard'
    _rec_name = 'date_order'

    date_order = fields.Date('Order date', required=True, index=True)
    check_fee = fields.Boolean('Management Fee')
    description = fields.Char('Description')
    reference = fields.Char('No. reference')
    check_change = fields.Boolean('Change?')
    check_error = fields.Boolean('Error')
    list_error = fields.Char('List errors')

    @api.onchange('check_change')
    def onchange_change_wizard(self):
        env_control = self.env['control.campaign.marketing']
        if self.check_change:
            obj_control = env_control.search([('id', 'in', self._context.get('active_ids'))])
            control_filter = obj_control.filtered(lambda e: e.state == 'sale' or e.type_invoice != 'sale') \
                if obj_control else False
            if control_filter:
                self.check_error = True
            self.list_error = '{}' .format(control_filter.mapped('campaign_id.name'))

    def action_create_order(self):
        _logger.info('Begin: action_quotation_sale')
        env_product_setting = self.env['product.fee.setting'].search([])
        env_pricelist_setting = self.env['pricelist.setting'].search([])
        env_control = self.env['control.campaign.marketing']
        if not env_product_setting:
            raise UserError(_('There are no "Product Settings" configured.\n Check in Settings/Product Settings menu.'))
        if not env_pricelist_setting:
            raise UserError(_('There are no "Pricelist Settings" configured.\n '
                              'Check in Settings/Pricelist Settings menu.'))
        else:
            obj_control_ids = env_control.search([('id', 'in', self._context.get('active_ids'))])
            if obj_control_ids:
                list_not_setting = [product.name for product in obj_control_ids.mapped('campaign_line_id.product_id')
                                    if product not in env_product_setting.mapped('product_id')]
                if list_not_setting:
                    raise UserError(_('Products {} are not configured.\n Check in Settings/Product Settings menu.'
                                      .format(list_not_setting)))
                price_not_setting = (obj_control_ids.mapped('currency_id') -
                                     env_pricelist_setting.mapped('currency_id')).mapped('name')
                if price_not_setting:
                    raise UserError(_('Currency {} are not configured.\n Check in Settings/Pricelist Settings menu.'
                                      .format(price_not_setting)))
                else:
                    if self.check_error:
                        raise UserError(_('There are campaign controls that cannot be processed.'))
                    else:
                        for obj_control in obj_control_ids:
                            self.action_quotation_sale(obj_control, env_product_setting, env_pricelist_setting)

    def action_quotation_sale(self, control, setting, pricelist_ids):
        order_lines = []
        order_obj = self.env['sale.order']
        list_line = [control.campaign_line_id.product_id]
        other_product = setting.filtered(lambda e: e.product_id == control.campaign_line_id.product_id)
        if other_product and self.check_fee:
            list_line.append(other_product.other_product_id)
        for line in list_line:
            line_vals = {}
            taxes = line.taxes_id if line.taxes_id else False
            if self.check_fee:
                price_unit = control.billed_revenue - control.fee_revenue
            else:
                price_unit = control.billed_revenue
            line_vals = {
                'price_unit': price_unit,
                'product_id': line.id,
                'product_uom': line.uom_id.id,
                'product_uom_qty': 1,
                'name': line.name,
                'tax_id': [(6, 0, taxes.ids)] if taxes else False,
                'currency_id': control.currency_id.id,
                'control_id': control.id,
                'campaign_elogia_id': control.campaign_id.id
            }
            order_lines.append((0, 0, line_vals))
        pricelist = pricelist_ids.filtered(lambda e: e.currency_id == control.currency_id)
        order_vals = {
            'partner_id': control.client_id.id,
            'date_order': self.date_order,
            'order_line': order_lines,
            'pricelist_id': pricelist and pricelist.pricelist_id.id or False,
            'fiscal_position_id': control.client_id.property_account_position_id.id
            if control.client_id.property_account_position_id else False,
            'currency_id': control.currency_id.id,
            'user_id': self.env.user.id,
            'analytic_account_id': control.campaign_id.analytic_account_id.id,
            'client_order_ref': self.description,
            'origin': self.reference,
        }
        sale_order = order_obj.create(order_vals)
        if sale_order:
            _logger.info('Order Created')
            _logger.info(sale_order.name)
            control.state = 'sale'
            control.message_post(body=_("Created sale order: {}").format(sale_order.name))


class HistoricalDateObjectives(models.Model):
    _name = 'historical.date.objectives'
    _description = 'Historical Date Objectives'
    _rec_name = 'date_start'

    date_start = fields.Date(string='Start Date', required=True)
    date = fields.Date(string='Finish Date')
    campaign_id = fields.Many2one('campaign.marketing.elogia', 'Campaign marketing')


class ExpenseEntrySetting(models.Model):
    _name = 'expense.entry.setting'
    _description = 'Expense Entry Setting'
    _rec_name = 'expense_account'

    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)
    journal_id = fields.Many2one('account.journal', 'Journal', required=True)
    expense_account = fields.Many2one('account.account', 'Expense Account', required=True)
    passive_account = fields.Many2one('account.account', 'Passive Account', required=True)


class PriceListSetting(models.Model):
    _name = 'pricelist.setting'
    _description = 'Pricelist Setting'
    _rec_name = 'currency_id'

    currency_id = fields.Many2one('res.currency', 'Currency', required=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', check_company=True,
                                   domain="[('currency_id', '=', currency_id)]")

    _sql_constraints = [
        ('currency_unique', 'unique (currency_id)', 'This currency already has a related Pricelist!')
    ]


class ProductFeeSetting(models.Model):
    _name = 'product.fee.setting'
    _description = 'Product Fee Setting'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', 'Product', required=True, index=True)
    other_product_id = fields.Many2one('product.product', 'Product fee', required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)

    _sql_constraints = [
        ('company_product_unique', 'unique (company_id,product_id)',
         'This product and company already has a related Product Fee Setting!')
    ]


class CampaignAccountingSetting(models.Model):
    _name = 'campaign.accounting.setting'
    _description = 'Accounting Setting'
    _rec_name = 'company_id'

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    journal_id = fields.Many2one('account.journal', 'Journal')
    account_debit_first = fields.Many2one('account.account', 'Debit (Invoice)', required=True)
    account_credit_first = fields.Many2one('account.account', 'Credit (Invoice)', required=True)
    account_debit_second = fields.Many2one('account.account', 'Debit (Control)')
    account_credit_second = fields.Many2one('account.account', 'Credit (Control)')

    _sql_constraints = [
        ('company_unique', 'unique (company_id)', 'This company already has a related Accounting Setting!')
    ]

    @api.constrains('account_debit_first', 'account_credit_first')
    def check_control_account(self):
        for record in self:
            if record.account_debit_first and record.account_credit_first:
                record.account_debit_second = record.account_credit_first.id
                record.account_credit_second = record.account_debit_first.id


class CampaignLineInvoice(models.Model):
    _name = 'campaign.line.invoice'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Line Invoice'
    _rec_name = 'invoice_date'

    campaign_id = fields.Many2one('campaign.marketing.elogia', 'Campaign', required=True, ondelete='restrict', tracking=1)
    invoice_date = fields.Date(string='Invoice Date', required=True)
    invoice_date_due = fields.Date(string='Due Date')
    order_id = fields.Many2one('sale.order', 'Sale')
    description = fields.Char('Description')
    amount = fields.Float('Amount', tracking=1)
    currency_id = fields.Many2one(related='campaign_id.currency_id', string="Currency")
    company_id = fields.Many2one(related='campaign_id.company_id', string="Company")
    invoice_id = fields.Many2one('account.move', string="Invoice", ondelete='restrict')
    invoice_line_id = fields.Many2one('account.move.line', string="Invoice line", ondelete='restrict')
    move_id = fields.Many2one('account.move', string="Move")
    state = fields.Selection([
        ('no_process', 'Not processed'),
        ('process', 'Processed')
    ], string='Status', compute='check_state_invoice', tracking=1)

    @api.depends('move_id')
    def check_state_invoice(self):
        for record in self:
            record.state = 'no_process'
            if record.move_id:
                record.state = 'process'

    def unlink(self):
        for record in self:
            if record.state == 'process':
                raise UserError(_('You cannot delete an line invoice in the processed state.'))
        res = super(CampaignLineInvoice, self).unlink()
        return res


class ControlLineSupplier(models.Model):
    _name = 'control.line.supplier'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Control Line'
    _rec_name = 'partner_id'

    def _get_default_currency_id(self):
        return self.env.company.currency_id.id

    control_id = fields.Many2one('control.campaign.marketing', 'Control', tracking=1)
    company_id = fields.Many2one(related='control_id.company_id', string='Company', tracking=1)
    name_campaign = fields.Char(related='control_id.campaign_id.name', store=True, string='Campaigns', tracking=1)
    client_id = fields.Many2one(related='control_id.client_id', store=True, string='Client', tracking=1)
    analytic_account_id = fields.Many2one(related='control_id.analytic_account_id', store=True,
                                          string='Analytic account', tracking=1)
    partner_id = fields.Many2one('res.partner', 'Supplier', required=True, index=True, tracking=1)
    invoice_provision = fields.Float('Provision', tracking=1)
    invoice_provision_ml = fields.Float('Provision (mt)', tracking=1, compute='calc_amount_total')
    currency_id = fields.Many2one('res.currency', default=_get_default_currency_id, string="Currency")
    currency_control_id = fields.Many2one(related='control_id.currency_id', store=True, string="Currency control")
    type_payment = fields.Selection(selection=[
        ('spain', 'Spain'),
        ('client', 'Client'),
        ('mexico', 'Mexico'),
    ], string='Payment type', tracking=1)
    state = fields.Selection([
        ('no_process', 'Not processed'),
        ('process', 'Processed')
    ], string='Status', default='no_process', tracking=1)

    @api.onchange('partner_id')
    def onchange_currency_by_partner(self):
        if self.partner_id and self.partner_id.property_product_pricelist:
            self.currency_id = self.partner_id.property_product_pricelist.currency_id.id

    @api.depends('invoice_provision')
    def calc_amount_total(self):
        for record in self:
            val_tmp = 0
            if record.currency_id == record.control_id.currency_id:
                val_tmp = record.invoice_provision
            if record.currency_id != record.control_id.currency_id:
                if record.control_id.currency_id == record.control_id.company_id.currency_id:
                    if record.currency_id.rate > 0:
                        val_tmp = record.invoice_provision / record.currency_id.rate
                else:
                    if record.currency_id.rate > 0:
                        val_tmp = (record.invoice_provision / record.currency_id.rate) * record.control_id.currency_id.rate
                    if record.currency_id == record.control_id.company_id.currency_id:
                        val_tmp = record.invoice_provision * record.control_id.currency_id.rate
            record.invoice_provision_ml = val_tmp

    def create_purchase_order(self):
        list_supplier = self.filtered(
            lambda a: a.state == 'no_process' and a.type_payment != 'client' and a.control_id.state in ['pending', 'sale'])
        if list_supplier:
            line_by_supplier = self._group_line_by_supplier(list_supplier)
            if line_by_supplier:
                for supplier_key, supplier_value in line_by_supplier.items():
                    line_by_currency = self._group_line_by_currency(supplier_value)
                    if line_by_currency:
                        for currency_key, currency_value in line_by_currency.items():
                            self.create_purchase(currency_value, supplier_key)
                            for item in currency_value:
                                item.state = 'process'
        for control in list_supplier.mapped('control_id'):
            if control.state == 'sale':
                control.state = 'both'
            else:
                control.state = 'purchase'

    def _group_line_by_supplier(self, list_supplier):
        """"
        Function to group the line by supplier
        """
        line_by_suppl = {}
        for record in list_supplier:
            supplier = record.partner_id
            if supplier not in line_by_suppl:
                line_by_suppl[supplier] = [record]
            else:
                line_by_suppl[supplier].append(record)
        return line_by_suppl

    def _group_line_by_currency(self, supplier_value):
        """"
        Function to group the line by currency
        """
        line_by_currency = {}
        for record in supplier_value:
            currency = record.currency_id
            if currency not in line_by_currency:
                line_by_currency[currency] = [record]
            else:
                line_by_currency[currency].append(record)
        return line_by_currency

    def create_purchase(self, line, supplier):
        purchase_obj = self.env['purchase.order']
        vals_purchase = self._prepare_vals_purchase_order(line, supplier)
        purchase = purchase_obj.create(vals_purchase)
        self._create_lines_purchase_order(purchase, line)

    def _prepare_vals_purchase_order(self, line, supplier):
        vals = {
            'partner_id': supplier.id,
            'origin': 'Control Campaign',
            'currency_id': line[0].currency_id.id,
            'date_planned': fields.datetime.now(),
            'control_id': line[0].control_id.id,
            'campaign_elogia_id': line[0].control_id.campaign_id.id
        }
        return vals

    def _create_lines_purchase_order(self, purchase, line):
        purchase_line_obj = self.env['purchase.order.line']
        vals = {
            'order_id': purchase.id,
            'product_id': line[0].control_id.campaign_line_id.product_id.id,
            'name': line[0].control_id.campaign_line_id.product_id.name,
            'product_uom': line[0].control_id.campaign_line_id.product_id.uom_po_id.id,
            'date_planned': fields.datetime.now(),
            'product_qty': 1,
            'price_unit': sum([item.invoice_provision for item in line]),
            'taxes_id': [(6, 0, line[0].control_id.campaign_line_id.product_id.supplier_taxes_id.ids)]
        }
        purchase_line_obj.create(vals)
        return True


class PeriodCampaign(models.Model):
    _name = 'period.campaign'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Period campaign'
    _order = "name_year desc, name_month desc"

    name = fields.Char('Name', required=True, default='/', index=True)
    name_month = fields.Integer('Month', required=True)
    name_year = fields.Integer('Year', required=True)
    state = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], string='Status control', default='closed')
    state_objective = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], string='Status objective', default='closed')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    @api.constrains('name_month', 'name_year')
    def check_name_period(self):
        for record in self:
            record.name = MONTHS[record.name_month - 1] + '-' + str(record.name_year)

    def action_read_period(self):
        self.ensure_one()
        return {
            'name': self.display_name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'period.campaign',
            'res_id': self.id,
        }


class ControlCampaign(models.Model):
    _name = 'control.campaign.marketing'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = "Control Campaign"
    _order = 'id desc'

    def _get_default_period(self):
        env_period = self.env['period.campaign']
        return env_period.search([('state', '=', 'open'), ('company_id', '=', self.env.company.id)], limit=1)

    name = fields.Char(string='Description', required=True, index=True)
    campaign_line_id = fields.Many2one('campaign.marketing.line', 'Product line', required=True, ondelete='restrict',
                                       index=True)
    campaign_id = fields.Many2one('campaign.marketing.elogia', 'Campaign', required=True, ondelete='restrict',
                                  tracking=1)
    company_id = fields.Many2one('res.company', 'Company', tracking=1)
    project_id = fields.Many2one('project.project', 'Project', tracking=1)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending processing'),
        ('sale', 'Processed sale'),
        ('purchase', 'Processed purchase'),
        ('both', 'Processed'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=1)
    period = fields.Many2one('period.campaign', 'Period', tracking=1, ondelete='restrict', default=_get_default_period,
                             domain=lambda self: [('state', '=', 'open'), ('company_id', '=', self.env.company.id)])
    currency_id = fields.Many2one(related='campaign_id.currency_id', store=True, string="Currency")
    currency_company_id = fields.Many2one(related='company_id.currency_id', store=True, string='Company currency')
    clicks = fields.Float('Click/Lead/Sale', required=True, default=1)
    amount_unit = fields.Float('Amount total', tracking=1)
    amount_currency = fields.Float('Amount(ml)', tracking=1, compute='calc_price_ml', store=True)
    consume = fields.Float('Campaign revenue', tracking=1, compute='calc_price_ml', store=True)
    consume_currency = fields.Float('Campaign revenue(ml)', tracking=1, compute='calc_price_ml', store=True)
    client_id = fields.Many2one('res.partner', 'Client', tracking=1)
    percentage_fee = fields.Float('% Fee', tracking=1)
    check_change = fields.Boolean('Change?')
    count_invoice_sale = fields.Integer('Count Invoice sale', compute='get_count_models')
    count_invoice_purchase = fields.Integer('Count Invoice vendor', compute='get_count_models')
    count_sale = fields.Integer('Count Sales', compute='get_count_models')
    count_purchase = fields.Integer('Count Purchase', compute='get_count_models')
    count_move = fields.Integer('Count Move', compute='get_count_models')
    control_line_ids = fields.One2many('control.line.supplier', 'control_id', 'Control lines')
    type_invoice = fields.Selection(related='campaign_id.type_invoice', store=True, string='Billing type', tracking=1)
    order_ids = fields.One2many('sale.order.line', 'control_id', 'Sales')
    invoice_ids = fields.One2many('account.move', 'control_id', 'Invoices')
    purchase_ids = fields.One2many('purchase.order.line', 'control_id', 'Purchase')
    fee_revenue = fields.Float('Fee revenue', tracking=1, compute='calc_price_ml', store=True)
    fee_revenue_ml = fields.Float('Fee revenue(ml)', tracking=1, compute='calc_kpi', store=True)
    billed_revenue = fields.Float('Billed revenue', tracking=1, compute='calc_kpi', store=True)
    billed_revenue_ml = fields.Float('Billed revenue(ml)', tracking=1, compute='calc_kpi', store=True)
    purchase_ml = fields.Float('Purchases(ml)', tracking=1, compute='calc_kpi', store=True)
    margin_ml = fields.Float('Margin(ml)', tracking=1, compute='calc_kpi', store=True)
    objective_month = fields.Float('Month objective', tracking=1, compute='calc_kpi', store=True)
    percent_objective = fields.Float('% Over objectives', tracking=1, compute='calc_kpi', store=True)
    margin_factor_ml = fields.Float('Margin factor(ml)', tracking=1, compute='calc_kpi', store=True)
    check_diff = fields.Boolean('Diff', compute='get_name_campaign')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic account', tracking=1)

    def set_pending(self):
        for record in self:
            record.state = 'pending'

    def set_process(self):
        for record in self:
            record.state = 'both'

    def set_draft(self):
        for record in self:
            record.state = 'draft'

    def set_cancel(self):
        for record in self:
            record.state = 'cancel'

    def generate_sale(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create sale order',
            'res_model': 'sale.order.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {'origin_view': 'wizard_into'}
        }

    def generate_move(self):
        env_mov = self.env['account.move']
        env_setting = self.env['campaign.accounting.setting']
        for record in self:
            obj_setting = env_setting.search([('company_id', '=', record.company_id.id)], limit=1)
            if obj_setting:
                self.generated_account_move(record, env_mov, obj_setting)
            if record.state == 'purchase':
                record.state = 'both'
            else:
                if record.count_purchase >= 1:
                    record.state = 'both'

    def generated_account_move(self, record, env_mov, obj_setting):
        list_setting = [{'key': 'debit', 'value_d': obj_setting.account_debit_second},
                        {'key': 'credit', 'value_c': obj_setting.account_credit_second}]
        vals = {
            'ref': record.campaign_id.name,
            'campaign_elogia_id': record.campaign_id.id,
            'control_id': record.id,
            'move_type': 'entry',
            'line_ids': []
        }
        billed_currency = record.billed_revenue_ml
        if record.currency_id != record.company_id.currency_id:
            if record.currency_id.rate > 0:
                billed_currency = record.billed_revenue_ml / record.currency_id.rate
        for item in list_setting:
            vals['line_ids'].append(((0, 0, {
                'account_id': item['value_d'].id if item['key'] == 'debit' else item['value_c'].id,
                'name': record.name,
                'partner_id': record.client_id.id,
                'debit': billed_currency if item['key'] == 'debit' else 0,
                'credit': billed_currency if item['key'] == 'credit' else 0,
            })))
        obj_move = env_mov.with_context(check_move_validity=False).create(vals)
        if obj_move:
            record.message_post(body=_("Created move: {}") .format(obj_move.ref))

    def generate_purchase(self):
        for record in self:
            if record.control_line_ids:
                record.control_line_ids.create_purchase_order()

    @api.onchange('campaign_id')
    def onchange_campaign_id(self):
        if self.campaign_id:
            self.project_id = self.campaign_id.project_id.id
            self.company_id = self.campaign_id.company_id.id
            self.client_id = self.campaign_id.client_id.id
            self.percentage_fee = self.campaign_id.percentage_fee
            self.campaign_line_id = False

    def get_count_models(self):
        env_line = self.env['account.move.line']
        for record in self:
            obj_line = env_line.search([('control_id', '=', record.id)])
            record.count_invoice_sale = len(obj_line.filtered(
                lambda e: e.move_id.move_type in ['out_invoice', 'out_refund']).mapped('move_id')) if obj_line else 0
            record.count_invoice_purchase = len(obj_line.filtered(
                lambda e: e.move_id.move_type in ['in_invoice', 'in_refund']).mapped('move_id')) if obj_line else 0
            record.count_sale = len(record.order_ids.mapped('order_id')) if record.order_ids else 0
            record.count_purchase = len(record.purchase_ids.mapped('order_id')) if record.purchase_ids else 0
            record.count_move = len(record.invoice_ids.filtered(lambda l: l.move_type == 'entry')) \
                if record.invoice_ids else 0

    def action_view_sales(self):
        dic_return = {
            'name': 'Sale Orders',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'domain': [('id', 'in', self.order_ids.mapped('order_id').ids)],
            'context': {
                'default_partner_id': self.client_id.id
            }
        }
        if self.order_ids:
            dic_return['view_mode'] = 'tree,form'
        else:
            dic_return['view_mode'] = 'form'
        return dic_return

    def action_view_purchases(self):
        dic_return = {
            'name': 'Purchase Orders',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'domain': [('id', 'in', self.purchase_ids.mapped('order_id').ids)],
        }
        if self.purchase_ids:
            dic_return['view_mode'] = 'tree,form'
        else:
            dic_return['view_mode'] = 'form'
        return dic_return

    def action_view_invoice_sale(self):
        obj_line = self.env['account.move.line'].search([('control_id', '=', self.id)])
        dic_return = {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'domain': [('id', 'in', obj_line.filtered(
                lambda e: e.move_id.move_type in ['out_invoice', 'out_refund']).mapped('move_id.id'))],
            'context': {
                'default_partner_id': self.client_id.id,
                'default_move_type': 'out_invoice'
            }
        }
        if obj_line.filtered(lambda e: e.move_id.move_type in ['out_invoice', 'out_refund']):
            dic_return['view_mode'] = 'tree,form'
        else:
            dic_return['view_mode'] = 'form'
        return dic_return

    def action_view_invoice_purchase(self):
        obj_line = self.env['account.move.line'].search([('control_id', '=', self.id)])
        dic_return = {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'domain': [('id', 'in', obj_line.filtered(
            lambda e: e.move_id.move_type in ['in_invoice', 'in_refund']).mapped('move_id.id'))],
            'context': {
                'default_move_type': 'in_invoice'
            }
        }
        if obj_line.filtered(lambda e: e.move_id.move_type in ['in_invoice', 'in_refund']):
            dic_return['view_mode'] = 'tree,form'
        else:
            dic_return['view_mode'] = 'form'
        return dic_return

    def action_view_moves(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
        action['domain'] = [('control_id', '=', self.id), ('move_type', '=', 'entry')]
        action['context'] = {'default_move_type': 'entry', 'view_no_maturity': True,
                             'default_control_id': self.id,
                             'default_campaign_elogia_id': self.campaign_id.id
                             }
        return action

    @api.depends('amount_unit', 'clicks', 'amount_currency', 'consume', 'percentage_fee')
    def calc_price_ml(self):
        for record in self:
            record.consume = record.amount_unit * record.clicks
            record.amount_currency = record.amount_unit
            if record.currency_id != record.company_id.currency_id:
                if record.currency_id.rate > 0:
                    record.amount_currency = record.amount_unit / record.currency_id.rate
            record.consume_currency = record.amount_currency * record.clicks
            record.fee_revenue = record.consume * record.percentage_fee / 100

    @api.depends('fee_revenue', 'fee_revenue_ml', 'consume', 'control_line_ids', 'billed_revenue',
                 'billed_revenue_ml', 'margin_ml', 'objective_month')
    def calc_kpi(self):
        env_objective = self.env['objective.campaign.marketing']
        for record in self:
            obj_objective_id = env_objective.search([
                ('campaign_id', '=', record.campaign_id.id),
                ('period', '=', record.period.id),
                ('product_id', '=', record.campaign_line_id.product_id.id)], limit=1)
            sum_client = sum(record.control_line_ids.filtered(
                lambda e: e.type_payment == 'client').mapped('invoice_provision_ml'))
            sum_not_client = (sum(record.control_line_ids.filtered(
                lambda e: e.type_payment != 'client').mapped('invoice_provision_ml')))
            record.fee_revenue_ml = record.fee_revenue
            record.billed_revenue = record.consume + record.fee_revenue - sum_client
            record.billed_revenue_ml = record.billed_revenue
            record.margin_ml = record.billed_revenue - sum_not_client
            if record.currency_id != record.company_id.currency_id:
                if record.currency_id.rate > 0:
                    record.fee_revenue_ml = record.fee_revenue / record.currency_id.rate
                    record.billed_revenue_ml = record.billed_revenue / record.currency_id.rate
                    record.margin_ml = (record.billed_revenue - sum_not_client) / record.currency_id.rate
            record.purchase_ml = - (sum_not_client / record.currency_id.rate) if record.currency_id else 0
            record.margin_factor_ml = record.margin_ml - record.fee_revenue_ml
            record.objective_month = obj_objective_id.amount_period if obj_objective_id else 0
            record.percent_objective = (record.consume * 100)/record.objective_month \
                if record.objective_month > 0 else 0

    def get_name_campaign(self):
        for record in self:
            record.check_diff = False
            if record.campaign_id and record.campaign_id.currency_id != record.currency_id:
                record.check_diff = True


class ObjectiveCampaignMarketing(models.Model):
    _name = 'objective.campaign.marketing'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = "Objective Campaign Marketing"
    _order = 'id desc'

    campaign_line_id = fields.Many2one('campaign.marketing.line', 'Campaign Line', required=True, ondelete='restrict',
                                       index=True, copy=False)
    name = fields.Char(string='Description', required=True, index=True)
    project_id = fields.Many2one('project.project', 'Project', tracking=1)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic account', tracking=1)
    campaign_id = fields.Many2one('campaign.marketing.elogia', 'Campaign')
    currency_id = fields.Many2one(related='campaign_id.currency_id', depends=['campaign_id.currency_id'], store=True,
                                  string='Currency')
    company_id = fields.Many2one(related='campaign_id.company_id', string='Company', store=True, index=True)
    client_id = fields.Many2one('res.partner', 'Client', tracking=1)
    partner_id = fields.Many2one('res.partner', 'Supplier', tracking=1)
    product_id = fields.Many2one('product.product', string='Product', domain="[('sale_ok', '=', True)]", tracking=1)
    period = fields.Many2one('period.campaign', 'Period', tracking=1, ondelete='restrict')
    amount_period = fields.Float('Amount', tracking=1)
    percentage_fee = fields.Float('Fee revenue', tracking=1)
    percentage_margin = fields.Float('% Margin', tracking=1)
    margin = fields.Float('Margin', tracking=1, compute="calc_amount_margin")
    margin_total = fields.Float('Margin total', tracking=1, compute="calc_amount_margin")
    type_payment = fields.Selection(selection=[
        ('spain', 'Spain'),
        ('client', 'Client'),
        ('mexico', 'Mexico'),
    ], string='Payment type', tracking=1)
    month_actual = fields.Integer('Month')
    check_deleted = fields.Boolean('To delete')

    def action_read_objective(self):
        self.ensure_one()
        return {
            'name': self.display_name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'objective.campaign.marketing',
            'res_id': self.id,
        }

    @api.depends('amount_period', 'percentage_margin', 'percentage_fee', 'margin')
    def calc_amount_margin(self):
        for record in self:
            record.margin = record.amount_period * record.percentage_margin / 100
            record.margin_total = record.margin + record.percentage_fee


class CampaignMarketingLine(models.Model):
    _name = 'campaign.marketing.line'
    _description = "Campaign Marketing Line"
    _rec_name = 'product_id'

    campaign_id = fields.Many2one('campaign.marketing.elogia', 'Campaign', required=True, ondelete='restrict',
                                  index=True, copy=False)
    name = fields.Char(string='Description', required=True, index=True)
    percentage_fee = fields.Float(string='% Fee', digits='Discount', default=0.0)
    amount_total = fields.Float('Amount')
    product_id = fields.Many2one('product.product', string='Product',
                                 domain="[('sale_ok', '=', True), '|', ('company_id', '=', False), "
                                        "('company_id', '=', company_id)]", change_default=True, ondelete='restrict',
                                 check_company=True, required=True)
    product_template_id = fields.Many2one('product.template', string='Product Template',
                                          related="product_id.product_tmpl_id", domain=[('sale_ok', '=', True)])
    currency_id = fields.Many2one(related='campaign_id.currency_id', depends=['campaign_id.currency_id'], store=True,
                                  string='Currency')
    company_id = fields.Many2one(related='campaign_id.company_id', string='Company', store=True, index=True)
    client_id = fields.Many2one(related='campaign_id.client_id', string='Client', store=True)
    campaign_client_id = fields.Many2one(related='campaign_id.client_id', store=True, string='Customer')
    state = fields.Selection(related='campaign_id.state', string='Status', copy=False, store=True)

    @api.onchange('product_id')
    def onchange_product_name(self):
        if self.product_id:
            self.name = self.product_id.name
            self.amount_total = self.product_id.list_price
            self.percentage_fee = self.campaign_id.percentage_fee if self.campaign_id.percentage_fee else 0


class CampaignMarketingElogia(models.Model):
    _name = 'campaign.marketing.elogia'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = "Campaign Marketing"
    _order = 'id desc'
    _check_company_auto = True

    def _get_default_currency_id(self):
        return self.env.company.currency_id.id

    def _calc_revenue_control(self):
        env_control = self.env['control.campaign.marketing']
        list_consume = []
        list_fee = []
        for record in self:
            obj_control = env_control.search([('campaign_id', '=', record.id)])
            for item in obj_control:
                if item.currency_id == record.currency_id:
                    val_consume_currency = item.consume
                    val_fee_currency = item.fee_revenue
                else:
                    if record.currency_id == record.company_id.currency_id:
                        if item.currency_id.rate > 0:
                            val_consume_currency = item.consume / item.currency_id.rate
                            val_fee_currency = item.fee_revenue / item.currency_id.rate
                    else:
                        if item.currency_id.rate > 0:
                            val_consume_currency = item.consume / item.currency_id.rate * record.currency_id.rate
                            val_fee_currency = item.fee_revenue / item.currency_id.rate * record.currency_id.rate
                        if item.currency_id == record.company_id.currency_id:
                            val_consume_currency = item.consume * record.currency_id.rate
                            val_fee_currency = item.fee_revenue * record.currency_id.rate
                list_consume.append(val_consume_currency)
                list_fee.append(val_fee_currency)
            record.amount_diff = sum(list_consume) if list_consume else 0
            record.amount_fee = sum(list_fee) if list_fee else 0

    name = fields.Char('Name', index=True, required=True)
    project_id = fields.Many2one('project.project', 'Project', tracking=1)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', default=_get_default_currency_id, string="Currency")
    client_id = fields.Many2one('res.partner', 'Client', tracking=1)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic account', tracking=1)
    date_start = fields.Date(string='Start Date', tracking=1)
    date = fields.Date(string='Finish Date', tracking=1)
    type_invoice = fields.Selection(selection=[
        ('sale', 'Sales'),
        ('account', 'Accounting')
    ], string='Billing type', tracking=1)
    percentage_fee = fields.Float('% Fee', default=0.0)
    type_payment = fields.Selection(selection=[
        ('spain', 'Spain'),
        ('client', 'Client'),
        ('mexico', 'Mexico'),
    ], string='Payment type', tracking=1)
    type_purchase = fields.Selection(selection=[
        ('purchase', 'Current Purchase Order')
    ], string='Purchase type', default='purchase', tracking=1, help='Purchase order document type')
    state = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], string='Status', default='open', tracking=1)
    campaign_line_ids = fields.One2many('campaign.marketing.line', 'campaign_id', 'Campaign lines')
    invoice_line_ids = fields.One2many('campaign.line.invoice', 'campaign_id', 'Line invoices')
    count_objectives = fields.Integer('Count objectives', compute='get_count_objectives')
    count_control = fields.Integer('Count control', compute='get_count_control')
    count_invoice_sale = fields.Integer('Count Invoice sale', compute='get_count_models')
    count_invoice_purchase = fields.Integer('Count Invoice vendor', compute='get_count_models')
    count_sale = fields.Integer('Count Sales', compute='get_count_models')
    count_purchase = fields.Integer('Count Purchase', compute='get_count_models')
    count_move = fields.Integer('Count Move', compute='get_count_models')
    user_ids = fields.Many2many('res.users', 'campaign_user_rel', 'campaign_id', 'user_id', string='Optimizers')
    product_id = fields.Many2one('product.product', string='Product', domain="[('sale_ok', '=', True)]", tracking=1)
    amount_total = fields.Float('Amount', tracking=1)
    amount_diff = fields.Float('Consumed', tracking=1, compute=_calc_revenue_control)
    amount_fee = fields.Float('Consumed Fee', tracking=1, compute=_calc_revenue_control)
    check_deleted = fields.Boolean('To delete', compute='get_delete_objectives')
    list_deleted = fields.Char('List to deleted', compute='get_delete_objectives')
    check_change = fields.Boolean('Change?')
    order_ids = fields.One2many('sale.order.line', 'campaign_elogia_id', 'Sales')
    invoice_ids = fields.One2many('account.move', 'campaign_elogia_id', 'Moves')
    purchase_ids = fields.One2many('purchase.order.line', 'campaign_elogia_id', 'Purchase')
    check_generated = fields.Boolean('Generated objectives', compute='get_new_objectives')

    def set_closed(self):
        self.state = 'closed'

    def set_open(self):
        self.state = 'open'

    def get_delete_objectives(self):
        env_objective = self.env['objective.campaign.marketing']
        check_deleted = False
        for record in self:
            record.list_deleted = ''
            obj_objectives = env_objective.search([('campaign_id', '=', record.id), ('check_deleted', '=', True)])
            if obj_objectives:
                check_deleted = True
                record.list_deleted = list(set([objective.period.name for objective in obj_objectives]))
            record.check_deleted = check_deleted

    def create_line(self, record):
        env_campaign_line = self.env['campaign.marketing.line']
        if record.product_id:
            if record.product_id not in record.campaign_line_ids.mapped('product_id'):
                env_campaign_line.create(
                    {'product_id': record.product_id.id,
                     'name': record.product_id.name,
                     'amount_total': record.product_id.list_price,
                     'campaign_id': record.id
                     })

    @api.onchange('analytic_account_id')
    def onchange_fields_by_analytic(self):
        if self.analytic_account_id:
            self.client_id = self.analytic_account_id.partner_id.id
            self.currency_id = self.analytic_account_id.currency_id.id
            self.company_id = self.analytic_account_id.company_id.id

    @api.onchange('project_id')
    def onchange_fields_by_project(self):
        env_users = self.env['res.users']
        if self.project_id:
            if not self.client_id:
                self.client_id = self.project_id.partner_id.id
            if not self.company_id:
                self.company_id = self.analytic_account_id.company_id.id
            self.date_start = self.project_id.date_start
            self.date = self.project_id.date
            list_followers = self.project_id.message_follower_ids.partner_id
            group_ids = [self.env.ref('elogia_sale.sale_elogia_user_group').id,
                         self.env.ref('elogia_sale.sale_elogia_manager_group').id]
            if list_followers:
                obj_user_ids = env_users.search([('groups_id', 'in', group_ids), ('partner_id', 'in', list_followers.ids)])
                self.user_ids = obj_user_ids

    @api.depends('date_start', 'date', 'campaign_line_ids')
    def get_new_objectives(self):
        env_historical = self.env['historical.date.objectives']
        env_objective = self.env['objective.campaign.marketing']
        check_generated = False
        for record in self:
            obj_historical = env_historical.search([('campaign_id', '=', record.id)], order='id desc')
            if record.date_start and record.date:
                if not record.count_objectives:
                    check_generated = True
                if obj_historical:
                    obj_historical_date = obj_historical.filtered(
                        lambda e: e.date_start == record.date_start and e.date == record.date)
                    if not obj_historical_date:
                        check_generated = True
            obj_objective = env_objective.search([('campaign_id', '=', record.id)])
            if obj_objective and record.campaign_line_ids:
                lines_no_obj = [item for item in record.campaign_line_ids if
                                item.id not in obj_objective.mapped('campaign_line_id').ids]
                if lines_no_obj:
                    check_generated = True
            record.check_generated = check_generated

    @api.onchange('check_change')
    def onchange_user_ids(self):
        group_ids = [self.env.ref('elogia_sale.sale_elogia_user_group').id,
                     self.env.ref('elogia_sale.sale_elogia_manager_group').id]
        domain = {
            'user_ids': False,
        }
        values = {
            'user_ids': False,
        }
        if group_ids:
            domain = {'user_ids': [('groups_id', 'in', group_ids)]}
        self.update(values)
        return {'domain': domain}

    @api.constrains('product_id', 'percentage_fee')
    def check_values_parent(self):
        for record in self:
            self.create_line(record)
            if record.percentage_fee and self.campaign_line_ids:
                record.campaign_line_ids.write({'percentage_fee': record.percentage_fee})

    def set_generated(self):
        """Generate objectives = product * count month"""
        env_objective = self.env['objective.campaign.marketing']
        env_historical = self.env['historical.date.objectives']
        for record in self:
            if not record.campaign_line_ids:
                raise UserError(_('There are no campaign lines created in this Campaign!'))
            if not record.user_ids:
                raise UserError(_('There are no Optimizers created in this Campaign!'))
            else:
                if record.date_start and record.date:
                    list_months = self.get_list_month(record.date_start, record.date)
                    filter_months = list_months
                    campaign_lines = record.campaign_line_ids
                    obj_objective = env_objective.search([('campaign_id', '=', record.id)])
                    if obj_objective:
                        lines_no_obj = [item for item in campaign_lines if item.id not in obj_objective.mapped('campaign_line_id').ids]
                        if lines_no_obj:
                            self.create_objectives(record, filter_months, lines_no_obj, env_objective)
                        else:
                            filter_months = [month for month in list_months if list_months and month.month
                                             not in obj_objective.mapped('month_actual')
                                             and obj_objective.mapped('campaign_line_id')
                                             not in record.campaign_line_ids.ids]
                            self.create_objectives(record, filter_months, campaign_lines, env_objective)
                    else:
                        self.create_objectives(record, filter_months, campaign_lines, env_objective)
                    env_historical.create({'date_start': record.date_start, 'date': record.date, 'campaign_id': record.id})
                    list_filter = [month.month for month in list_months]
                    obj_objective.filtered(lambda e: e.month_actual not in list_filter).write({'check_deleted': True})

    def generate_period(self, month):
        env_period = self.env['period.campaign']
        obj_period = env_period.search([('name_month', '=', month.month), ('company_id', '=', self.company_id.id)],
                                       limit=1)
        if obj_period:
            val_period = obj_period
        else:
            val_period = env_period.create({
                    'name_month': month.month,
                    'name_year': month.year,
                    'company_id': self.company_id.id
                })
        return val_period.id

    def create_objectives(self, record, filter_months, list_lines, env_objective):
        for month in filter_months:
            list_add_item = [
                {'name': record.name + ' ' + item.product_id.name + ' ' + MONTHS[month.month - 1],
                 'campaign_line_id': item.id, 'client_id': record.client_id.id,
                 'analytic_account_id': record.analytic_account_id.id, 'campaign_id': record.id,
                 'project_id': record.project_id.id, 'product_id': item.product_id.id,
                 'period': self.generate_period(month), 'amount_period': item.amount_total,
                 'month_actual': month.month, 'type_payment': record.type_payment}
                for item in list_lines]
            env_objective.create(list_add_item)

    def action_view_objectives(self):
        action = self.env["ir.actions.actions"]._for_xml_id("elogia_sale.action_objective_campaign_marketing")
        action['domain'] = [('campaign_id', '=', self.id)]
        return action

    def action_view_control(self):
        action = self.env["ir.actions.actions"]._for_xml_id("elogia_sale.action_control_campaign_marketing")
        action['domain'] = [('campaign_id', '=', self.id)]
        action['context'] = {'default_campaign_id': self.id, 'default_analytic_account_id': self.analytic_account_id.id}
        return action

    def action_view_sales(self):
        dic_return = {
            'name': 'Sale Orders',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'domain': [('id', 'in', self.order_ids.mapped('order_id').ids)],
            'context': {
                'default_partner_id': self.client_id.id,
            }
        }
        if self.order_ids:
            dic_return['view_mode'] = 'tree,form'
        else:
            dic_return['view_mode'] = 'form'
        return dic_return

    def action_view_purchases(self):
        dic_return = {
            'name': 'Purchase Orders',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'domain': [('id', 'in', self.purchase_ids.mapped('order_id').ids)],
        }
        if self.purchase_ids:
            dic_return['view_mode'] = 'tree,form'
        else:
            dic_return['view_mode'] = 'form'
        return dic_return

    def action_view_invoice_sale(self):
        obj_line = self.env['account.move.line'].search([('campaign_elogia_id', '=', self.id)])
        dic_return = {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'domain': [('id', 'in', obj_line.filtered(
                lambda e: e.move_id.move_type in ['out_invoice', 'out_refund']).mapped('move_id.id'))],
            'context': {
                'default_partner_id': self.client_id.id,
                'default_move_type': 'out_invoice'
            }
        }
        if obj_line.filtered(lambda e: e.move_id.move_type in ['out_invoice', 'out_refund']):
            dic_return['view_mode'] = 'tree,form'
        else:
            dic_return['view_mode'] = 'form'
        return dic_return

    def action_view_invoice_purchase(self):
        obj_line = self.env['account.move.line'].search([('campaign_elogia_id', '=', self.id)])
        dic_return = {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'domain': [('id', 'in', obj_line.filtered(
                lambda e: e.move_id.move_type in ['in_invoice', 'in_refund']).mapped('move_id.id'))],
            'context': {
                'default_move_type': 'in_invoice'
            }
        }
        if obj_line.filtered(lambda e: e.move_id.move_type in ['in_invoice', 'in_refund']):
            dic_return['view_mode'] = 'tree,form'
        else:
            dic_return['view_mode'] = 'form'
        return dic_return

    def action_view_moves(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
        action['domain'] = [('campaign_elogia_id', '=', self.id), ('move_type', '=', 'entry')]
        action['context'] = {'default_move_type': 'entry', 'view_no_maturity': True, 'default_campaign_elogia_id': self.id}
        return action

    def get_count_objectives(self):
        env_objective = self.env['objective.campaign.marketing']
        for record in self:
            obj_objective = env_objective.search([('campaign_id', '=', record.id)])
            record.count_objectives = len(obj_objective) if obj_objective else 0

    def get_count_control(self):
        env_control = self.env['control.campaign.marketing']
        for record in self:
            obj_control = env_control.search([('campaign_id', '=', record.id)])
            record.count_control = len(obj_control) if obj_control else 0

    def get_count_models(self):
        env_line = self.env['account.move.line']
        for record in self:
            obj_line = env_line.search([('campaign_elogia_id', '=', record.id)])
            record.count_invoice_sale = len(obj_line.filtered(
                lambda e: e.move_id.move_type in ['out_invoice', 'out_refund']).mapped('move_id')) if obj_line else 0
            record.count_invoice_purchase = len(obj_line.filtered(
                lambda e: e.move_id.move_type in ['in_invoice', 'in_refund']).mapped('move_id')) if obj_line else 0
            record.count_sale = len(record.order_ids.mapped('order_id')) if record.order_ids else 0
            record.count_purchase = len(record.purchase_ids.mapped('order_id')) if record.purchase_ids else 0
            record.count_move = len(record.invoice_ids.filtered(lambda l: l.move_type == 'entry')) \
                if record.invoice_ids else 0

    def create_invoice(self):
        env_mov = self.env['account.move']
        env_setting = self.env['campaign.accounting.setting']
        list_process = [item.id for item in self.invoice_line_ids if item.state == 'process']
        if not self.invoice_line_ids:
            raise UserError(_('There are no line invoices created in this Campaign!'))
        if len(list_process) == len(self.invoice_line_ids):
            raise UserError(_('Line invoices have been processed in this Campaign!'))
        else:
            invoice_filters = self.invoice_line_ids.filtered(lambda e: e.id not in list_process)
            for record in invoice_filters:
                obj_setting = env_setting.search([('company_id', '=', record.company_id.id)], limit=1)
                if obj_setting:
                    self.generated_account_move(record, env_mov, obj_setting)
                else:
                    raise UserError(
                        _('There are no "Accounting Settings" configured.\n '
                          'Check in Settings/Accounting Settings menu.'))

    def generated_account_move(self, record, env_mov, obj_setting):
        list_setting = [{'key': 'debit', 'value_d': obj_setting.account_debit_first},
                        {'key': 'credit', 'value_c': obj_setting.account_credit_first}]
        vals = {
            'ref': record.description,
            'date': record.invoice_date,
            'campaign_elogia_id': record.campaign_id.id,
            'move_type': 'entry',
            'currency_id': record.currency_id.id,
            'line_ids': []
        }
        for item in list_setting:
            amount_currency = record.amount
            amount_val = record.amount
            if record.currency_id != record.company_id.currency_id:
                if record.currency_id.rate > 0:
                    amount_val = record.amount / record.currency_id.rate
            vals['line_ids'].append(((0, 0, {
                'account_id': item['value_d'].id if item['key'] == 'debit' else item['value_c'].id,
                'name': record.description,
                'partner_id': record.campaign_id.client_id.id,
                'amount_currency': - amount_currency if item['key'] == 'credit' else amount_currency,
                'currency_id': record.currency_id.id,
                'debit': amount_val if item['key'] == 'debit' else 0,
                'credit': amount_val if item['key'] == 'credit' else 0
            })))
        obj_move = env_mov.with_context(check_move_validity=False).create(vals)
        if obj_move:
            record.move_id = obj_move.id
            record.campaign_id.message_post(body=_("Created move: {}") .format(obj_move.ref))
            obj_move.action_post()

    def unlink(self):
        env_control = self.env['control.campaign.marketing']
        for record in self:
            obj_control = env_control.search([('campaign_id', '=', record.id)])
            if any(obj_control.filtered(lambda e: e.state != 'cancel')):
                raise UserError(_("You can't delete a campaign if you have associated controls."))
            if any(record.invoice_ids.filtered(
                    lambda e: e.move_type in ['out_invoice', 'out_refund'] and e.state != 'cancel')):
                raise UserError(_("You can't delete a campaign if you have associated customer invoices."))
            if any(record.invoice_ids.filtered(
                    lambda e: e.move_type in ['in_invoice', 'in_refund'] and e.state != 'cancel')):
                raise UserError(_("You can't delete a campaign if you have associated vendor invoices."))
            if any(record.invoice_ids.filtered(lambda e: e.move_type == 'entry' and e.state != 'cancel')):
                raise UserError(_("You can't delete a campaign if you have associated move lines."))
            if any(record.order_ids.filtered(lambda e: e.state not in ['draft', 'cancel'])):
                raise UserError(_("You can't delete a campaign if you have associated sale orders."))
            if any(record.purchase_ids.filtered(lambda e: e.state not in ['draft', 'cancel'])):
                raise UserError(_("You can't delete a campaign if you have associated purchase orders."))
        res = super(CampaignMarketingElogia, self).unlink()
        return res

    @staticmethod
    def get_list_month(start_date, end_date):
        """ This method return a list of every month inside the period"""
        difference = ((end_date.year - start_date.year) * 12 + end_date.month - start_date.month) + 1
        i = 0
        list_month = []
        for i in range(difference - i):
            list_month.append(fields.Date.to_date(start_date).replace(day=1) + relativedelta(months=i))
        return list_month

