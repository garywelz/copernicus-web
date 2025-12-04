#!/bin/bash
# Quick script to check failed podcasts

API_URL="https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app"
ENDPOINT="/api/admin/podcasts/failed"

echo "🔍 Checking failed podcast jobs..."
echo "=================================="
echo ""

if [ -z "$ADMIN_API_KEY" ]; then
    echo "Please provide your admin API key:"
    echo "  export ADMIN_API_KEY=your_key_here"
    echo "  or run: ADMIN_API_KEY=your_key bash check_failed_podcast.sh"
    exit 1
fi

# Query the endpoint
RESPONSE=$(curl -s -X GET \
  "${API_URL}${ENDPOINT}" \
  -H "X-Admin-API-Key: ${ADMIN_API_KEY}" \
  -H "Content-Type: application/json")

# Check if we got a response
if [ $? -ne 0 ]; then
    echo "❌ Failed to connect to API"
    exit 1
fi

# Check for errors in response
ERROR=$(echo "$RESPONSE" | grep -o '"detail":"[^"]*"' | head -1)
if [ ! -z "$ERROR" ]; then
    echo "❌ API Error: $ERROR"
    echo ""
    echo "Full response:"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    exit 1
fi

# Parse and display results
echo "$RESPONSE" | python3 << 'PYTHON_SCRIPT'
import sys
import json

try:
    data = json.load(sys.stdin)
    failed_jobs = data.get('failed_jobs', [])
    total = data.get('total_count', 0)
    
    print(f"📊 Found {total} failed podcast job(s):\n")
    
    if total == 0:
        print("✅ No failed jobs found!")
        sys.exit(0)
    
    # Search for Metalloenzyme
    metalloenzyme_found = False
    for i, job in enumerate(failed_jobs, 1):
        topic = job.get('topic', '')
        title = job.get('title', '')
        
        if 'metalloenzyme' in topic.lower() or 'metalloenzyme' in str(title).lower():
            metalloenzyme_found = True
            print("=" * 70)
            print(f"🎯 FOUND THE METALLOENZYMES PODCAST!")
            print("=" * 70)
            print(f"Job ID:       {job.get('job_id')}")
            print(f"Topic:        {job.get('topic')}")
            print(f"Title:        {job.get('title')}")
            print(f"Category:     {job.get('category')}")
            print(f"Status:       {job.get('status')}")
            print(f"Created:      {job.get('created_at')}")
            print(f"Updated:      {job.get('updated_at')}")
            
            error = job.get('error', 'No error message')
            error_type = job.get('error_type', '')
            
            print(f"\n❌ ERROR:")
            if error_type:
                print(f"   Type: {error_type}")
            print(f"   Message: {error}")
            print()
    
    if not metalloenzyme_found:
        print("⚠️  Metalloenzymes podcast not found in failed jobs list.")
        print("\nShowing all failed jobs:\n")
    
    # Show all failed jobs
    for i, job in enumerate(failed_jobs, 1):
        if metalloenzyme_found and ('metalloenzyme' in job.get('topic', '').lower() or 'metalloenzyme' in str(job.get('title', '')).lower()):
            continue  # Already shown
        
        print(f"{'='*70}")
        print(f"Failed Job #{i}")
        print(f"{'='*70}")
        print(f"Job ID:       {job.get('job_id')}")
        print(f"Topic:        {job.get('topic')}")
        print(f"Category:     {job.get('category')}")
        print(f"Created:      {job.get('created_at')}")
        error = job.get('error', 'No error message')
        print(f"Error:        {error[:100]}{'...' if len(error) > 100 else ''}")
        print()

except json.JSONDecodeError as e:
    print("❌ Failed to parse JSON response")
    print("Response:", sys.stdin.read())
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
PYTHON_SCRIPT

