from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_is_zero


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    # def _mark_done(self):
    #     super()._mark_done()
    #     if self.survey_id.survey_type != "lunch":
    #         return
    #     inputs_to_unlink = self.survey_id.user_input_ids.filtered(lambda x: x.partner_id == self.partner_id and x.id != self.id and x.state == "done")
    #     if inputs_to_unlink:
    #         inputs_to_unlink.unlink()
