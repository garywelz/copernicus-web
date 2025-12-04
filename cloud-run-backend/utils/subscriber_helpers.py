"""Subscriber helper functions for authentication and database operations"""

import hashlib
from typing import Optional
from config.database import db
from utils.logging import structured_logger


def generate_subscriber_id(email: str) -> str:
    """Generate a unique subscriber ID from email"""
    # Use full SHA256 hash to avoid collisions
    return hashlib.sha256(email.encode()).hexdigest()


def get_subscriber_by_email(email: str):
    """Get subscriber by email, trying both old and new ID formats"""
    if not db:
        return None
    
    # Try new format first (full hash)
    new_id = generate_subscriber_id(email)
    subscriber_doc = db.collection('subscribers').document(new_id).get()
    if subscriber_doc.exists:
        return subscriber_doc
    
    # Try old format (16 chars) for backward compatibility
    old_id = hashlib.sha256(email.encode()).hexdigest()[:16]
    subscriber_doc = db.collection('subscribers').document(old_id).get()
    if subscriber_doc.exists:
        return subscriber_doc
    
    return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password (simple implementation - in production use proper hashing)"""
    # Hash the plain password and compare with stored hash
    return hash_password(plain_password) == hashed_password


def hash_password(password: str) -> str:
    """Hash password (simple implementation - in production use proper hashing)"""
    # For now, simple encoding - in production use bcrypt or similar
    return password.encode().hex()

