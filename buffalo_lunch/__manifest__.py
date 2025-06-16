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
    'depends': ['calendar', 'website', 'survey', 'lunch', 'contacts'],
    'data': [
        'security/survey_security.xml',
        'views/survey.xml',
        'views/survey_question.xml',
        'views/survey_actions.xml',
        'views/portal_template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'buffalo_lunch/static/src/**/*',
        ],
    },
}

