#!/usr/bin/env python3
"""Update gwelz@jjay.cuny.edu account to unlimited subscription tier"""

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

print(f"\n🔧 Updating account to unlimited subscription: {email}\n")

# Get subscriber
subscriber_doc = get_subscriber_by_email(email)
if not subscriber_doc:
    print(f"❌ Subscriber not found: {email}")
    sys.exit(1)

subscriber_id = subscriber_doc.id
subscriber_data = subscriber_doc.to_dict() or {}

print("Current subscription:")
print(f"   Tier: {subscriber_data.get('subscription_tier', 'free')}")
print(f"   Status: {subscriber_data.get('subscription_status', 'unknown')}")
print()

# Update to research tier (unlimited)
updates = {
    'subscription_tier': 'research',
    'subscription_status': 'active',
    'updated_at': firestore.SERVER_TIMESTAMP if hasattr(firestore, 'SERVER_TIMESTAMP') else None
}

# Remove SERVER_TIMESTAMP if not available, use string timestamp instead
import datetime
updates['updated_at'] = datetime.datetime.utcnow().isoformat()

print("Updating to:")
print(f"   Tier: research (unlimited)")
print(f"   Status: active")
print()

# Confirm
response = input("Proceed with update? (yes/no): ").strip().lower()
if response not in ['yes', 'y']:
    print("❌ Update cancelled")
    sys.exit(0)

try:
    db.collection('subscribers').document(subscriber_id).update(updates)
    print("✅ Account updated successfully!")
    print()
    print("Your account now has:")
    print("   ✅ Unlimited podcast generation")
    print("   ✅ Research tier access")
    print("   ✅ Active status")
except Exception as e:
    print(f"❌ Error updating account: {e}")
    sys.exit(1)

