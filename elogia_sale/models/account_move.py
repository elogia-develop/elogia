# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    campaign_elogia_id = fields.Many2one('campaign.marketing.elogia', 'Campaigns', ondelete='restrict', tracking=1)
    control_id = fields.Many2one('control.campaign.marketing', 'Control', ondelete='restrict', tracking=1)

    @api.constrains('invoice_origin')
    def check_ref_in_sale(self):
        env_order = self.env['sale.order']
        for record in self:
            if record.invoice_origin:
                obj_order = env_order.search([('name', 'like', record.invoice_origin)], limit=1)
                if obj_order:
                    record.control_id = obj_order.control_id.id
                    record.campaign_elogia_id = obj_order.campaign_elogia_id.id
