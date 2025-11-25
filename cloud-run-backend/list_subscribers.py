#!/usr/bin/env python3
"""
List all CopernicusAI subscribers from Firestore.
"""

from google.cloud import firestore
from datetime import datetime
import json

def list_all_subscribers():
    """Query Firestore and display all subscribers."""
    
    # Initialize Firestore client with the copernicusai database
    db = firestore.Client(database='copernicusai')
    
    # Query the subscribers collection
    subscribers_ref = db.collection('subscribers')
    subscribers = subscribers_ref.stream()
    
    print("=" * 100)
    print("COPERNICUS AI - SUBSCRIBER ACCOUNTS")
    print("=" * 100)
    print()
    
    count = 0
    subscriber_list = []
    
    for sub in subscribers:
        count += 1
        data = sub.to_dict()
        
        # Extract key fields
        email = sub.id  # Document ID is the email
        display_name = data.get('display_name', 'N/A')
        initials = data.get('initials', 'N/A')
        show_attribution = data.get('show_attribution', False)
        created_at = data.get('created_at', 'Unknown')
        last_login = data.get('last_login', 'Never')
        podcast_count = data.get('podcast_count', 0)
        
        # Format timestamps if they're Firestore timestamps
        if hasattr(created_at, 'timestamp'):
            created_at = datetime.fromtimestamp(created_at.timestamp()).strftime('%Y-%m-%d %H:%M:%S')
        if hasattr(last_login, 'timestamp'):
            last_login = datetime.fromtimestamp(last_login.timestamp()).strftime('%Y-%m-%d %H:%M:%S')
        
        subscriber_info = {
            'email': email,
            'display_name': display_name,
            'initials': initials,
            'show_attribution': show_attribution,
            'created_at': str(created_at),
            'last_login': str(last_login),
            'podcast_count': podcast_count
        }
        
        subscriber_list.append(subscriber_info)
        
        print(f"#{count}")
        print(f"  Email:           {email}")
        print(f"  Display Name:    {display_name}")
        print(f"  Initials:        {initials}")
        print(f"  Show Attribution: {show_attribution}")
        print(f"  Created:         {created_at}")
        print(f"  Last Login:      {last_login}")
        print(f"  Podcasts:        {podcast_count}")
        print("-" * 100)
    
    print()
    print("=" * 100)
    print(f"TOTAL SUBSCRIBERS: {count}")
    print("=" * 100)
    
    # Optionally save to JSON file
    with open('/tmp/copernicus_subscribers.json', 'w') as f:
        json.dump(subscriber_list, f, indent=2)
    print(f"\n✓ Subscriber data saved to: /tmp/copernicus_subscribers.json")

if __name__ == "__main__":
    try:
        list_all_subscribers()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure you have the correct Google Cloud credentials set up.")
        print("Run: gcloud auth application-default login")

