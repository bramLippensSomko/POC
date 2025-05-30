from odoo import models, fields, api, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    skills = fields.Text(help='employee skills seperated by ","')
