import logging
import uuid
import contextvars

# Context variable for tracing correlation across the asynchronous boundary
correlation_id_var = contextvars.ContextVar('correlation_id', default=None)

class StructuredLogger:
    def __init__(self, logger_name):
        self._logger = logging.getLogger(logger_name)

    def log(self, level, message, *args, **kwargs):
        """
        Log with correlation ID injection. If no correlation ID exists 
        in the context, it generates a new one.
        """
        corr_id = correlation_id_var.get()
        if not corr_id:
            corr_id = str(uuid.uuid4())
            correlation_id_var.set(corr_id)

        # Base struct for JSON or extended formatting in Odoo logs
        extra = {
            'correlation_id': corr_id,
            'integration_id': kwargs.pop('integration_id', None),
            'entity_type': kwargs.pop('entity_type', None),
            'entity_id': kwargs.pop('entity_id', None),
        }
        
        # Odoo's default logger merges `extra` into LogRecord. Add remaining kwargs if any.
        existing_extra = kwargs.pop('extra', {})
        existing_extra.update(extra)
        
        # Inject our structured data into standard logging extra
        kwargs['extra'] = existing_extra

        self._logger.log(level, message, *args, **kwargs)

    def info(self, message, *args, **kwargs):
        self.log(logging.INFO, message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        self.log(logging.WARNING, message, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        self.log(logging.ERROR, message, *args, **kwargs)

    def debug(self, message, *args, **kwargs):
        self.log(logging.DEBUG, message, *args, **kwargs)
