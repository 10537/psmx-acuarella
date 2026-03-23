# -*- coding: utf-8 -*-

from odoo import models, api
from ..tools.logging_helper import correlation_id_var
from odoo.addons.queue_job.job import Job
import uuid

# Monkey-patch OCA queue_job execution
_original_perform = Job.perform

def _patched_perform(self):
    """
    When the queue job is executed by the worker, retrieve the correlation_id
    from the context and restore it in the contextvars for structured logging.
    """
    corr_id = self.env.context.get('correlation_id')
    if corr_id:
        correlation_id_var.set(corr_id)
    else:
        # If no correlation_id is found, generate one for the worker
        correlation_id_var.set(str(uuid.uuid4()))
        
    try:
        return _original_perform(self)
    finally:
        # Reset correlation ID when job is done
        correlation_id_var.set(None)

Job.perform = _patched_perform

class QueueJob(models.Model):
    _inherit = 'queue.job'

