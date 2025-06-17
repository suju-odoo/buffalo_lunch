from odoo import api, fields, models,  _


class LunchProduct(models.Model):
    _inherit = 'lunch.product'

    question_ids = fields.Many2many(
        'survey.question',
        'survey_question_lunch_product_rel',
        'product_ids',
        'question_ids',
        string='Questions'
    )
    
    special_description = fields.Html(
        string='Allergens, etc.,',
        sanitize=False,
        translate=True,
    )
