# Voice Assignment Fix - November 27, 2025

## 🐛 Bug Description
When users selected **Brian** (host) and **Bella** (expert) voices:
- **Brian's lines were spoken in Matilda's voice** (default host voice)
- **Bella's lines were spoken in Adam's voice** (default expert voice)

The selected voice IDs were not being correctly applied to the audio segments.

## 🔍 Root Cause
The script parser in `elevenlabs_voice_service.py` was using a hardcoded name-to-role mapping that:
1. Didn't consider which voice IDs were actually selected
2. Had "brian" mapped to "expert" role by default (or missing entirely)
3. Had "bella" mapped to "host" role by default
4. Was rebuilding the mapping inside the parsing loop (inefficient)

This meant that even though custom voice IDs were set for host and expert, the parser was mapping speaker names from the script to roles based on hardcoded defaults, not the selected voices.

## ✅ Fix Applied

### 1. Dynamic Name-to-Role Mapping
Modified `_parse_script_segments()` to:
- Build the name-to-role mapping **once** at the start of the function
- **Prioritize** selected voice IDs when mapping names to roles
- Map speaker names based on which voice was actually selected for each role

### 2. Voice ID to Name Mapping
Added logic to determine speaker names from voice IDs:
- If Bryan's voice ID (`pqHfZKP75CvOlQylNhV4`) is selected for host, then "bryan" maps to "host"
- If Bella's voice ID (`EXAVITQu4vr4xnSDxMaL`) is selected for expert, then "bella" maps to "expert"

### 3. Name Variant Support
Added support for name variants:
- "brian" is now automatically mapped as a variant of "bryan"
- If "bryan" is mapped to "host" (because Bryan's voice was selected for host), then "brian" also maps to "host"

### Key Changes in `cloud-run-backend/elevenlabs_voice_service.py`:

1. **Modified `generate_multi_voice_audio_with_bumpers()`** (lines ~1061-1089):
   - Determines speaker names from voice IDs
   - Passes voice IDs and names to the parser
   - Updates voice configs with selected voice IDs and names

2. **Modified `_parse_script_segments()`** (lines ~265-350):
   - Builds dynamic name-to-role mapping based on selected voices
   - Prioritizes selected voice mappings over defaults
   - Maps "brian" as variant of "bryan"
   - Uses the mapping throughout script parsing

## 🧪 Testing
**After deployment completes**, test with:

1. Generate a new podcast
2. Select **Bryan** (or variant **Brian**) for Host and **Bella** for Expert
3. Expected results:
   - ✅ Script says "BRIAN:" or "BRYAN:" and "BELLA:"
   - ✅ **Brian's voice matches Bryan's voice** (pqHfZKP75CvOlQylNhV4)
   - ✅ **Bella's voice matches Bella's voice** (EXAVITQu4vr4xnSDxMaL)
   - ✅ Two distinct voices in the audio that match the selected voices

## 📋 Files Changed

- `cloud-run-backend/elevenlabs_voice_service.py`
  - Modified `generate_multi_voice_audio_with_bumpers()` to pass voice IDs and names to parser
  - Completely refactored `_parse_script_segments()` to use dynamic mapping

## 📦 Deployment
- **Deployed:** November 27, 2025
- **Service:** `copernicus-podcast-api`
- **Revision:** `copernicus-podcast-api-00131-p7w`

## 🎯 Impact
This fix ensures that:
- Selected voice IDs are correctly applied to audio segments
- Speaker names in scripts are correctly mapped to their assigned roles
- Name variants (like "brian" → "bryan") are handled automatically
- The system works with any combination of voice selections

