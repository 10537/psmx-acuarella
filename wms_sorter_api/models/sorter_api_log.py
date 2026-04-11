# -*- coding: utf-8 -*-

import datetime
from odoo import models, fields, api


class WmsSorterApiLog(models.Model):
    _name = "wms.sorter.api.log"
    _description = "WMS Sorter API Audit Log"
    _order = "create_date desc"

    name = fields.Char(string="Endpoint", readonly=True)
    method = fields.Char(string="Method", readonly=True)
    ip_address = fields.Char(string="IP Address", readonly=True)
    request_payload = fields.Text(string="Request Body", readonly=True)
    response_payload = fields.Text(string="Response Body", readonly=True)
    status_code = fields.Integer(string="HTTP Status", readonly=True)
    state = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error')
    ], string="State", compute="_compute_state", store=True)
    error_message = fields.Text(string="Error Detail", readonly=True)

    @api.depends('status_code')
    def _compute_state(self):
        for log in self:
            if not log.status_code:
                log.state = 'error'
            elif 200 <= log.status_code < 300:
                log.state = 'success'
            else:
                log.state = 'error'

    @api.model
    def cron_cleanup_logs(self):
        """Delete logs older than 30 days."""
        retention_days = 30
        date_limit = fields.Datetime.now() - datetime.timedelta(days=retention_days)
        logs_to_delete = self.search([('create_date', '<', date_limit)])
        logs_to_delete.unlink()
        return True
