# -*- coding: utf-8 -*-
{
    'name': "buffalo_lunch",
    'summary': "Buffalo Lunch",
    'description': """
We eat lunch
    """,
    'author': "odoo-psam",
    'website': "https://www.odoo.com",
    'category': 'Custom Development',
    'version': '18.0.1.0.0',
    'depends': ['survey', 'lunch', 'contacts'],
    'data': [
        'views/survey.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'buffalo_lunch/static/src/**/*',
        ],
    },
}

