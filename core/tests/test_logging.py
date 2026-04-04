"""
Tests for logging utilities.
"""

import pytest
import logging
from core.logging import ContextLogger, log_request
from django.test import RequestFactory

@pytest.mark.django_db
class TestContextLogger:
    """Tests for ContextLogger."""
    
    def test_context_logger_creation(self):
        """Test creating context logger."""
        logger = ContextLogger('test')
        assert logger.logger.name == 'test'
        assert logger.context == {}
    
    def test_add_context(self):
        """Test adding context."""
        logger = ContextLogger('test')
        logger.add_context(user_id='123', action='test')
        
        assert logger.context['user_id'] == '123'
        assert logger.context['action'] == 'test'
    
    def test_clear_context(self):
        """Test clearing context."""
        logger = ContextLogger('test')
        logger.add_context(user_id='123')
        logger.clear_context()
        
        assert logger.context == {}


class TestLogRequest:
    """Tests for log_request function."""
    
    def test_log_request(self, caplog):
        """Test logging request."""
        factory = RequestFactory()
        request = factory.get('/api/v1/test/')
        
        logger = logging.getLogger('apps.api')
        logger.addHandler(caplog.handler)
        
        try:
            with caplog.at_level(logging.INFO, logger='apps.api'):
                log_request(request)
        finally:
            logger.removeHandler(caplog.handler)
        
        assert 'GET /api/v1/test/' in caplog.text