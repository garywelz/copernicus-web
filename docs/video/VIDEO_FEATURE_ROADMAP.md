# Video Feature Roadmap - Copernicus AI Podcasts

**Date:** December 2025  
**Status:** Planning Phase - Architecture Prepared for Video Expansion

---

## 🎯 Vision

Expand Copernicus AI podcasts to support **optional video augmentation** while maintaining full support for **audio-only podcasts**. Users can choose the format that best fits their needs.

---

## 📋 Planned Video Features

### 1. **Still Images**
- AI-generated images (DALL-E 3 / Stable Diffusion)
- Scientific diagrams and visualizations
- Charts and graphs from research data
- Static slides for key concepts

### 2. **Computer Animations (Python-Generated)**
- Matplotlib/Plotly animations for data visualization
- Scientific process animations
- Molecular/atomic structure animations
- Network/graph visualizations
- Algorithm visualizations

### 3. **AI Video Insertion**
- AI-generated video clips relevant to content
- Background video loops
- Scientific concept visualization videos
- Research demonstration videos

### 4. **Subtitle Insertion**
- Automatic subtitle generation from transcript
- Multi-language support
- Stylized subtitle overlays
- Keyword highlighting

### 5. **Video Output**
- Final video file generation (MP4)
- YouTube-optimized format
- High-quality encoding
- Multiple resolution options

---

## 🏗️ Architecture Design

### Current Pipeline (Audio-Only)
```
Research → Content Generation → Audio Synthesis → Upload → RSS
```

### Future Pipeline (With Video)
```
Research → Content Generation → Audio Synthesis → [OPTIONAL VIDEO GENERATION] → Upload → RSS
                                            ↓
                    Video Generation Phases:
                    - Still Image Generation
                    - Animation Creation
                    - AI Video Insertion
                    - Subtitle Generation
                    - Video Composition
                    - Final Encoding
```

---

## 📁 Service Structure for Video Support

### Proposed Services

1. **`PodcastGenerationService`** (Current)
   - Handles audio-only generation
   - Can delegate to video service when needed

2. **`VideoGenerationService`** (Future)
   - `generate_still_images()` - AI image generation
   - `generate_animations()` - Python-based animations
   - `insert_ai_videos()` - AI video clip insertion
   - `generate_subtitles()` - Subtitle creation
   - `compose_video()` - Final video composition
   - `encode_video()` - Video encoding/compression

3. **`AnimationService`** (Future)
   - Python-based animation generation
   - Matplotlib/Plotly integration
   - Scientific visualization tools

---

## 🔧 Implementation Strategy

### Phase 1: Architecture Preparation (Current)
- ✅ Modular service structure
- ✅ Extensible orchestrator design
- ✅ Optional phase support

### Phase 2: Video Service Foundation (Future)
- Create `VideoGenerationService` class
- Add video format to `PodcastRequest` model
- Extend episode document to include video URLs

### Phase 3: Still Images (Future)
- Integrate image generation
- Add image timing/synchronization
- Store images in GCS

### Phase 4: Animations (Future)
- Create `AnimationService`
- Integrate Python animation libraries
- Generate animations on-the-fly

### Phase 5: Full Video Pipeline (Future)
- Complete video composition
- Subtitle integration
- Final encoding and upload

---

## 📝 Code Structure Notes

### Current Structure (Supports Video Extension)

```python
class PodcastGenerationService:
    async def run_podcast_generation_job(...):
        # Phase 1: Research
        # Phase 2: Content Generation
        # Phase 3: Audio Synthesis
        # Phase 4: [OPTIONAL] Video Generation  ← EXTENSION POINT
        # Phase 5: Upload & Catalog
```

### Future Extension Point

```python
# In run_podcast_generation_job():
if request.format_type == "video" or request.include_video:
    video_url = await video_service.generate_video_podcast(
        audio_url=audio_url,
        script=content["script"],
        canonical_filename=canonical_filename,
        images=...,  # Still images
        animations=...,  # Python animations
        subtitles=...  # Subtitle tracks
    )
```

---

## 🔄 Backward Compatibility

- **Audio-only remains default** - No breaking changes
- **Video is opt-in** - Users request video format explicitly
- **RSS feeds support both** - Separate feeds or unified feed with media type tags
- **Database supports both** - `audio_url` and `video_url` fields

---

## 📦 Dependencies (Future)

### For Video Generation
- `ffmpeg-python` or `moviepy` - Video editing/composition
- `opencv-python` - Image/video processing
- `Pillow` - Image manipulation
- `matplotlib` - Scientific animations
- `plotly` - Interactive visualizations
- `pydub` - Audio processing

### For Subtitle Generation
- Existing transcript → subtitle conversion
- `pysrt` - Subtitle format handling

---

## 🎬 Video Generation Pipeline (Detailed)

