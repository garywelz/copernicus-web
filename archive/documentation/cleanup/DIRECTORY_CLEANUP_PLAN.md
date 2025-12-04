# Directory Cleanup Plan

## 📋 **Analysis**

Based on directory scan, here's what needs cleanup:

### **Files to Archive** (Move to `archive/one_off_scripts/`)

**Python Scripts:**
- `run_fix_all_issues.py` - One-time fix script
- `find_missing_3_podcasts.py` - Diagnostic script
- `find_youtube_missing_podcasts.py` - Diagnostic script  
- `fix_rss_missing_podcasts.py` - Fix script
- `check_missing_audio_files.py` - Diagnostic script
- `fix_missing_audio_urls.py` - Fix script
- `check_regeneration_data.py` - Diagnostic script
- `diagnose_youtube_audio.py` - Diagnostic script
- `find_all_podcasts_complete.py` - Diagnostic script
- `check_gwelz_podcast_count.py` - Diagnostic script
- `fix_gwelz_podcast_count.py` - Fix script
- `check_database_status.py` - Diagnostic script
- `find_all_missing_podcasts.py` - Diagnostic script

### **Documentation to Archive** (Move to `archive/documentation/`)

**Bug Fix Documentation:**
- `BUG_FIX_PRIORITIES.md`
- `BUG_FIX_PROGRESS.md`
- `SCRIPT_RESULTS_SUMMARY.md`
- `FINDINGS_AND_NEXT_STEPS.md`
- `FINAL_BUG_FIX_SUMMARY.md`
- `COMPLETE_BUG_FIX_STATUS.md`
- `ALL_4_TASKS_COMPLETE.md`
- `SUBSCRIBER_COUNT_FIX.md`
- `SUBSCRIBER_DASHBOARD_COUNT_FIX.md`
- `FIX_SUMMARY_GWELZ_COUNT.md`

**Refactoring Documentation:**
- `REFACTORING_PLAN.md`
- `REFACTORING_IMPLEMENTATION_PLAN.md`
- `REFACTORING_EXECUTION_SUMMARY.md`
- `REFACTORING_PROGRESS.md`
- `REFACTORING_RISK_ASSESSMENT.md`
- `REFACTORING_DECISION_SUMMARY.md`

**Cleanup Documentation:**
- `CLEANUP_COMPLETE.md` (old)
- `CLEANUP_PLAN.md` (old)
- `CLEANUP_PLAN_NOW.md` (temporary)
- `DIRECTORY_CLEANUP_PLAN.md` (this file - archive after cleanup)

### **Keep in Root** (Active Files)

- `README.md` - Main readme
- `CODE_REVIEW_REPORT.md` - Important reference document
- `NEW_PODCAST_TOPIC_SUGGESTIONS.md` - Active topic suggestions
- `PODCAST_TOPIC_SUGGESTIONS.md` - Can remove if NEW is better
- `QUICK_COPY_NEW_PROMPTS.txt` - Active prompts file
- `QUICK_COPY_PROMPTS.txt` - Can remove if NEW is used

## 🎯 **Cleanup Steps**

1. Create archive subdirectories if needed
2. Move all diagnostic/fix scripts to `archive/one_off_scripts/`
3. Move all bug fix docs to `archive/documentation/bug-fixes/`
4. Move refactoring docs to `archive/documentation/refactoring/`
5. Remove duplicate/old files
6. Keep only active/important files in root

