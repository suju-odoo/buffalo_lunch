from odoo import api, fields, models,  _


class Partner(models.Model):
    _inherit = "res.partner"
    is_vegan = fields.Boolean(string='Is Vegan', default=False)
