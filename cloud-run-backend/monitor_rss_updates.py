"""
Monitor RSS feed and database for episode removals
Check if ever-phys-250038 and ever-phys-250042 have been removed
"""

import asyncio
import time
from google.cloud import firestore
from google.cloud import storage
from xml.etree import ElementTree as ET
from html import unescape
from config.constants import RSS_BUCKET_NAME, RSS_FEED_BLOB_NAME

EPISODES_TO_REMOVE = [
    'ever-phys-250038',  # Quantum Error Correction: Paving the Way...
    'ever-phys-250042'   # Quantum Sensing Revolution: Unveiling Hidden Realities...
]

def check_rss_feed():
    """Check current state of RSS feed"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(RSS_BUCKET_NAME)
    blob = bucket.blob(RSS_FEED_BLOB_NAME)
    
    if not blob.exists():
        return None, "RSS feed not found"
    
    xml_bytes = blob.download_as_bytes()
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    
    if channel is None:
        return None, "RSS feed missing channel"
    
    items = channel.findall("item")
    
    # Extract GUIDs
    rss_guids = set()
    for item in items:
        guid_elem = item.find("guid")
        if guid_elem is not None and guid_elem.text:
            rss_guids.add(guid_elem.text)
    
    return rss_guids, None

def check_database():
    """Check current state in database"""
    db = firestore.Client(database='copernicusai')
    
    episode_status = {}
    for guid in EPISODES_TO_REMOVE:
        doc = db.collection('episodes').document(guid).get()
        if doc.exists:
            data = doc.to_dict() or {}
            episode_status[guid] = {
                'exists': True,
                'submitted_to_rss': data.get('submitted_to_rss', False),
                'title': data.get('title', 'N/A')
            }
        else:
            episode_status[guid] = {
                'exists': False,
                'submitted_to_rss': False,
                'title': 'N/A'
            }
    
    return episode_status

def monitor_changes():
    """Monitor RSS feed and database for changes"""
    print("=" * 80)
    print("🔍 MONITORING RSS FEED UPDATES")
    print("=" * 80)
    print()
    print(f"Monitoring removal of these episodes:")
    for guid in EPISODES_TO_REMOVE:
        print(f"  - {guid}")
    print()
    print("Checking RSS feed and database...")
    print()
    
    # Check RSS feed
    rss_guids, error = check_rss_feed()
    if error:
        print(f"❌ Error checking RSS feed: {error}")
        return
    
    total_episodes = len(rss_guids)
    
    # Check database
    db_status = check_database()
    
    # Check status for each episode
    print("=" * 80)
    print("📊 CURRENT STATUS")
    print("=" * 80)
    print()
    
    all_removed = True
    for guid in EPISODES_TO_REMOVE:
        in_rss = guid in rss_guids
        db_info = db_status.get(guid, {})
        
        status = "❌ STILL IN RSS" if in_rss else "✅ REMOVED FROM RSS"
        all_removed = all_removed and not in_rss
        
        print(f"{guid}:")
        print(f"  Status: {status}")
        print(f"  Title: {db_info.get('title', 'N/A')}")
        print(f"  In RSS Feed: {in_rss}")
        print(f"  Database submitted_to_rss: {db_info.get('submitted_to_rss', False)}")
        print()
    
    print("=" * 80)
    print("📈 RSS FEED SUMMARY")
    print("=" * 80)
    print()
    print(f"Total episodes in RSS feed: {total_episodes}")
    print(f"Expected after removal: 72")
    print(f"Target episodes in RSS: {len(rss_guids - set(EPISODES_TO_REMOVE))}")
    print()
    
    if all_removed:
        print("✅ SUCCESS: Both episodes have been removed from RSS feed")
        print(f"✅ RSS feed now has {total_episodes} episodes (target: 72)")
        if total_episodes == 72:
            print("✅ Count matches expected target!")
        else:
            print(f"⚠️  Count is {total_episodes} but expected 72 (difference: {total_episodes - 72})")
    else:
        print("⏳ PENDING: Some episodes still in RSS feed")
        print("   Waiting for updates to propagate...")
    
    print()
    
    # Show full list of episodes in RSS for verification
    print("=" * 80)
    print("📋 ALL EPISODES IN RSS FEED (for verification)")
    print("=" * 80)
    print()
    
    # Get titles for display
    storage_client = storage.Client()
    bucket = storage_client.bucket(RSS_BUCKET_NAME)
    blob = bucket.blob(RSS_FEED_BLOB_NAME)
    xml_bytes = blob.download_as_bytes()
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    items = channel.findall("item") if channel is not None else []
    
    episodes_list = []
    for item in items:
        guid_elem = item.find("guid")
        title_elem = item.find("title")
        if guid_elem is not None and guid_elem.text:
            guid = guid_elem.text
            title = unescape(title_elem.text) if title_elem is not None else "Untitled"
            episodes_list.append((guid, title))
    
    # Sort by GUID
    episodes_list.sort(key=lambda x: x[0])
    
    for i, (guid, title) in enumerate(episodes_list, 1):
        marker = "⚠️ " if guid in EPISODES_TO_REMOVE else "  "
        print(f"{marker}{i:3d}. {guid:30s} | {title[:50]}")
    
    print()
    
    return {
        'total_episodes': total_episodes,
        'episodes_removed': all_removed,
        'rss_guids': rss_guids
    }

if __name__ == "__main__":
    result = monitor_changes()
    
    if result and not result['episodes_removed']:
        print("=" * 80)
        print("💡 NOTE")
        print("=" * 80)
        print()
        print("If episodes are still showing in RSS feed:")
        print("  - Changes may take a few minutes to propagate")
        print("  - The 'Remove RSS' action updates the database")
        print("  - RSS feed update happens asynchronously")
        print("  - Check again in a few minutes")
        print()


