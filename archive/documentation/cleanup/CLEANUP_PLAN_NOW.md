# Directory Cleanup Plan

## 📋 **Files to Archive**

### **Diagnostic Scripts** (Move to `archive/one_off_scripts/`)
- `find_missing_3_podcasts.py`
- `find_youtube_missing_podcasts.py`
- `check_missing_audio_files.py`
- `check_regeneration_data.py`
- `diagnose_youtube_audio.py`
- `find_all_podcasts_complete.py`
- `check_gwelz_podcast_count.py`
- `check_database_status.py`
- `find_all_missing_podcasts.py`

### **Fix Scripts** (Move to `archive/one_off_scripts/`)
- `fix_rss_missing_podcasts.py`
- `fix_missing_audio_urls.py`
- `fix_gwelz_podcast_count.py`
- `run_fix_all_issues.py`

### **Documentation Files to Consolidate** (Move to `archive/documentation/`)
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
- `REFACTORING_PLAN.md`
- `REFACTORING_IMPLEMENTATION_PLAN.md`
- `REFACTORING_EXECUTION_SUMMARY.md`
- `REFACTORING_PROGRESS.md`
- `REFACTORING_RISK_ASSESSMENT.md`
- `REFACTORING_DECISION_SUMMARY.md`

### **Keep in Root** (Active/Important)
- `README.md` - Main readme
- `CODE_REVIEW_REPORT.md` - Important reference
- `NEW_PODCAST_TOPIC_SUGGESTIONS.md` - Active topic suggestions
- `PODCAST_TOPIC_SUGGESTIONS.md` - Active topic suggestions (can remove if NEW is better)
- `QUICK_COPY_NEW_PROMPTS.txt` - Active prompts file
- `QUICK_COPY_PROMPTS.txt` - Can remove if NEW is used

### **Questionable** (Review first)
- `CLEANUP_COMPLETE.md` - Might be old
- `CLEANUP_PLAN.md` - Might be old

## 🎯 **Action Plan**

1. Create subdirectories in archive if needed
2. Move diagnostic scripts to archive
3. Move fix scripts to archive
4. Move old documentation to archive
5. Remove duplicate/unused files
6. Update archive README

