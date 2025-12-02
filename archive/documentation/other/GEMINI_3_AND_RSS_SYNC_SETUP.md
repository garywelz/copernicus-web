# Gemini 3.0 Upgrade & Daily RSS Sync Setup

## 1. ✅ Gemini 3.0 Integration

**Status:** Code updated to use Gemini 3.0 with automatic fallback

### Changes Made:
- Updated all Gemini model calls to try `models/gemini-3.0-flash` first
- Automatic fallback to `models/gemini-2.5-flash` if 3.0 is not available
- Updated in 4 locations:
  - `generate_podcast_from_analysis()` - Research-driven podcast generation
  - `generate_topic_research_content()` - Topic-based content generation  
  - `generate_podcast_from_analysis_vertex()` - Vertex AI version
  - `generate_content_from_research_context()` - Research context generation

### Testing:
To verify Gemini 3.0 availability, run:
```bash
cd cloud-run-backend
python3 test_gemini_3.py
```

This will test which models are available and report back.

### Next Steps:
1. **Deploy the updated code** to Cloud Run
2. **Monitor logs** during podcast generation to see which model is being used
3. **Compare quality** between Gemini 3.0 and 2.5 to validate the upgrade

---

## 2. ✅ Daily RSS Sync Setup

**Status:** Cloud Scheduler setup script created

### Files Created:
- `cloud-run-backend/setup_daily_rss_sync.sh` - Setup script for Cloud Scheduler
- `cloud-run-backend/sync_rss_status.py` - Standalone sync script (already exists)

### To Set Up Daily RSS Sync:

1. **Make the script executable:**
   ```bash
   chmod +x cloud-run-backend/setup_daily_rss_sync.sh
   ```

2. **Run the setup script:**
   ```bash
   cd cloud-run-backend
   ./setup_daily_rss_sync.sh
   ```

   This will:
   - Enable Cloud Scheduler API
   - Create a daily job at 2 AM UTC
   - Call `/api/admin/episodes/sync-rss-status` endpoint
   - Use OIDC authentication

3. **Test the job manually:**
   ```bash
   gcloud scheduler jobs run daily-rss-sync \
     --location=us-central1 \
     --project=regal-scholar-453620-r7
   ```

4. **View job details:**
   ```bash
   gcloud scheduler jobs describe daily-rss-sync \
     --location=us-central1 \
     --project=regal-scholar-453620-r7
   ```

### Schedule Details:
- **Frequency:** Daily
- **Time:** 2 AM UTC (adjustable in the script)
- **Timezone:** UTC (adjustable)
- **Endpoint:** `/api/admin/episodes/sync-rss-status`

### To Change Schedule:
Edit `setup_daily_rss_sync.sh` and modify:
- `SCHEDULE="0 2 * * *"` - Cron format (minute hour day month weekday)
- `TIMEZONE="UTC"` - Your preferred timezone

---

## 3. 🔍 Website Episode Count Investigation

**Issue:** Website showing only 32 podcasts instead of all available episodes

### Potential Causes:

1. **Firestore Query Limit:**
   - The API endpoint has `limit: int = 500` with max of 1000
   - Website requests `limit=500`
   - But there might be a Firestore index issue limiting results

2. **Filter Applied:**
   - Check if a default filter is applied (e.g., `submitted_to_rss=true`)
   - The website might be filtering to show only published episodes

3. **Pagination:**
   - The Next.js API route (`app/api/podcasts/catalog/route.ts`) has pagination
   - Default limit is 20 per page
   - Total episodes shown = page * limit

4. **Different Endpoint:**
   - The homepage might be using `/api/podcasts/catalog` instead of `/api/episodes`
   - This endpoint queries `podcast_jobs` collection, not `episodes` collection

### Investigation Steps:

1. **Check which endpoint the homepage uses:**
   - Look at `public/index.html` or homepage component
   - Verify which API endpoint it calls

2. **Check Firestore query:**
   ```bash
   # Query Firestore directly to see how many episodes exist
   # This requires GCP access
   ```

3. **Check API response:**
   - Visit `https://copernicus-podcast-api-204731194849.us-central1.run.app/api/episodes?limit=500`
   - Check the `total_count` in the response
   - Verify it matches what's in Firestore

4. **Check logs:**
   - Review Cloud Run logs for the `/api/episodes` endpoint
   - Look for any query errors or warnings

### Quick Fix to Try:

If the issue is pagination on the Next.js API route, the default limit is 20. 
32 episodes = 1.6 pages, so it might be showing page 1 (20) + some from page 2 (12).

To fix, increase the default limit in `app/api/podcasts/catalog/route.ts`:
```typescript
const limit = parseInt(searchParams.get('limit') || '100')  // Changed from 20 to 100
```

---

## Summary

1. ✅ **Gemini 3.0:** Code updated, will try 3.0 first with fallback to 2.5
2. ✅ **Daily RSS Sync:** Script ready to deploy Cloud Scheduler job
3. 🔍 **Episode Count:** Needs investigation - likely pagination or filter issue

### Immediate Actions:
1. Run `test_gemini_3.py` to check Gemini 3.0 availability
2. Deploy updated `main.py` to Cloud Run
3. Run `setup_daily_rss_sync.sh` to set up daily sync
4. Investigate why only 32 episodes are showing (check homepage endpoint)

