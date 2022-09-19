# Copyright 2022-TODAY Rapsodoo Iberia S.r.L. (www.rapsodoo.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    'name': "Elogia project",
    'summary': 'Changes to be consider in Elogia enviroment',
    'author': "Rapsodoo Iberia",
    'website': "https://www.rapsodoo.com/es/",
    'category': 'Project/Project',
    'license': 'LGPL-3',
    'version': '15.0.1.0.7',
    'depends': [
        'base',
        'project',
        'calendar',
        'elogia_base',
        'elogia_hr'
    ],
    'data': [
        'views/elogia_view.xml',
        'views/mail_activity_view.xml',
    ],
    'application': False,
    'assets': {
        'web.assets_backend': [
            'elogia_project/static/src/js/backend/**/*',
        ],
        'web.assets_qweb': [
            'elogia_project/static/src/xml/**/*',
        ],
    }
}
