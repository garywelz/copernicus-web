"""Subscriber-related data models"""

from pydantic import BaseModel
from typing import Optional, List, Dict


class SubscriberRegistration(BaseModel):
    email: str
    name: str
    password: Optional[str] = None  # For email/password auth
    google_id: Optional[str] = None  # For Google OAuth
    subscription_tier: str = "free"  # free, premium, research
    
    # RSS Attribution fields (Phase 2.1)
    display_name: Optional[str] = None  # Public screen name (e.g., "QuantumPhysicist")
    initials: Optional[str] = None      # Abbreviation for attribution (e.g., "GW")
    show_attribution: bool = False      # Opt-in to show attribution on published podcasts


class SubscriberLogin(BaseModel):
    email: str
    password: Optional[str] = None
    google_id: Optional[str] = None


class PasswordResetRequest(BaseModel):
    email: str


class PasswordReset(BaseModel):
    email: str
    new_password: str


class SubscriberProfile(BaseModel):
    subscriber_id: str
    email: str
    name: str
    subscription_tier: str
    subscription_status: str = "active"
    created_at: str
    last_login: str
    podcasts_generated: int = 0
    podcasts_submitted_to_rss: int = 0
    
    # RSS Attribution fields
    display_name: Optional[str] = None
    initials: Optional[str] = None
    show_attribution: bool = False


class SubscriberProfileUpdate(BaseModel):
    name: Optional[str] = None
    subscription_tier: Optional[str] = None
    display_name: Optional[str] = None
    initials: Optional[str] = None
    show_attribution: Optional[bool] = None


class PodcastSubmission(BaseModel):
    podcast_id: str
    submit_to_rss: bool


class AssignPodcastsRequest(BaseModel):
    podcast_ids: Optional[List[str]] = None
    assign_all_legacy: bool = False

