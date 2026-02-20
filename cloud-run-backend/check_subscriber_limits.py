#!/usr/bin/env python3
"""Check subscriber's subscription limits and usage"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from google.cloud import firestore
    from utils.subscriber_helpers import get_subscriber_by_email
    db = firestore.Client(project="regal-scholar-453620-r7", database="copernicusai")
    print("✅ Connected to Firestore")
except Exception as e:
    print(f"❌ Error connecting to Firestore: {e}")
    sys.exit(1)

email = "gwelz@jjay.cuny.edu"

print(f"\n🔍 Checking subscription limits and usage for: {email}\n")

# Get subscriber
subscriber_doc = get_subscriber_by_email(email)
if not subscriber_doc:
    print(f"❌ Subscriber not found: {email}")
    sys.exit(1)

subscriber_id = subscriber_doc.id
subscriber_data = subscriber_doc.to_dict() or {}

print("=" * 80)
print("SUBSCRIBER INFORMATION")
print("=" * 80)
print(f"Email: {email}")
print(f"Subscriber ID: {subscriber_id}")
print()

# Check subscription tier
subscription_tier = subscriber_data.get('subscription_tier', 'free')
subscription_status = subscriber_data.get('subscription_status', 'unknown')
podcasts_generated = subscriber_data.get('podcasts_generated', 0)

print(f"Subscription Tier: {subscription_tier}")
print(f"Subscription Status: {subscription_status}")
print(f"Podcasts Generated (stored): {podcasts_generated}")
print()

# Calculate actual count from podcast_jobs
jobs_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).stream()
actual_job_count = sum(1 for _ in jobs_query)

print(f"Actual Jobs in podcast_jobs: {actual_job_count}")
print()

# Determine limits based on tier
if subscription_tier == 'free':
    limit = 10
    remaining = max(0, limit - podcasts_generated)
    print(f"📊 FREE TIER LIMITS:")
    print(f"   Monthly Limit: {limit} podcasts")
    print(f"   Used: {podcasts_generated}")
    print(f"   Remaining: {remaining}")
    if podcasts_generated >= limit:
        print(f"   ⚠️  LIMIT REACHED - Cannot generate more podcasts")
    else:
        print(f"   ✅ Limit not reached - Can still generate podcasts")
elif subscription_tier in ['premium', 'research']:
    print(f"📊 {subscription_tier.upper()} TIER:")
    print(f"   ✅ UNLIMITED podcasts")
    print(f"   Used: {podcasts_generated} (tracked, but no limit)")
else:
    print(f"⚠️  Unknown subscription tier: {subscription_tier}")
    print(f"   Assuming free tier limits (10/month)")

print()
print("=" * 80)
print("RECENT ACTIVITY (Last 24 hours)")
print("=" * 80)

from datetime import datetime, timedelta
twenty_four_hours_ago = (datetime.utcnow() - timedelta(hours=24)).isoformat()

jobs_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).limit(100).stream()

recent_jobs = []
for job in jobs_query:
    job_data = job.to_dict() or {}
    created_at = job_data.get('created_at', '')
    if created_at >= twenty_four_hours_ago:
        request_data = job_data.get('request', {})
        topic = request_data.get('topic', 'Unknown') if isinstance(request_data, dict) else 'Unknown'
        status = job_data.get('status', 'unknown')
        recent_jobs.append({
            'created_at': created_at,
            'topic': topic,
            'status': status
        })

recent_jobs.sort(key=lambda x: x.get('created_at', ''), reverse=True)

print(f"Jobs in last 24 hours: {len(recent_jobs)}")
for i, job in enumerate(recent_jobs[:10], 1):
    status_icon = "✅" if job['status'] == 'completed' else "❌" if job['status'] == 'failed' else "⏳"
    print(f"   {i}. {status_icon} {job['topic'][:60]} ({job['status']})")

