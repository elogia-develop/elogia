# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    campaign_elogia_id = fields.Many2one('campaign.marketing.elogia', 'Campaigns', ondelete='restrict')
    control_id = fields.Many2one('control.campaign.marketing', 'Control', ondelete='restrict')
