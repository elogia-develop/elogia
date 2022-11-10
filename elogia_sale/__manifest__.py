# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    'name': "Elogia Sale",
    'summary': 'Elogia Sale Vertical: Campaign, Sale, Purchase, Invoices, Campaign Control',
    'author': "Rapsodoo Iberia",
    'website': "https://www.rapsodoo.com/es/",
    'category': 'Sales/Sales',
    'license': 'LGPL-3',
    'version': '15.0.1.0.15',
    'depends': [
        'base',
        'sale',
        'sale_management',
        'account',
        'purchase',
        'elogia_base',
        'elogia_project'
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/elogia_view.xml',
    ],
    'application': True,
}
