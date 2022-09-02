# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    'name': "Elogia HR",
    'summary': 'Changes to be consider in Elogia enviroment',
    'author': "Rapsodoo Iberia",
    'website': "https://www.rapsodoo.com/es/",
    'category': 'Project/Project',
    'license': 'LGPL-3',
    'version': '15.0.1.0.5',
    'depends': [
        'base',
        'elogia_base',
        'hr',
        'hr_holidays',
        'hr_contract',
        'hr_skills',
        'hr_expense',
        'resource',
        'planning',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_view.xml',
        'data/elogia_data.xml'
    ],
    'application': False,
}
