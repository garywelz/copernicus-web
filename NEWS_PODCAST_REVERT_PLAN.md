# News Podcast Revert Plan - December 1, 2025

## 🚨 Critical Issue

News podcasts with proper canonical filenames (like `news-bio-28032025`) were incorrectly changed to `ever-` format by the assignment script.

## 📋 What Needs to Happen

### 1. Fix the Pattern Matching ✅ (Already Done)

The pattern matching now recognizes BOTH formats:
- `ever-{category}-{6 digits}` for evergreen podcasts
- `news-{category}-{8 digits}` for news podcasts (DDMMYYYY format)

### 2. Revert Incorrectly Changed News Podcasts

We need to:
1. Find news podcasts that were incorrectly changed
2. Determine their original `news-category-DDMMYYYY` filename
3. Revert them back

### 3. Sources for Original Filenames

Original filenames can be found from:
- **RSS Feed**: Check RSS feed for original GUIDs
- **GCS Bucket**: Check audio file names in GCS (e.g., `audio/news-bio-28032025.mp3`)
- **Firestore History**: Check if there's a history/backup
- **Created Date**: Calculate date from `created_at` and format as DDMMYYYY

## 🔧 Solution

### Option 1: Check RSS Feed for Original GUIDs
- Read RSS feed XML
- Look for items with titles containing "News"
- Extract original GUIDs (should be `news-category-DDMMYYYY` format)

### Option 2: Check GCS Bucket for Audio Files
- List all files in GCS bucket with `news-` prefix
- Match audio files to podcasts by title/date
- Extract canonical filename from audio file name

### Option 3: Reconstruct from Created Date
- Use `created_at` timestamp from Firestore
- Format as DDMMYYYY (e.g., March 28, 2025 → 28032025)
- Reconstruct as `news-{category}-{DDMMYYYY}`

## 📝 Next Steps

1. Create endpoint to identify incorrectly changed news podcasts
2. Create endpoint to revert them using one of the methods above
3. Test the revert process
4. Deploy and run the revert

## ⚠️ Important Rules

- **News podcasts**: `news-{category}-{DDMMYYYY}` format (e.g., `news-bio-28032025`)
- **Evergreen podcasts**: `ever-{category}-{6 digits}` format (e.g., `ever-bio-250040`)
- **Only change**: Podcasts using UUID/job_id identifiers
- **Never change**: Podcasts that already have valid canonical filenames (either format)

