# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    campaign_elogia_id = fields.Many2one('campaign.marketing.elogia', 'Campaigns', ondelete='restrict')
    control_id = fields.Many2one('control.campaign.marketing', 'Control', ondelete='restrict')

    def _prepare_invoice_line(self, **optional_values):
        values = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        values['campaign_elogia_id'] = self.campaign_elogia_id.id
        values['control_id'] = self.control_id.id
        return values

    @api.constrains('state')
    def check_state_by_order_line(self):
        env_control = self.env['control.campaign.marketing']
        for record in self:
            if record.state == 'cancel':
                obj_control_ids = env_control.search([('id', '=', record.control_id.id)])
                if obj_control_ids:
                    if any(obj_control_ids.filtered(lambda e: e.state == 'both')):
                        raise UserError(_('Sale order cannot be cancelled. \n '
                                          'The related control is in "Processed" state!'))
                    else:
                        for control in obj_control_ids:
                            if control.show_sale:
                                control.write({'state': 'pending'})
                            else:
                                if control.type_invoice == 'sale':
                                    control.write({'state': 'purchase'})
                                else:
                                    control.write({'state': 'pending'})