### Step 1: Still Images
```python
async def generate_still_images(
    script: str,
    canonical_filename: str,
    topic: str
) -> List[ImageAsset]:
    """
    Generate still images at key moments in the script
    - Analyze script for visualization opportunities
    - Generate AI images for key concepts
    - Time-stamp images to audio timeline
    """
```

### Step 2: Animations
```python
async def generate_animations(
    script: str,
    research_context: ResearchContext,
    canonical_filename: str
) -> List[AnimationAsset]:
    """
    Generate Python-based animations
    - Identify data visualization needs
    - Create matplotlib/plotly animations
    - Export as video segments
    - Time-stamp to audio timeline
    """
```

### Step 3: AI Video Clips
```python
async def insert_ai_videos(
    script: str,
    topic: str,
    duration: str
) -> List[VideoClip]:
    """
    Generate or source AI video clips
    - Background video loops
    - Concept demonstration videos
    - Research visualization videos
    """
```

### Step 4: Subtitles
```python
async def generate_subtitles(
    script: str,
    audio_url: str,
    canonical_filename: str
) -> SubtitleTrack:
    """
    Generate subtitle track
    - Extract timing from audio
    - Format subtitles (SRT/VTT)
    - Style subtitles
    """
```

### Step 5: Video Composition
```python
async def compose_video(
    audio_url: str,
    images: List[ImageAsset],
    animations: List[AnimationAsset],
    video_clips: List[VideoClip],
    subtitles: SubtitleTrack,
    canonical_filename: str
) -> str:
    """
    Compose final video
    - Layer audio, images, animations, video clips
    - Add subtitles overlay
    - Synchronize all elements
    - Export as MP4
    """
```

---

## 📊 Data Model Extensions (Future)

### PodcastRequest Model
```python
class PodcastRequest(BaseModel):
    # Existing fields...
    
    # New video fields (optional)
    format_type: str = "audio"  # "audio" or "video"
    include_video: bool = False
    video_features: Optional[VideoFeatures] = None

class VideoFeatures(BaseModel):
    include_still_images: bool = True
    include_animations: bool = True
    include_ai_videos: bool = False
    include_subtitles: bool = True
    animation_style: str = "scientific"  # "scientific", "minimal", "dynamic"
```

### Episode Document Extensions
```python
{
    "audio_url": "...",
    "video_url": "...",  # New field
    "video_assets": {
        "images": [...],
        "animations": [...],
        "video_clips": [...],
        "subtitle_url": "..."
    }
}
```

---

## 🎯 Integration Points

### Current Code Locations

1. **`services/podcast_generation_service.py`**
   - Main orchestrator function
   - **Extension point:** After audio generation, before upload

2. **`models/podcast.py`**
   - `PodcastRequest` model
   - **Extension point:** Add video fields

3. **`services/episode_service.py`**
   - Episode document preparation
   - **Extension point:** Add video URL and assets

4. **`services/rss_service.py`**
   - RSS feed generation
   - **Extension point:** Support video enclosure tags

---

## 🔐 Storage Considerations

### Current Structure
```
GCS Bucket:
  - audio/
  - thumbnails/
  - transcripts/
  - descriptions/
```

### Future Structure
```
GCS Bucket:
  - audio/
  - videos/          ← NEW
  - thumbnails/
  - transcripts/
  - descriptions/
  - video-assets/    ← NEW
    - images/
    - animations/
    - video-clips/
    - subtitles/
```

---

## ⚡ Performance Considerations

### Video Generation Time
- Still images: ~30-60 seconds per image
- Animations: ~2-5 minutes per animation
- Video composition: ~5-10 minutes
- **Total:** ~15-30 minutes for full video podcast

### Optimization Strategies
- Generate assets in parallel
- Cache reusable animations
- Use background jobs for video generation
- Offer "quick video" vs "full video" options

---

## 🚀 Migration Path

### Backward Compatibility
1. All existing podcasts remain audio-only
2. Video features opt-in only
3. No changes to existing RSS feeds
4. Database schema extends (backward compatible)

### Rollout Strategy
1. Beta: Video generation for internal testing
2. Limited release: Selected subscribers
3. General availability: All users can opt-in
4. Default option: Offer both formats

---

## 📝 Notes for Implementation

### Key Principles
1. **Audio-first** - Video is enhancement, not replacement
2. **Modular design** - Each video feature is independent
3. **Extensible** - Easy to add new video features
4. **Backward compatible** - Never break existing functionality

### Current Refactoring Impact
- ✅ Service structure already supports extension
- ✅ Orchestrator function will have clear video insertion point
- ✅ Models can be extended without breaking changes
- ✅ Episode service can handle both formats

---

**Status:** Architecture prepared, ready for video feature implementation when needed.

*Last Updated: December 2025*

