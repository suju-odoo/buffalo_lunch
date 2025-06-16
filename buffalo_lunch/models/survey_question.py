from odoo import api, fields, models,  _
from datetime import datetime
import calendar
import json
import collections
import itertools
import operator


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
    lunch_survey_stats_text = fields.Html(
        string='Lunch Survey Statistics',
        compute='_compute_lunch_survey_stats_text',
        store=False,
        help="Statistics for lunch survey questions, showing Yes, Yes (Vegan)"
    )

    @api.depends('user_input_line_ids.user_input_id.state',
                 'user_input_line_ids.user_input_id.partner_id.is_vegan',
                 'user_input_line_ids.suggested_answer_id.value',
                 'user_input_line_ids.value_char_box',
                 'user_input_line_ids.skipped')
    def _compute_lunch_survey_stats_text(self):
        """
        Computes a formatted HTML string summarizing Yes, Yes (Vegan)
        for 'lunch' type survey questions. It filters user inputs to count only the
        most representative answer per unique user (latest 'done' or latest overall).
        """
        for question in self:
            question.lunch_survey_stats_text = "" # Default empty

            if question.survey_id.survey_type == 'lunch' and question.question_type == 'simple_choice':
                # Get all user input lines for this specific question
                current_question_user_input_lines = question.user_input_line_ids

                unique_user_inputs_map = {}
                user_inputs_for_question = current_question_user_input_lines.mapped('user_input_id').sorted(key=lambda ui: ui.create_date, reverse=True)

                for user_input in user_inputs_for_question:
                    user_key = (user_input.partner_id.id if user_input.partner_id else None, user_input.email)
                    if user_key not in unique_user_inputs_map:
                        unique_user_inputs_map[user_key] = user_input
                    else:
                        stored_input = unique_user_inputs_map[user_key]
                        if user_input.state == 'done' and stored_input.state != 'done':
                            unique_user_inputs_map[user_key] = user_input

                processed_user_input_ids = self.env['survey.user_input'].concat(*unique_user_inputs_map.values())
                processed_answer_lines = current_question_user_input_lines.filtered(lambda line: line.user_input_id in processed_user_input_ids)

                # Call the overridden _get_stats_data_answers for this question
                table_data, _graph_data = question._get_stats_data_answers(processed_answer_lines, lunch_survey_vegan_stats=True)

                yes_count = 0
                yes_vegan_count = 0

                for item in table_data:
                    if item['value'] == _('Yes'):
                        yes_count = item['count']
                    elif item['value'] == _('Yes (Vegan)'):
                        yes_vegan_count = item['count']

                # HTML formatting
                question.lunch_survey_stats_text = f"""
                    <div style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
                        <span style="font-weight: bold;">Yes: {yes_count}</span> |
                        <span style="font-weight: bold;">Yes (Vegan): {yes_vegan_count}</span>
                    </div>
                """
            else:
                question.lunch_survey_stats_text = "" # Or some other default message

    def _prepare_statistics(self, user_input_lines):
        all_questions_data = []

        for question in self:
            question_data = {'question': question, 'is_page': question.is_page}

            if question.is_page:
                all_questions_data.append(question_data)
                continue

            current_question_user_input_lines = user_input_lines.filtered(lambda line: line.question_id == question)

            if question.survey_id.survey_type == 'lunch':
                # Custom logic for unique user inputs (latest 'Done' or latest overall)
                unique_user_inputs_map = {}  # Key: (partner_id, email) -> Value: selected user_input record
                # Sort by create_date descending to get latest first
                user_inputs_for_question = current_question_user_input_lines.mapped('user_input_id').sorted(key=lambda ui: ui.create_date, reverse=True)

                for user_input in user_inputs_for_question:
                    # Identify unique user: prefer partner_id, then email
                    user_key = (user_input.partner_id.id if user_input.partner_id else None, user_input.email)
                    if user_key not in unique_user_inputs_map:
                        # If this is the first time we see this user for this question, store the latest one
                        unique_user_inputs_map[user_key] = user_input
                    else:
                        # If we've already seen this user for this question,
                        # prioritize 'done' state. If both are 'done', keep the latest (already there).
                        # If current user_input is 'done' and the already stored one is not 'done', replace.
                        stored_input = unique_user_inputs_map[user_key]
                        if user_input.state == 'done' and stored_input.state != 'done':
                            unique_user_inputs_map[user_key] = user_input
                        # Otherwise, keep the one already stored (which is either the latest or a preferred 'done' state).

                processed_user_input_ids = self.env['survey.user_input'].concat(*unique_user_inputs_map.values())
                processed_answer_lines = current_question_user_input_lines.filtered(lambda line: line.user_input_id in processed_user_input_ids)

                if question.question_type in ['simple_choice', 'multiple_choice', 'matrix']:
                    answer_lines = processed_answer_lines.filtered(
                        lambda line: line.answer_type == 'suggestion' or (
                            line.skipped and not line.answer_type) or (
                            line.answer_type == 'char_box' and question.comment_count_as_answer)
                        )
                    comment_line_ids = processed_answer_lines.filtered(lambda line: line.answer_type == 'char_box')
                else:
                    answer_lines = processed_answer_lines
                    comment_line_ids = self.env['survey.user_input.line']

                skipped_lines = answer_lines.filtered(lambda line: line.skipped)
                done_lines = answer_lines - skipped_lines
                question_data.update(
                    answer_line_ids=answer_lines,
                    answer_line_done_ids=done_lines,
                    answer_input_done_ids=done_lines.mapped('user_input_id'),
                    answer_input_ids=answer_lines.mapped('user_input_id'),
                    comment_line_ids=comment_line_ids)
                question_data.update(question._get_stats_summary_data(answer_lines))

                table_data, graph_data = question._get_stats_data(answer_lines, lunch_survey_vegan_stats=True)
                question_data['table_data'] = table_data
                question_data['graph_data'] = json.dumps(graph_data)

            else:  # Original Odoo logic for non-lunch surveys
                # Re-call the super method for other survey types using the original user_input_lines
                # This ensures the original logic is fully preserved for non-lunch surveys.
                # The super method expects 'self' to be a single record, which it is in this loop iteration.
                super_result = super(SurveyQuestion, question)._prepare_statistics(current_question_user_input_lines)
                # Assuming super_result will contain one entry for the current question
                if super_result:
                    question_data.update(super_result[0])

            all_questions_data.append(question_data)
        return all_questions_data

    def _get_stats_data(self, user_input_lines, lunch_survey_vegan_stats=False):
        if self.question_type == 'simple_choice':
            return self._get_stats_data_answers(user_input_lines, lunch_survey_vegan_stats)
        elif self.question_type == 'multiple_choice':
            table_data, graph_data = self._get_stats_data_answers(user_input_lines, lunch_survey_vegan_stats)
            return table_data, [{'key': self.title, 'values': graph_data}]
        else:
            # For other question types, call the original method from the superclass.
            # The original _get_stats_data does not take the lunch_survey_vegan_stats parameter,
            # so we ensure it's not passed to super.
            return super()._get_stats_data(user_input_lines)

    def _get_stats_data_answers(self, user_input_lines, lunch_survey_vegan_stats=False):
        # Re-implementing the core logic of original _get_stats_data_answers
        # to correctly integrate the 'Yes (Vegan)' logic.
        
        suggested_answers = [answer for answer in self.mapped('suggested_answer_ids')]
        # This dummy record is for comments counted as answers, usually "Other (see comments)"
        comment_dummy_answer = self.env['survey.question.answer']
        if self.comment_count_as_answer:
            suggested_answers.append(comment_dummy_answer)

        counts = collections.defaultdict(int)
        
        yes_answer_obj = self.suggested_answer_ids.filtered(lambda a: a.value == 'Yes')

        for line in user_input_lines.filtered(lambda l: not l.skipped): # Only count non-skipped lines
            if line.suggested_answer_id:
                if lunch_survey_vegan_stats and line.suggested_answer_id == yes_answer_obj:
                    # Check if partner exists and is vegan
                    if line.user_input_id.partner_id and line.user_input_id.partner_id.is_vegan:
                        counts['Yes (Vegan)'] += 1
                    else:
                        counts[line.suggested_answer_id.id] += 1 # Original 'Yes' count (non-vegan)
                else:
                    counts[line.suggested_answer_id.id] += 1
            elif line.value_char_box and self.comment_count_as_answer:
                counts[comment_dummy_answer.id] += 1 # Use dummy record ID as key

        table_data = []
        graph_data = []

        # Add 'Yes (Vegan)' if counted
        if lunch_survey_vegan_stats and 'Yes (Vegan)' in counts and counts['Yes (Vegan)'] > 0:
            table_data.append({
                'value': _('Yes (Vegan)'),
                'suggested_answer': comment_dummy_answer, # Use dummy record for display purposes
                'count': counts['Yes (Vegan)'],
                'count_text': _("%s Votes", counts['Yes (Vegan)']),
            })
            graph_data.append({
                'text': _('Yes (Vegan)'),
                'count': counts['Yes (Vegan)'],
            })
        
        # Iterate through all relevant suggested answers (including the dummy comment answer)
        for suggested_answer in suggested_answers:
            current_answer_id = suggested_answer.id if suggested_answer else comment_dummy_answer.id
            
            # If it's the 'Yes' answer and we are doing vegan stats, it means it has been handled
            # or split. So, we only add the remaining non-vegan 'Yes' count if any.
            if lunch_survey_vegan_stats and suggested_answer == yes_answer_obj:
                # If 'Yes (Vegan)' was processed, the original 'Yes' count only holds non-vegan 'Yes' answers
                if counts.get(current_answer_id, 0) > 0: # Only add if there are non-vegan 'Yes' answers
                    table_data.append({
                        'value': suggested_answer.value_label,
                        'suggested_answer': suggested_answer,
                        'count': counts[current_answer_id],
                        'count_text': _("%s Votes", counts[current_answer_id]),
                    })
                    graph_data.append({
                        'text': suggested_answer.value_label,
                        'count': counts[current_answer_id],
                    })
                continue # Skip this suggested_answer as it's already handled (split or not)
            
            if current_answer_id in counts:
                table_data.append({
                    'value': _('Other (see comments)') if not suggested_answer else suggested_answer.value_label,
                    'suggested_answer': suggested_answer,
                    'count': counts[current_answer_id],
                    'count_text': _("%s Votes", counts[current_answer_id]),
                })
                graph_data.append({
                    'text': _('Other (see comments)') if not suggested_answer else suggested_answer.value_label,
                    'count': counts[current_answer_id],
                })
        
        return table_data, graph_data

