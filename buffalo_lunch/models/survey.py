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
                'constr_mandatory': True
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
        new_survey.questions_layout = "one_page"
        new_survey.access_mode = "token"
        new_survey.users_login_required = True
        new_survey._populate_lunch_questions()
        return new_survey

    @api.model
    def open_next_lunch_survey_form(self):
        # create next lunch survey and open form view
        new_survey = self.create_next_lunch_survey()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'survey.survey',
            'res_id': new_survey.id,
            'view_mode': 'form',
            'name': 'Lunch Survey',
            'views': [(self.env.ref('buffalo_lunch.buffalo_lunch_survey_form_base').id, 'form')],
            'target': 'current',
        }

    def action_buffalo_survey_user_input_completed(self):
        action = self.env['ir.actions.act_window']._for_xml_id('buffalo_lunch.action_survey_user_input')
        ctx = dict(self.env.context)
        ctx.update(
            {
                'search_default_survey_id': self.ids[0],
                'search_default_completed': 1,
                'search_default_group_by_partner': 1,
            }
        )
        action['context'] = ctx
        return action
    
    def action_buffalo_survey_user_input(self):
        action = self.env['ir.actions.act_window']._for_xml_id('buffalo_lunch.action_survey_user_input')
        ctx = dict(self.env.context)
        ctx.update(
            {
                'search_default_survey_id': self.ids[0],
                'search_default_group_by_partner': 1,
            }
        )
        action['context'] = ctx
        return action

    def _compute_survey_statistic(self):
        """
        Computes statistics for surveys. For 'lunch' type surveys, it counts each unique user's
        most representative answer (prioritizing 'done' state) as one entry for statistics.
        For other survey types, it defers to the original Odoo computation.
        """
        default_vals = {
            'answer_count': 0, 'answer_done_count': 0, 'success_count': 0,
            'answer_score_avg': 0.0, 'success_ratio': 0.0
        }

        lunch_surveys = self.filtered(lambda s: s.survey_type == 'lunch')
        other_surveys = self - lunch_surveys # records in self but not in lunch_surveys

        # Apply original computation for non-lunch surveys
        if other_surveys:
            super(Survey, other_surveys)._compute_survey_statistic()

        # Apply custom computation for lunch surveys
        if lunch_surveys:
            stat = dict((cid, dict(default_vals, total_score=0.0, unique_done_inputs_count=0)) for cid in lunch_surveys.ids)

            user_inputs = self.env['survey.user_input'].search([
                ('survey_id', 'in', lunch_surveys.ids),
                ('test_entry', '=', False)
            ], order='create_date desc')

            unique_user_inputs_map = {}

            for user_input in user_inputs:
                survey_id = user_input.survey_id.id
                user_key = (user_input.partner_id.id if user_input.partner_id else None, user_input.email)
                composite_key = (survey_id, user_key)

                if composite_key not in unique_user_inputs_map:
                    unique_user_inputs_map[composite_key] = user_input
                else:
                    stored_input = unique_user_inputs_map[composite_key]
                    if user_input.state == 'done' and stored_input.state != 'done':
                        unique_user_inputs_map[composite_key] = user_input

            for selected_input in unique_user_inputs_map.values():
                survey_id = selected_input.survey_id.id
                current_stat = stat[survey_id]

                current_stat['answer_count'] += 1

                if selected_input.state == 'done':
                    current_stat['answer_done_count'] += 1
                    current_stat['total_score'] += selected_input.scoring_percentage
                    current_stat['unique_done_inputs_count'] += 1
                    if selected_input.scoring_success:
                        current_stat['success_count'] += 1

            for survey_id, survey_stats in stat.items():
                total_score = survey_stats.pop('total_score')
                unique_done_count = survey_stats.pop('unique_done_inputs_count')

                survey_stats['answer_score_avg'] = total_score / (unique_done_count or 1)
                survey_stats['success_ratio'] = (survey_stats['success_count'] / (survey_stats['answer_done_count'] or 1.0)) * 100

            for survey in lunch_surveys:
                survey.update(stat.get(survey.id, default_vals))
