# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _
from odoo.tools import format_date
from odoo.exceptions import UserError

from dateutil.relativedelta import relativedelta


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.depends('order_line')
    def _compute_qty_lines(self):
        for record in self:
            record.product_qty = sum(record.order_line.mapped('product_qty'))
            record.qty_invoiced = sum(record.order_line.mapped('qty_invoiced'))
            record.qty_to_invoice = sum(record.order_line.mapped('qty_to_invoice'))

    check_vertical = fields.Boolean('From vertical?')
    product_qty = fields.Float(compute='_compute_qty_lines', string='Quantity', tracking=1)
    qty_invoiced = fields.Float(compute='_compute_qty_lines', string='Billed Qty', tracking=1)
    qty_to_invoice = fields.Float(compute='_compute_qty_lines', string='To Invoice Quantity',
                                  digits='Product Unit of Measure', tracking=1)
    state_expense = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('full', 'Full'),
    ], string='Provisioned', compute='get_state_by_qty')
    count_expense = fields.Integer('Count Expenses', compute='get_count_move')
    move_line_ids = fields.Many2many('account.move', 'rel_purchase_move', 'purchase_id', 'move_id', 'Moves')

    def action_view_expense(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
        action['domain'] = [('id', 'in', self.move_line_ids.ids), ('move_type', '=', 'entry'),
                            ('type_move', '=', 'provision')]
        action['context'] = {
            'default_move_type': 'entry',
            'view_no_maturity': True,
            'default_type_move': 'provision'
        }
        return action

    def get_count_move(self):
        for record in self:
            record.count_expense = len((record.move_line_ids.filtered(
                lambda l: l.move_type == 'entry' and l.type_move == 'provision')))

    @api.depends('product_qty', 'qty_invoiced', 'qty_to_invoice')
    def get_state_by_qty(self):
        for record in self:
            state = 'no'
            if record.qty_invoiced >= record.product_qty:
                state = 'full'
            if record.qty_to_invoice > 0 and any(record.move_line_ids.filtered(
                    lambda e: e.state != 'cancel' and e.reversed_entry_id)):
                state = 'yes'
            record.state_expense = state

    def create_expense_entry(self):
        env_mov = self.env['account.move']
        env_setting = self.env['expense.entry.setting']
        obj_setting = env_setting.search([('company_id', '=', self.company_id.id)])
        if not obj_setting:
            raise UserError(_('There are no configured Expense Entries created'))
        else:
            for record in self:
                if record.state_expense == 'full':
                    raise UserError(_('You cannot generate an Expense Entry for an order in "Full" status.'))
                else:
                    self.generated_account_move(record, env_mov, obj_setting)

    def generated_account_move(self, record, env_mov, obj_setting):
        line_ids = [{
            'product': item.product_id,
            'line': item,
            'journal': False,
            'passive': False,
            } for item in record.order_line
        ]
        for line in line_ids:
            if line['product'].property_account_expense_id not in obj_setting.mapped('expense_account'):
                raise UserError(_('Expense account for the products: {} is not set up.'
                                  .format(line['product'].name)))
            else:
                list_setting = [{'setting': item, 'expenses': item.mapped('expense_account').ids}
                                for item in obj_setting]
                for setting in list_setting:
                    if line['product'].property_account_expense_id.id in setting['expenses']:
                        line['journal'] = setting['setting'].journal_id
                        line['passive'] = setting['setting'].passive_account
        if line_ids:
            journal = [item['journal'] for item in line_ids]
            unique_journal = [item['journal'].name for item in line_ids]
            if len(set(unique_journal)) > 1:
                raise UserError(_('Different journals: {} are configured for the same purchase order {}.'
                                  .format(list(set(unique_journal)), record.name)))
            else:
                dict_move = {
                    'ref': _('Accrued Expense entry as of %s', format_date(self.env, record.date_planned)),
                    'journal_id': journal[0].id if journal else False,
                    'date': record.date_planned,
                    'move_type': 'entry',
                    'partner_id': record.partner_id.id,
                    'currency_id': record.currency_id.id,
                    'type_move': 'provision',
                    'line_ids': [],
                }
                purchase_by_account = self._group_purchase_by_account(line_ids)
                for purchase_key, purchase_value in purchase_by_account.items():
                    purchase_by_passive = self._group_purchase_by_passive(purchase_value)
                    if purchase_by_passive:
                        for passive_key, passive_value in purchase_by_passive.items():
                            val_amount = 0
                            if len(set([item['passive'] for item in passive_value])) == 1:
                                if record.qty_to_invoice == record.product_qty:
                                    val_amount = sum([item['line'].price_subtotal for item in passive_value])
                                if record.product_qty > record.qty_to_invoice > 0:
                                    val_amount = sum([item['line'].qty_to_invoice * item['line'].price_unit for item in passive_value])
                                if record.currency_id != record.company_id.currency_id and record.currency_id.rate > 0:
                                    val_amount = val_amount / record.currency_id.rate
                                line_move = {
                                    'account_id': purchase_key.id,
                                    'name': record.name + ' - Accrued Expense by {}' .format(passive_value[0]['line'].account_analytic_id.name),
                                    'partner_id': record.partner_id.id,
                                    'control_id': passive_value[0]['line'].control_id.id,
                                    'campaign_elogia_id': passive_value[0]['line'].campaign_elogia_id.id,
                                    'amount_currency': val_amount,
                                    'currency_id': record.currency_id.id,
                                    'debit': val_amount,
                                    'credit': 0,
                                    'analytic_account_id': passive_value[0]['line'].account_analytic_id.id
                                }
                                line_expense = {
                                    'account_id': passive_key.id,
                                    'name': 'Total accrued',
                                    'partner_id': record.partner_id.id,
                                    'control_id': passive_value[0]['line'].control_id.id,
                                    'campaign_elogia_id': passive_value[0]['line'].campaign_elogia_id.id,
                                    'amount_currency': val_amount,
                                    'currency_id': record.currency_id.id,
                                    'debit': 0,
                                    'credit': val_amount,
                                    'analytic_account_id': passive_value[0]['line'].account_analytic_id.id
                                }
                                dict_move['line_ids'].append((0, 0, line_move))
                                dict_move['line_ids'].append((0, 0, line_expense))
                obj_move = env_mov.with_context(check_move_validity=False).create(dict_move)
                if obj_move:
                    record.move_line_ids += obj_move
                    record.message_post(body=_("Created move: {}") .format(obj_move.ref))
                    obj_move._post()
                    reverse_move = obj_move._reverse_moves(default_values_list=[{
                        'ref': _('Reversal of: %s', obj_move.ref),
                        'date': record.date_planned + relativedelta(years=100),
                    }])
                    reverse_move.write({'date': record.date_planned + relativedelta(years=100)})
                    reverse_move._post()
                    record.move_line_ids += reverse_move

    def _group_purchase_by_account(self, lines):
        """"
        Function to group the purchase by account
        """
        purchase_by_account = {}
        for record in lines:
            account = record['product'].property_account_expense_id
            if account not in purchase_by_account:
                purchase_by_account[account] = [record]
            else:
                purchase_by_account[account].append(record)
        return purchase_by_account

    def _group_purchase_by_passive(self, lines):
        """"
        Function to group the purchase by passive
        """
        purchase_by_passive = {}
        for record in lines:
            passive = record['passive']
            if passive not in purchase_by_passive:
                purchase_by_passive[passive] = [record]
            else:
                purchase_by_passive[passive].append(record)
        return purchase_by_passive


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _get_default_campaign(self):
        env_campaign = self.env['campaign.marketing.elogia']
        env_control = self.env['control.campaign.marketing']
        if 'active_model' in self._context:
            if self._context.get('active_model') == 'campaign.marketing.elogia':
                return env_campaign.search([('id', '=', self._context.get('active_id'))], limit=1)
            elif self._context.get('active_model') == 'control.campaign.marketing':
                return env_control.search([('id', '=', self._context.get('active_id'))], limit=1).mapped('campaign_id')

    def _get_default_control(self):
        env_control = self.env['control.campaign.marketing']
        if 'active_model' in self._context:
            if self._context.get('active_model') == 'control.campaign.marketing':
                return env_control.search([('id', '=', self._context.get('active_id'))], limit=1)

    def _get_default_account(self):
        env_campaign = self.env['campaign.marketing.elogia']
        env_control = self.env['control.campaign.marketing']
        if 'active_model' in self._context:
            if self._context.get('active_model') == 'campaign.marketing.elogia':
                return env_campaign.search([('id', '=', self._context.get('active_id'))], limit=1).mapped('analytic_account_id')
            elif self._context.get('active_model') == 'control.campaign.marketing':
                return env_control.search([('id', '=', self._context.get('active_id'))], limit=1).mapped('analytic_account_id')

    campaign_elogia_id = fields.Many2one('campaign.marketing.elogia', 'Campaigns', ondelete='restrict',
                                         default=_get_default_campaign)
    control_id = fields.Many2one('control.campaign.marketing', 'Control', ondelete='restrict',
                                 default=_get_default_control)
    account_analytic_id = fields.Many2one('account.analytic.account', store=True, string='Analytic Account',
                                          compute='_compute_account_analytic_id', readonly=False,
                                          default=_get_default_account)

    def _prepare_account_move_line(self, move=False):
        res = super(PurchaseOrderLine, self)._prepare_account_move_line(move=False)
        res.update({
            'campaign_elogia_id': self.campaign_elogia_id.id,
            'control_id': self.control_id.id
        })
        return res

    @api.constrains('state')
    def check_state_by_purchase_line(self):
        env_line = self.env['control.line.supplier']
        for record in self:
            if record.state == 'cancel':
                obj_line_ids = env_line.search([('order_line_id', '=', record.id), ('type_payment', '!=', 'client')])
                if obj_line_ids:
                    if any(obj_line_ids.mapped('control_id').filtered(lambda e: e.state != 'draft')):
                        raise UserError(_('Purchase order cannot be cancelled. \n '
                                          'The related control must be in "Draft" state!'))
                    else:
                        obj_line_ids.write({'state': 'no_process'})

