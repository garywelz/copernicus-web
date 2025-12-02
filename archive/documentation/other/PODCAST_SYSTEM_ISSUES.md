# Copernicus AI Podcast Generation System - Technical Issues Summary

## System Overview
- **Platform**: Google Cloud Run (FastAPI backend) + Google Cloud Storage (frontend form)
- **Purpose**: AI-generated science podcasts with multi-voice TTS using ElevenLabs
- **Current Status**: Audio combination process hangs after segment generation

## Current Problem: Audio Combination Hanging

### What's Working:
1. ✅ **Content Generation**: AI generates 5-minute podcast scripts correctly
2. ✅ **Multi-voice Script**: Proper speaker assignments (Host, Expert, Questioner)
3. ✅ **ElevenLabs TTS**: All 51 audio segments generated successfully
4. ✅ **Temp File Creation**: System creates temporary files for each segment
5. ✅ **Timeout Protection**: 5-minute timeout implemented

### What's Failing:
1. ❌ **Audio Combination**: Process hangs during pydub audio combination
2. ❌ **No Final Output**: No MP3, transcript, description, or thumbnail files created
3. ❌ **No Email Notifications**: Completion emails not sent
4. ❌ **Process Timeout**: Cloud Run instances timeout after 30 minutes

## Technical Details

### Audio Processing Pipeline:
```
Script Generation → ElevenLabs TTS (51 segments) → pydub Combination → GCS Upload → Email Notification
                                                           ↑
                                                    HANGS HERE
```

### Current Implementation:
- **Language**: Python with FastAPI
- **Audio Library**: pydub with ffmpeg
- **TTS Service**: ElevenLabs API
- **Storage**: Google Cloud Storage
- **Deployment**: Google Cloud Run (30-minute timeout)

### Recent Fixes Attempted:
1. **Timeout Protection**: Added `asyncio.wait_for(300 seconds)` to audio combination
2. **Memory Management**: Implemented temp file approach for large segment counts (>20)
3. **Error Handling**: Added fallback export options for pydub
4. **Data Type Fixes**: Corrected audio data extraction from AudioSegment objects

### Log Evidence:
```
INFO:elevenlabs_voice_service:🔗 Combining 51 audio segments with pydub
INFO:elevenlabs_voice_service:📁 Using temporary file approach for large segment count
INFO:elevenlabs_voice_service:✅ Created temp file for segment 1
INFO:elevenlabs_voice_service:✅ Created temp file for segment 2
... (all 51 segments created successfully)
[Process hangs after this point - no further logs]
```

## Root Cause Analysis

### Suspected Issues:
1. **pydub Memory Leak**: Large audio combination may cause memory issues
2. **ffmpeg Process Hanging**: Underlying ffmpeg process may be stuck
3. **Cloud Run Resource Limits**: Memory/CPU constraints during combination
4. **Async/Sync Mismatch**: pydub operations may not be properly async

### Current Cloud Run Configuration:
- **Memory**: 2GB
- **CPU**: 2 vCPU
- **Timeout**: 30 minutes
- **Max Instances**: 80

## Files to Examine

### Key Files:
1. **`cloud-run-backend/elevenlabs_voice_service.py`** - Audio combination logic
2. **`cloud-run-backend/main.py`** - Main FastAPI application
3. **`cloud-run-backend/requirements.txt`** - Dependencies
4. **`cloud-run-backend/Dockerfile`** - Container configuration

### Critical Function:
```python
async def _combine_audio_segments_with_temp_files(self, audio_segments: List[bytes], output_path: str) -> bytes:
    # This function hangs during pydub combination
```

## Potential Solutions to Investigate

### 1. Alternative Audio Libraries:
- **librosa**: More memory-efficient audio processing
- **soundfile**: Direct audio file manipulation
- **wave**: Python built-in audio processing

### 2. Streaming Approach:
- Process segments in smaller batches
- Stream combination instead of loading all into memory
- Use temporary files more aggressively

### 3. External Processing:
- Move audio combination to Cloud Functions
- Use Google Cloud Video Intelligence API
- Implement serverless audio processing

### 4. pydub Alternatives:
- **audioread**: Lightweight audio reading
- **pydub with different backends**: Try different ffmpeg configurations
- **Custom ffmpeg commands**: Direct subprocess calls

## Test Cases Needed

### 1. Small Segment Test:
- Test with 5-10 segments to isolate the issue
- Verify if problem is segment count related

### 2. Memory Monitoring:
- Add memory usage logging during combination
- Monitor Cloud Run memory consumption

### 3. ffmpeg Direct Test:
- Test ffmpeg commands directly without pydub
- Verify ffmpeg process completion

## Current Deployment Info

### Service Details:
- **Service Name**: `copernicus-podcast-api-v2`
- **Region**: `us-central1`
- **Project**: `regal-scholar-453620-r7`
- **Current Revision**: `copernicus-podcast-api-v2-00010-gtl`

### Recent Job ID:
- **Job ID**: `85b0f041-75be-4e79-9175-f46498ba9d39`
- **Topic**: "Quantum Computing chip advances"
- **Status**: Hung during audio combination

## Next Steps for Resolution

1. **Immediate**: Investigate pydub memory usage and ffmpeg process status
2. **Short-term**: Implement alternative audio combination approach
3. **Long-term**: Consider moving to more robust audio processing solution

## Contact Information
- **System Owner**: User working on Copernicus AI podcast system
- **Last Updated**: January 27, 2025
- **Priority**: High - System is non-functional for production use
