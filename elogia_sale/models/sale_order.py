# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

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
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic account', default=_get_default_account)

    def _prepare_invoice_line(self, **optional_values):
        values = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        values['campaign_elogia_id'] = self.campaign_elogia_id.id
        values['control_id'] = self.control_id.id
        values['analytic_account_id'] = self.analytic_account_id.id
        return values

    @api.constrains('state')
    def check_state_by_order_line(self):
        env_control = self.env['control.campaign.marketing']
        for record in self:
            if record.state == 'cancel':
                obj_control_ids = env_control.search([('id', '=', record.control_id.id)])
                if obj_control_ids:
                    if any(obj_control_ids.filtered(lambda e: e.state != 'draft')):
                        raise UserError(_('Sale order cannot be cancelled. \n '
                                          'The related control must be in "Draft" state!'))

