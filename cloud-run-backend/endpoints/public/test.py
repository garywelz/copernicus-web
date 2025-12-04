"""Test endpoint"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/test")
async def test_endpoint():
    """Test endpoint to verify API is working"""
    return {"message": "API is working", "glmp_endpoints": "available"}

