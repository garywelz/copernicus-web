"""Structured logging utility for Copernicus Podcast API"""

import logging
import re
import sys
import json
from datetime import datetime

_EMAIL_SHAPED = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+")
ADDRESS_PLACEHOLDER = "[address removed]"


def redact_addresses(value):
    """Replace email-shaped text in a log value (strings, and strings nested in lists and dicts). A backstop: call sites
    should pass subscriber ids, not addresses, and error types, not error text."""
    if isinstance(value, str):
        return _EMAIL_SHAPED.sub(ADDRESS_PLACEHOLDER, value)
    if isinstance(value, dict):
        return {redact_addresses(k): redact_addresses(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_addresses(v) for v in value]
    return value


class StructuredLogger:
    """Structured logger that outputs JSON-formatted log entries"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Ensure we have a handler
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log(self, level: str, message: str, **kwargs):
        """Log structured message with additional context"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.upper(),
            "message": message,
            **kwargs
        }
        self.logger.info(json.dumps(redact_addresses(log_entry)))
    
    def info(self, message: str, **kwargs):
        self.log("info", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self.log("error", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self.log("warning", message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self.log("debug", message, **kwargs)


# Global structured logger instance
structured_logger = StructuredLogger("copernicus-podcast")


