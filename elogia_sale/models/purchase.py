# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


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

