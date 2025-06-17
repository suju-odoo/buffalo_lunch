from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request, route
import calendar
from datetime import timedelta, date

class CustomerPortalBuffalo(CustomerPortal):
    def _get_optional_fields(self):
        optional_fields = super()._get_optional_fields()
        optional_fields.append('is_vegan')
        return optional_fields


    @route(['/my/account'], type='http', auth='user', website=True)
    def account(self, redirect=None, **post):
        # OVERRIDE
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        values.update({
            'error': {},
            'error_message': [],
        })

        if post and request.httprequest.method == 'POST':
            if not partner.can_edit_vat():
                post['country_id'] = str(partner.country_id.id)

            error, error_message = self.details_form_validate(post)
            values.update({'error': error, 'error_message': error_message})
            values.update(post)
            if not error:
                values = {key: post[key] for key in self._get_mandatory_fields()}
                values.update({key: post[key] for key in self._get_optional_fields() if key in post})
                for field in set(['country_id', 'state_id']) & set(values.keys()):
                    try:
                        values[field] = int(values[field])
                    except:
                        values[field] = False
                values.update({'zip': values.pop('zipcode', '')})
                # OVERRIDE START
                if values.get('is_vegan'):
                    values['is_vegan'] = True
                else:
                    values['is_vegan'] = False
                # OVERRIDE START
                self.on_account_update(values, partner)
                partner.sudo().write(values)
                if redirect:
                    return request.redirect(redirect)
                return request.redirect('/my/home')

        countries = request.env['res.country'].sudo().search([])
        states = request.env['res.country.state'].sudo().search([])

        values.update({
            'partner': partner,
            'countries': countries,
            'states': states,
            'has_check_vat': hasattr(request.env['res.partner'], 'check_vat'),
            'partner_can_edit_vat': partner.can_edit_vat(),
            'redirect': redirect,
            'page_name': 'my_details',
        })

        response = request.render("portal.portal_my_details", values)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response

    @route(['/lunch'], type='http', auth='public', website=True)
    def lunch_page(self, week_offset=0, **post):
        try:
            week_offset = int(week_offset)
        except ValueError:
            week_offset = 0

        today = date.today()
        # Calculate the Monday of the target week based on week_offset
        # If week_offset is 0 and today is Saturday or Sunday, adjust to the next Monday
        if week_offset == 0 and today.weekday() >= 5:  # 5 for Saturday, 6 for Sunday
            # Move to the upcoming Monday
            days_until_monday = (7 - today.weekday()) % 7
            display_week_start = today + timedelta(days=days_until_monday)
        else:
            # Calculate Monday of the week determined by week_offset
            current_week_monday = today - timedelta(days=today.weekday())
            display_week_start = current_week_monday + timedelta(weeks=week_offset)

        display_week_end = display_week_start + timedelta(days=4) # Friday of the target week

        # Search for a lunch survey that spans the display week
        # Prioritize surveys that directly contain the start of the display week
        lunch_survey = request.env['survey.survey'].sudo().search([
            ('survey_type', '=', 'lunch'),
            ('date_from', '<=', display_week_end),
            ('date_end', '>=', display_week_start),
            ('question_ids.product_ids', '!=', False),
            ('question_ids.date', '!=', False)
        ], order='create_date desc', limit=1)

        # If no survey found for the exact week_offset and it's the current week,
        # try to find the next available survey.
        if not lunch_survey and week_offset == 0:
            lunch_survey = request.env['survey.survey'].sudo().search([
                ('survey_type', '=', 'lunch'),
                ('date_from', '>=', today),
                ('question_ids.product_ids', '!=', False),
                ('question_ids.date', '!=', False)
            ], order='date_from asc', limit=1)
            # If a next survey is found, adjust display_week_start to its week's Monday
            if lunch_survey:
                display_week_start = lunch_survey.date_from - timedelta(days=lunch_survey.date_from.weekday())
                display_week_end = display_week_start + timedelta(days=4)
                week_offset = (display_week_start - (today - timedelta(days=today.weekday()))).days // 7

        survey_date_from = lunch_survey.date_from if lunch_survey else False
        survey_date_end = lunch_survey.date_end if lunch_survey else False

        questions = request.env['survey.question'].sudo().search([
            ('survey_id', '=', lunch_survey.id if lunch_survey else 0),
            ('product_ids', '!=', False),
            # Filter questions to be within the determined display week
            ('date', '>=', display_week_start),
            ('date', '<=', display_week_end),
        ], order='date asc')

        lunch_menu_by_day = {}
        
        for i in range(5):  # Monday (0) to Friday (4)
            current_day = display_week_start + timedelta(days=i)
            day_name = calendar.day_name[current_day.weekday()]
            lunch_menu_by_day[day_name] = {
                'date': current_day,
                'questions': [],
                'day_user_answer': None # Initialize user answer for the day
            }

        for question in questions:
            if question.date:
                day_name = calendar.day_name[question.date.weekday()]
                if day_name in lunch_menu_by_day: # Ensure the day is one of Mon-Fri for the current week
                    product = question.product_ids[0]
                    user_answer_for_question = None
                    if request.env.user.id:
                        user_answer_for_question = question.get_answer_of_user(request.env.user.id)

                    lunch_menu_by_day[day_name]['questions'].append({
                        'id': question.id,
                        'name': product.name,
                        'description': product.description,
                        'image_url': request.website.image_url(product, 'image_1920'),
                        'question_title': question.title,
                        'product_id': product.id,
                        'user_answer': user_answer_for_question, # Still keep individual question answer for flexibility
                    })

                    # Determine the overall user answer for the day
                    # If any question for the day has a 'Yes' answer, mark the day as 'Yes'
                    # If no 'Yes' but at least one 'No', mark as 'No'
                    if user_answer_for_question in ['Yes', 'Yes (Vegan)']:
                        lunch_menu_by_day[day_name]['day_user_answer'] = user_answer_for_question
                    elif lunch_menu_by_day[day_name]['day_user_answer'] is None and user_answer_for_question == 'No':
                        lunch_menu_by_day[day_name]['day_user_answer'] = 'No'

        values = {
            'lunch_survey': lunch_survey,
            'survey_date_from': survey_date_from,
            'survey_date_end': survey_date_end,
            'lunch_menu_by_day': lunch_menu_by_day,
            'page_name': 'lunch',
            'week_offset': week_offset,
        }
        return request.render('buffalo_lunch.lunch_portal_page', values)
