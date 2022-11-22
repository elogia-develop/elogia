# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime


class AccountMove(models.Model):
    """ Override AccountInvoice_line to add the link to the purchase order line it is related to"""
    _inherit = 'account.move'

    type_move = fields.Selection(selection=[
        ('null', 'Null'),
        ('accounting', 'Accounting'),
        ('provision', 'Provision'),
    ], string='Type move', default='null', tracking=1)
    campaign_id = fields.Many2one('campaign.marketing.elogia', 'Campaigns', required=False)
    process_control = fields.Boolean('Process control')
    process_campaign = fields.Boolean('Process campaign')

    @api.model_create_multi
    def create(self, vals_list):
        res = super(AccountMove, self).create(vals_list)
        if res and res.line_ids.mapped('purchase_line_id.order_id'):
            purchase = res.line_ids.mapped('purchase_line_id.order_id')
            move_reverse = purchase.move_line_ids.filtered(
                lambda l: l.move_type == 'entry' and l.type_move == 'provision' and l.state == 'draft')
            val_day = datetime.today().date()
            if res.invoice_date:
                val_day = res.invoice_date
            if move_reverse:
                move_reverse.write({'date': val_day, 'auto_post': False})
                move_reverse.action_post()
        return res


class AccountMoveLine(models.Model):
    """ Override AccountInvoice_line to add the link to the purchase order line it is related to"""
    _inherit = 'account.move.line'

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
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', index=True,
                                          compute="_compute_analytic_account_id", store=True, readonly=False,
                                          check_company=True, copy=True, default=_get_default_account)

    @api.constrains('parent_state')
    def check_state_by_order_line(self):
        env_control = self.env['control.campaign.marketing']
        for record in self:
            if record.parent_state == 'cancel':
                obj_control_ids = env_control.search([('id', '=', record.control_id.id)])
                if obj_control_ids:
                    if record.move_id.process_control:
                        if any(obj_control_ids.filtered(lambda e: e.state != 'draft')):
                            raise UserError(_('Account move cannot be cancelled. \n '
                                              'The related control must be in "Draft" state!'))

