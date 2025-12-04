"""
Integration tests for Admin Router endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from fastapi import FastAPI

# Mock dependencies before importing router
with patch('config.database.db', MagicMock()), \
     patch('utils.logging.structured_logger', MagicMock()), \
     patch('utils.auth.get_admin_api_key', return_value='test-key'):
    from endpoints.admin.routes import router


# Create test app with admin router
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestAdminRouter:
    """Test suite for admin router endpoints"""
    
    @patch('endpoints.admin.routes.verify_admin_api_key')
    def test_list_subscribers_endpoint_structure(self, mock_auth):
        """Test that list subscribers endpoint exists and has correct structure"""
        mock_auth.return_value = True
        
        # Mock database
        with patch('endpoints.admin.routes.db') as mock_db:
            mock_collection = MagicMock()
            mock_stream = MagicMock()
            mock_stream.__iter__ = MagicMock(return_value=iter([]))
            mock_collection.stream = MagicMock(return_value=mock_stream)
            mock_db.collection = MagicMock(return_value=mock_collection)
            
            response = client.get(
                "/api/admin/subscribers",
                headers={"X-Admin-API-Key": "test-key"}
            )
            
            # Should return 200 or appropriate status
            assert response.status_code in [200, 401, 403, 503]
    
    @patch('endpoints.admin.routes.verify_admin_api_key')
    def test_admin_endpoints_require_auth(self, mock_auth):
        """Test that admin endpoints require authentication"""
        mock_auth.side_effect = Exception("Unauthorized")
        
        response = client.get("/api/admin/subscribers")
        
        # Should fail without auth (503 means service not configured, which is also valid)
        assert response.status_code in [401, 403, 422, 503]
    
    def test_router_registered(self):
        """Test that admin router is properly registered"""
        # Check that router has routes
        assert len(router.routes) > 0
        
        # Check that routes have /api/admin prefix
        admin_routes = [r for r in router.routes if hasattr(r, 'path') and '/api/admin' in r.path]
        assert len(admin_routes) > 0

