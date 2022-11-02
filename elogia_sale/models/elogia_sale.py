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
        env_control = self.env['control.campaign.marketing']
        if not env_product_setting:
            raise UserError(_('There are no "Product Settings" configured.\n Check in Settings/Product Settings menu.'))
        else:
            obj_control_ids = env_control.search([('id', 'in', self._context.get('active_ids'))])
            if obj_control_ids:
                list_not_setting = [product.name for product in obj_control_ids.mapped('campaign_line_id.product_id')
                                    if product not in env_product_setting.mapped('product_id')]
                if list_not_setting:
                    raise UserError(_('Products {} are not configured.\n Check in Settings/Product Settings menu.'
                                      .format(list_not_setting)))
                else:
                    if self.check_error:
                        raise UserError(_('There are campaign controls that cannot be processed.'))
                    else:
                        for obj_control in obj_control_ids:
                            self.action_quotation_sale(obj_control, env_product_setting)

    def action_quotation_sale(self, control, setting):
        order_lines = []
        order_obj = self.env['sale.order']
        list_line = [control.campaign_line_id.product_id]
        other_product = setting.filtered(lambda e: e.product_id == control.campaign_line_id.product_id)
        if other_product and self.check_fee:
            list_line.append(other_product.other_product_id)
        for line in list_line:
            line_vals = {}
            taxes = line.taxes_id if line.taxes_id else False
            if line.check_fee:
                price_unit = control.fee_revenue
            else:
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
            }
            order_lines.append((0, 0, line_vals))
        order_vals = {
            'partner_id': control.client_id.id,
            'date_order': self.date_order,
            'order_line': order_lines,
            'pricelist_id': control.pricelist_id.id,
            'fiscal_position_id': control.client_id.property_account_position_id.id
            if control.client_id.property_account_position_id else False,
            'currency_id': control.currency_id.id,
            'user_id': self.env.user.id,
            'analytic_account_id': control.campaign_id.analytic_account_id.id,
            'client_order_ref': self.description,
            'origin': self.reference,
            'control_id': control.id,
            'campaign_elogia_id': control.campaign_id.id
        }
        sale_order = order_obj.create(order_vals)
        if sale_order:
            _logger.info('Order Created')
            _logger.info(sale_order.name)
            control.state = 'sale'
            control.message_post(body=_("Created sale order: {}").format(sale_order.name))


