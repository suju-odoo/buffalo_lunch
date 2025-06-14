from odoo import api, fields, models,  _
from datetime import datetime
import calendar


class SurveyQuestion(models.Model):
    _inherit = "survey.question"

    date = fields.Date()
    product_ids = fields.Many2many(
        'lunch.product',
        'survey_question_lunch_product_rel',
        'question_ids',
        'product_ids',
        string='Products'
    )
    day_of_week = fields.Char(compute='_compute_day_of_week', store=True)

    @api.depends('date')
    def _compute_day_of_week(self):
        for record in self:
            if record.date:
                record.day_of_week = calendar.day_name[record.date.weekday()]
            else:
                record.day_of_week = False

    # Title = date + day 
    # food_id 
    # description = food_id.description

