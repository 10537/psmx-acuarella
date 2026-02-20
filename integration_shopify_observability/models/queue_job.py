# -*- coding: utf-8 -*-

from odoo import models, api
from ..tools.logging_helper import correlation_id_var
import uuid

class QueueJob(models.Model):
    _inherit = 'queue.job'

    @api.model_create_multi
    def create(self, vals_list):
        """
        When a queue job is created, ensure it captures the current correlation_id 
        in its serialized context.
        """
        corr_id = correlation_id_var.get()
        # If no correlation_id is present but we are launching a job, we might want to group it 
        # but let's just make sure if we have one, it's propagated.
        if corr_id:
            self = self.with_context(correlation_id=corr_id)
        
        return super(QueueJob, self).create(vals_list)

    @api.model
    def perform(self, *args, **kwargs):
        """
        When the queue job is executed by the worker, retrieve the correlation_id
        from the context and restore it in the contextvars for structured logging.
        """
        corr_id = self.env.context.get('correlation_id')
        if corr_id:
            correlation_id_var.set(corr_id)
            
        return super(QueueJob, self).perform(*args, **kwargs)