class ProductFeeSetting(models.Model):
    _name = 'product.fee.setting'
    _description = 'Product Fee Setting'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', 'Product', required=True, index=True)
    other_product_id = fields.Many2one('product.product', 'Product fee', required=True)


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
    move_id = fields.Many2one('account.move', string="Move")
    state = fields.Selection([
        ('no_process', 'Not processed'),
        ('process', 'Processed')
    ], string='Status', compute='check_state_invoice', tracking=1)

    @api.depends('move_id')
    def check_state_invoice(self):
        for record in self:
            record.state = 'no_process'
            if record.invoice_id and record.move_id:
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
                    val_tmp = record.invoice_provision / record.currency_id.rate
                else:
                    val_tmp = (record.invoice_provision / record.currency_id.rate) * record.control_id.currency_id.rate
            record.invoice_provision_ml = val_tmp

    @api.model
    def create_purchase_order(self):
        for record in self:
            pass


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
                                  domain=lambda self: [('state', '=', 'open'), ('user_ids', '=', self.env.user.id)],
                                  tracking=1)
    company_id = fields.Many2one('res.company', 'Company', tracking=1)
    project_id = fields.Many2one('project.project', 'Project', tracking=1, domain=lambda self:
                                 [('message_follower_ids.partner_id', '=', self.env.user.partner_id.id)])
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
    currency_id = fields.Many2one('res.currency', string="Currency")
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
    type_invoice = fields.Selection(selection=[
        ('sale', 'Sales'),
        ('account', 'Accounting')
    ], string='Billing type', tracking=1)
    team_id = fields.Many2one('crm.team', 'Sale team', tracking=1)
    order_ids = fields.One2many('sale.order', 'control_id', 'Sales')
    invoice_ids = fields.One2many('account.move', 'control_id', 'Invoices')
    purchase_ids = fields.One2many('purchase.order', 'control_id', 'Purchase')
    fee_revenue = fields.Float('Fee revenue', tracking=1, compute='calc_price_ml', store=True)
    fee_revenue_ml = fields.Float('Fee revenue(ml)', tracking=1, compute='calc_kpi', store=True)
    billed_revenue = fields.Float('Billed revenue', tracking=1, compute='calc_kpi', store=True)
    billed_revenue_ml = fields.Float('Billed revenue(ml)', tracking=1, compute='calc_kpi', store=True)
    purchase_ml = fields.Float('Purchases(ml)', tracking=1, compute='calc_kpi', store=True)
    margin_ml = fields.Float('Margin(ml)', tracking=1, compute='calc_kpi', store=True)
    margin_factor_ml = fields.Float('Margin factor(ml)', tracking=1, compute='calc_kpi', store=True)
    check_diff = fields.Boolean('Diff', compute='get_name_campaign')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', check_company=True, tracking=1,
                                   states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
                                   domain="[('currency_id', '=', currency_id), '|', ('company_id', '=', company_id), "
                                          "('company_id', '=', False)]")

    def set_pending(self):
        for record in self:
            record.state = 'pending'

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
        for item in list_setting:
            vals['line_ids'].append(((0, 0, {
                'account_id': item['value_d'].id if item['key'] == 'debit' else item['value_c'].id,
                'name': record.name,
                'partner_id': record.client_id.id,
                'debit': record.billed_revenue_ml if item['key'] == 'debit' else 0,
                'credit': record.billed_revenue_ml if item['key'] == 'credit' else 0,
            })))
        obj_move = env_mov.with_context(check_move_validity=False).create(vals)
        if obj_move:
            record.message_post(body=_("Created move: {}") .format(obj_move.ref))

    def generate_purchase(self):
        for record in self:
            pass

    @api.onchange('campaign_id')
    def onchange_campaign_id(self):
        if self.campaign_id:
            self.project_id = self.campaign_id.project_id.id
            self.currency_id = self.campaign_id.currency_id.id
            self.company_id = self.campaign_id.company_id.id
            self.client_id = self.campaign_id.client_id.id
            self.percentage_fee = self.campaign_id.percentage_fee
            self.type_invoice = self.campaign_id.type_invoice
            self.campaign_line_id = False

    @api.onchange('client_id')
    def onchange_client_id(self):
        if self.client_id.team_id:
            self.team_id = self.client_id.team_id

    @api.onchange('campaign_line_id')
    def onchange_campaign_line_id(self):
        if self.campaign_line_id:
            self.percentage_fee = self.campaign_line_id.percentage_fee

    def get_count_models(self):
        for record in self:
            record.count_invoice_sale = len(record.invoice_ids.filtered(
                lambda e: e.move_type in ['out_invoice', 'out_refund'])) if record.invoice_ids else 0
            record.count_invoice_purchase = len(record.invoice_ids.filtered(
                lambda e: e.move_type in ['in_invoice', 'in_refund'])) if record.invoice_ids else 0
            record.count_sale = len(record.order_ids) if record.order_ids else 0
            record.count_purchase = len(record.purchase_ids) if record.purchase_ids else 0
            record.count_move = len(record.invoice_ids.filtered(lambda l: l.move_type == 'entry')) \
                if record.invoice_ids else 0

    def action_view_sales(self):
        dic_return = {
            'name': 'Sale Orders',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'domain': [('control_id', '=', self.id)],
            'context': {
                'default_partner_id': self.client_id.id,
                'default_control_id': self.id,
                'default_campaign_elogia_id': self.campaign_id.id,
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
            'domain': [('control_id', '=', self.id)],
            'context': {
                'default_control_id': self.id,
                'default_campaign_elogia_id': self.campaign_id.id,
            }
        }
        if self.purchase_ids:
            dic_return['view_mode'] = 'tree,form'
        else:
            dic_return['view_mode'] = 'form'
        return dic_return

    def action_view_invoice_sale(self):
        dic_return = {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'domain': [('campaign_elogia_id', '=', self.id), ('move_type', 'in', ['out_invoice', 'out_refund'])],
            'context': {
                'default_partner_id': self.client_id.id,
                'default_control_id': self.id,
                'default_campaign_elogia_id': self.campaign_id.id,
                'default_move_type': 'out_invoice'
            }
        }
        if self.invoice_ids.filtered(lambda l: l.move_type in ['out_invoice', 'out_refund']):
            dic_return['view_mode'] = 'tree,form'
        else:
            dic_return['view_mode'] = 'form'
        return dic_return

    def action_view_invoice_purchase(self):
        dic_return = {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'domain': [('campaign_elogia_id', '=', self.id), ('move_type', 'in', ['in_invoice', 'in_refund'])],
            'context': {
                'default_partner_id': self.client_id.id,
               'default_control_id': self.id,
                'default_campaign_elogia_id': self.campaign_id.id,
                'default_move_type': 'in_invoice'
            }
        }
        if self.invoice_ids.filtered(lambda l: l.move_type in ['in_invoice', 'in_refund']):
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
                record.amount_currency = record.amount_unit / record.currency_id.rate
            record.consume_currency = record.amount_currency * record.clicks
            record.fee_revenue = record.consume * record.percentage_fee / 100

    @api.depends('fee_revenue', 'fee_revenue_ml', 'consume', 'control_line_ids', 'billed_revenue',
                 'billed_revenue_ml', 'margin_ml')
    def calc_kpi(self):
        for record in self:
            sum_client = sum(record.control_line_ids.filtered(
                lambda e: e.type_payment == 'client').mapped('invoice_provision_ml'))
            sum_not_client = (sum(record.control_line_ids.filtered(
                lambda e: e.type_payment != 'client').mapped('invoice_provision_ml')))
            record.fee_revenue_ml = record.fee_revenue
            record.billed_revenue = record.consume + record.fee_revenue - sum_client
            record.billed_revenue_ml = record.billed_revenue
            record.margin_ml = record.billed_revenue - sum_not_client
            if record.currency_id != record.company_id.currency_id:
                record.fee_revenue_ml = record.fee_revenue / record.currency_id.rate
                record.billed_revenue_ml = record.billed_revenue / record.currency_id.rate
                record.margin_ml = (record.billed_revenue - sum_not_client) / record.currency_id.rate
            record.purchase_ml = - (sum_not_client / record.currency_id.rate) if record.currency_id else 0
            record.margin_factor_ml = record.margin_ml - record.fee_revenue_ml

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

    @api.depends('amount_period', 'percentage_margin')
    def calc_amount_margin(self):
        for record in self:
            margin = 0
            if record.amount_period and record.percentage_margin:
                margin = record.amount_period * record.percentage_margin / 100
            record.margin = margin


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
        for record in self:
            obj_control = env_control.search([('campaign_id', '=', record.id)])
            record.amount_diff = sum(obj_control.mapped('consume'))
            record.amount_fee = sum(obj_control.mapped('fee_revenue'))

    name = fields.Char('Name', index=True, required=True)
    project_id = fields.Many2one('project.project', 'Project',
                                 domain=lambda self: [('message_follower_ids.partner_id', '=', self.env.user.partner_id.id)], tracking=1)
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
    order_ids = fields.One2many('sale.order', 'campaign_elogia_id', 'Sales')
    invoice_ids = fields.One2many('account.move', 'campaign_elogia_id', 'Invoices')
    purchase_ids = fields.One2many('purchase.order', 'campaign_elogia_id', 'Purchase')

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
            env_campaign_line.create(
                {'product_id': record.product_id.id,
                 'name': record.product_id.name,
                 'amount_total': record.product_id.list_price,
                 'campaign_id': record.id
                 })

    @api.onchange('project_id')
    def onchange_fields_by_project(self):
        env_users = self.env['res.users']
        if self.project_id:
            self.client_id = self.project_id.partner_id.id
            self.date_start = self.project_id.date_start
            self.analytic_account_id = self.project_id.analytic_account_id
            self.date = self.project_id.date
            list_followers = self.project_id.message_follower_ids.partner_id
            group_ids = [self.env.ref('elogia_sale.sale_elogia_user_group').id,
                         self.env.ref('elogia_sale.sale_elogia_manager_group').id]
            if list_followers:
                obj_user_ids = env_users.search([('groups_id', 'in', group_ids), ('partner_id', 'in', list_followers.ids)])
                self.user_ids = obj_user_ids

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

    @api.onchange('client_id')
    def onchange_currency_by_client(self):
        if self.client_id and self.client_id.property_product_pricelist:
            self.currency_id = self.client_id.property_product_pricelist.currency_id.id

    @api.constrains('product_id', 'percentage_fee')
    def check_values_parent(self):
        for record in self:
            if not record.campaign_line_ids:
                self.create_line(record)
            else:
                if record.percentage_fee:
                    record.campaign_line_ids.write({'percentage_fee': record.percentage_fee})

    def set_generated(self):
        """Generate objectives = product * count month"""
        env_objective = self.env['objective.campaign.marketing']
        for record in self:
            if not record.campaign_line_ids:
                raise UserError(_('There are no campaign lines created in this Campaign!'))
            if not record.user_ids:
                raise UserError(_('There are no Optimizers created in this Campaign!'))
            else:
                if record.date_start and record.date:
                    list_months = self.get_list_month(record.date_start, record.date)
                    filter_months = list_months
                    obj_objective = env_objective.search([('campaign_id', '=', record.id)])
                    if obj_objective:
                        filter_months = [month for month in list_months if list_months
                                         and month.month not in obj_objective.mapped('month_actual')]
                    for month in filter_months:
                        list_add_item = [{'name': record.name + ' ' + item.product_id.name + ' ' + MONTHS[month.month - 1],
                                          'campaign_line_id': item.id, 'project_id': record.project_id.id,
                                          'campaign_id': record.id, 'client_id': record.client_id.id,
                                          'product_id': item.product_id.id, 'period': self.generate_period(month),
                                          'amount_period': item.amount_total, 'percentage_margin': 0, 'margin': 0,
                                          'month_actual': month.month, 'type_payment': record.type_payment}
                                         for item in record.campaign_line_ids]
                        env_objective.create(list_add_item)
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

    def action_view_objectives(self):
        action = self.env["ir.actions.actions"]._for_xml_id("elogia_sale.action_objective_campaign_marketing")
        action['domain'] = [('campaign_id', '=', self.id)]
        return action

    def action_view_control(self):
        action = self.env["ir.actions.actions"]._for_xml_id("elogia_sale.action_control_campaign_marketing")
        action['domain'] = [('campaign_id', '=', self.id)]
        action['context'] = {'default_campaign_id': self.id}
        return action

    def action_view_sales(self):
        dic_return = {
            'name': 'Sale Orders',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'domain': [('campaign_elogia_id', '=', self.id)],
            'context': {
                'default_partner_id': self.client_id.id,
                'default_campaign_elogia_id': self.id
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
            'domain': [('campaign_elogia_id', '=', self.id)],
            'context': {
                'default_campaign_elogia_id': self.id
            }
        }
        if self.purchase_ids:
            dic_return['view_mode'] = 'tree,form'
        else:
            dic_return['view_mode'] = 'form'
        return dic_return

    def action_view_invoice_sale(self):
        dic_return = {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'domain': [('campaign_elogia_id', '=', self.id), ('move_type', 'in', ['out_invoice', 'out_refund'])],
            'context': {
                'default_partner_id': self.client_id.id,
                'default_campaign_elogia_id': self.id,
                'default_move_type': 'out_invoice'
            }
        }
        if self.invoice_ids.filtered(lambda l: l.move_type in ['out_invoice', 'out_refund']):
            dic_return['view_mode'] = 'tree,form'
        else:
            dic_return['view_mode'] = 'form'
        return dic_return

    def action_view_invoice_purchase(self):
        dic_return = {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'domain': [('campaign_elogia_id', '=', self.id), ('move_type', 'in', ['in_invoice', 'in_refund'])],
            'context': {
                'default_partner_id': self.client_id.id,
                'default_campaign_elogia_id': self.id,
                'default_move_type': 'in_invoice'
            }
        }
        if self.invoice_ids.filtered(lambda l: l.move_type in ['in_invoice', 'in_refund']):
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
        for record in self:
            record.count_invoice_sale = len(record.invoice_ids.filtered(
                lambda l: l.move_type in ['out_invoice', 'out_refund'])) if record.invoice_ids else 0
            record.count_invoice_purchase = len(record.invoice_ids.filtered(
                lambda l: l.move_type in ['in_invoice', 'in_refund'])) if record.invoice_ids else 0
            record.count_sale = len(record.order_ids) if record.order_ids else 0
            record.count_purchase = len(record.purchase_ids) if record.purchase_ids else 0
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

    def generated_account_move(self, record, env_mov, obj_setting):
        list_setting = [{'key': 'debit', 'value_d': obj_setting.account_debit_first},
                        {'key': 'credit', 'value_c': obj_setting.account_credit_first}]
        vals = {
            'ref': record.description,
            'date': record.invoice_date,
            'campaign_elogia_id': record.campaign_id.id,
            'move_type': 'entry',
            'line_ids': []
        }
        for item in list_setting:
            amount_currency = record.amount
            if record.currency_id != record.company_id.currency_id:
                amount_currency = record.amount / record.currency_id.rate
            vals['line_ids'].append(((0, 0, {
                'account_id': item['value_d'].id if item['key'] == 'debit' else item['value_c'].id,
                'name': record.description,
                'partner_id': record.campaign_id.client_id.id,
                'debit': amount_currency if item['key'] == 'debit' else 0,
                'credit': amount_currency if item['key'] == 'credit' else 0,
            })))
        obj_move = env_mov.with_context(check_move_validity=False).create(vals)
        if obj_move:
            record.move_id = obj_move.id
            record.campaign_id.message_post(body=_("Created move: {}") .format(obj_move.ref))

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
            if any(record.invoice_ids.filtered(lambda e: e.state not in ['draft', 'cancel'])):
                raise UserError(_("You can't delete a campaign if you have associated sale orders."))
            if any(record.invoice_ids.filtered(lambda e: e.state not in ['draft', 'cancel'])):
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

