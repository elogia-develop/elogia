# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    campaign_elogia_id = fields.Many2one('campaign.marketing.elogia', 'Campaigns', ondelete='restrict')
    control_id = fields.Many2one('control.campaign.marketing', 'Control', ondelete='restrict')

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
                    if any(obj_line_ids.mapped('control_id').filtered(lambda e: e.state == 'both')):
                        raise UserError(_('Purchase order cannot be cancelled. \n '
                                          'The related control is in "Processed" state!'))
                    else:
                        obj_line_ids.write({'state': 'no_process'})
                        for line in obj_line_ids:
                            if line.control_id.show_sale:
                                line.control_id.write({'state': 'pending'})
                            else:
                                if line.control_id.type_invoice == 'sale':
                                    line.control_id.write({'state': 'sale'})
                                else:
                                    if line.control_id.state not in ['cancel', 'draft']:
                                        line.control_id.write({'state': 'pending'})
