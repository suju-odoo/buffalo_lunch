from odoo import api, fields, models,  _
from datetime import timedelta, datetime, date


class Survey(models.Model):
    _inherit = "survey.survey"

    date_from = fields.Date()
    date_end = fields.Date()
    survey_type = fields.Selection(selection_add=[('lunch', 'Lunch')], ondelete={'lunch': 'set default'})

    @api.depends_context('uid', 'buffalo_lunch')
    def _compute_allowed_survey_types(self):
        # Extend allowed survey types if context is from buffalo_lunch
        super()._compute_allowed_survey_types()
        if self.env.context.get('buffalo_lunch'):
            self.allowed_survey_types = (self.allowed_survey_types or []) + ['lunch']
    
    @api.model
    def _get_next_lunch_survey_dates(self):
        # Calculate the next lunch survey's date_from and date_end
        # If there is a previous lunch survey, get the next Monday and Friday after it
        # Otherwise, use this week's Monday and Friday
        today = date.today()
        # Search for the latest lunch survey, including archived ones
        latest_survey = self.env['survey.survey'].with_context(active_test=False).search([('survey_type', '=', 'lunch')], order='date_end desc', limit=1)
        if latest_survey and latest_survey.date_from:
            last_date = latest_survey.date_from
            days_ahead = 0 - last_date.weekday() + 7
            next_monday = last_date + timedelta(days=days_ahead)
            next_friday = next_monday + timedelta(days=4)
            date_from = next_monday
            date_end = next_friday
        else:
            monday = today - timedelta(days=today.weekday())
            friday = monday + timedelta(days=4)
            date_from = monday
            date_end = friday
        return date_from, date_end

    def _populate_lunch_questions(self):
        if not self.date_from or not self.date_end:
            return

        question_values = []
        current_date = self.date_from
        while current_date <= self.date_end:
            # Prepare values for each question
            question_values.append({
                'survey_id': self.id, # Link to the current survey
                'date': current_date,
                'title': current_date.strftime('%A'),
                'question_type': 'simple_choice',
                'is_page': False,
            })
            current_date += timedelta(days=1)
        
        # Create all questions in a single bulk operation for better performance
        questions = self.env['survey.question'].create(question_values)

        answer_values = []
        for question in questions:
            answer_values.append({
                'question_id': question.id,
                'value': 'Yes',
                'sequence': 1,
            })
            answer_values.append({
                'question_id': question.id,
                'value': 'No',
                'sequence': 2,
            })
        
        # Create all answers in a single bulk operation
        if answer_values:
            self.env['survey.question.answer'].create(answer_values)

        questions.survey_id = self

    @api.model
    def create_next_lunch_survey(self):
        date_from, date_end = self._get_next_lunch_survey_dates()
        new_survey = self.create({
            "date_from": date_from,
            "date_end": date_end,
            "survey_type": "lunch",
            "title": f"Lunch Survey: {date_from.strftime('%B %d, %Y')} - {date_end.strftime('%B %d, %Y')}"
        })
        new_survey._populate_lunch_questions()
        # TODO: open windowaction
