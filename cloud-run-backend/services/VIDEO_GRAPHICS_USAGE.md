# Video Generation with Computational Graphics

## Overview

The enhanced `VideoGenerationService` now supports:
1. **Minimal-size mode**: Creates very small video files (0.1 fps, low bitrate) - similar to MP3 + embedded image
2. **Computational graphics**: Generate images programmatically from code/formulas, not image files

## Minimal-Size Mode

When `minimal_size=True`, videos are encoded with:
- **Frame rate**: 0.1 fps (1 frame per 10 seconds) - extremely small file size
- **Video bitrate**: 50k (very low)
- **Audio bitrate**: 192k (unchanged, maintains audio quality)
- **Result**: ~1-2 MB for 10-minute podcast (vs 5-10 MB with standard encoding)

## Computational Graphics Support

Generate images from:

### 1. Mermaid Diagrams
```python
video_options = VideoOptions(
    minimal_size=True,
    graphics_source="mermaid",
    graphics_content="""
graph TD
    A[Research Discovery] --> B[Analysis]
    B --> C[Podcast Generation]
    C --> D[Distribution]
"""
)
```

### 2. Python (Matplotlib/Plotly)
```python
video_options = VideoOptions(
    minimal_size=True,
    graphics_source="python",
    graphics_content="""
# Your matplotlib/plotly code here
plt.plot([1, 2, 3, 4], [1, 4, 9, 16])
plt.xlabel('Time')
plt.ylabel('Value')
plt.title('Scientific Data')
"""
)
```

### 3. LaTeX Formulas
```python
video_options = VideoOptions(
    minimal_size=True,
    graphics_source="latex",
    graphics_content=r"$E = mc^2$ or $\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}$"
)
```

### 4. Mathematica (if available)
```python
video_options = VideoOptions(
    minimal_size=True,
    graphics_source="mathematica",
    graphics_content="Plot[Sin[x], {x, 0, 2 Pi}]"
)
```

## Usage Examples

### Basic Usage with Computational Graphics
```python
from services.video_generation_service import VideoGenerationService, VideoOptions

service = VideoGenerationService()

# Generate minimal-size video with Mermaid diagram
output = await service.generate_podcast_video(
    audio_url="https://storage.googleapis.com/.../audio.mp3",
    canonical_filename="episode-001",
    video_options=VideoOptions(
        minimal_size=True,
        graphics_source="mermaid",
        graphics_content="graph TD\n    A --> B"
    )
)

print(f"Video URL: {output.video_url}")
print(f"File size: {output.file_size / 1024 / 1024:.2f} MB")
```

### Convenience Method
```python
# Shortcut method for minimal-size + graphics
output = await service.generate_minimal_video_with_graphics(
    audio_url="https://storage.googleapis.com/.../audio.mp3",
    graphics_source="python",
    graphics_content="plt.plot([1,2,3], [1,4,9])",
    canonical_filename="episode-001"
)
```

### Traditional Mode (with thumbnail URL)
```python
# Standard video with existing thumbnail
output = await service.generate_podcast_video(
    audio_url="https://storage.googleapis.com/.../audio.mp3",
    thumbnail_url="https://storage.googleapis.com/.../thumbnail.jpg",
    canonical_filename="episode-001",
    video_options=VideoOptions(
        minimal_size=True  # Still use minimal size for smaller files
    )
)
```

## Dependencies

### Required
- **FFmpeg**: For video encoding (`apt-get install ffmpeg`)
- **Python 3**: With matplotlib, numpy (for Python graphics)

### Optional (for specific graphics types)
- **Mermaid CLI**: `npm install -g @mermaid-js/mermaid-cli` (or uses API fallback)
- **LaTeX**: `apt-get install texlive-latex-base` (for LaTeX rendering)
- **ImageMagick or pdftoppm**: For LaTeX PDF→PNG conversion
- **Mathematica**: For Mathematica graphics (if available)

## File Size Comparison

| Mode | Frame Rate | Video Bitrate | 10-min Podcast Size |
|------|------------|---------------|---------------------|
| Standard | 30 fps | 1000k | ~5-10 MB |
| Minimal | 0.1 fps | 50k | ~1-2 MB |
| MP3 only | N/A | N/A | ~8-10 MB |

**Result**: Minimal-size mode creates files similar in size to MP3 files, but with embedded graphics!

## Integration with Podcast Generation

The video service can be integrated into the podcast generation pipeline at the `[VIDEO EXTENSION POINT]` in `podcast_generation_service.py`:

```python
# In podcast_generation_service.py, around line 2569
if request.format_type == "video" or request.include_video:
    video_service = VideoGenerationService()
    video_output = await video_service.generate_minimal_video_with_graphics(
        audio_url=audio_url,
        graphics_source="mermaid",  # or from request
        graphics_content=mermaid_diagram,  # generate from script/research
        canonical_filename=canonical_filename
    )
    # video_output.video_url can be stored/returned
```

## Notes

- **Computational graphics are generated on-the-fly** - no need to pre-create image files
- **Minimal-size mode is perfect for podcasts** - small files, embedded graphics, full compatibility
- **All graphics are rendered at specified resolution** - defaults to 1920x1080
- **Graphics generation happens before video encoding** - errors in graphics generation will fail early
- **Local file paths are handled automatically** - generated images are used directly without upload

## Timestamp Synchronization (NEW!)

### Multiple Visuals with Timestamps

You can now create videos with multiple visual segments that change at specific timestamps:

```python
from services.video_generation_service import VideoGenerationService, VideoOptions, VisualSegment

service = VideoGenerationService()

# Create visual segments with timestamps
segments = [
    VisualSegment(
        start_time=0.0,
        end_time=30.0,  # First 30 seconds
        graphics_source="mermaid",
        graphics_content="graph TD\n    A[Introduction] --> B[Main Topic]",
        transition="fade"
    ),
    VisualSegment(
        start_time=30.0,
        end_time=120.0,  # 30-120 seconds
        graphics_source="latex",
        graphics_content=r"$E = mc^2$",
        transition="crossfade"
    ),
    VisualSegment(
        start_time=120.0,
        end_time=None,  # Rest of audio
        graphics_source="python",
        graphics_content="plt.plot([1,2,3], [1,4,9])",
        transition="fade"
    )
]

video_options = VideoOptions(
    minimal_size=True,
    use_moviepy=True,  # Use MoviePy for advanced editing
    visual_segments=segments
)

output = await service.generate_podcast_video(
    audio_url="https://storage.googleapis.com/.../audio.mp3",
    canonical_filename="episode-001",
    video_options=video_options
)
```

### Using Claude.ai's Structure

The service now includes methods matching Claude.ai's suggested structure:

```python
# 1. Generate visual from LaTeX
image_path = await service.generate_math_visual(
    latex_string=r"$\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}$",
    output_path="/tmp/formula.png"
)

# 2. Create video from image sequence and audio
video_path = await service.create_video(
    image_sequence=[
        ("/tmp/image1.png", 0.0, 30.0),
        ("/tmp/image2.png", 30.0, 60.0),
        ("/tmp/image3.png", 60.0, None)  # None = until end
    ],
    audio_path="/tmp/audio.mp3",
    output_path="/tmp/output.mp4",
    fps=0.1,  # Minimal size mode
    transitions=["fade", "crossfade", "fade"]
)

# 3. Main workflow pipeline
output = await service.audio_to_video_pipeline(
    audio_file="https://storage.googleapis.com/.../audio.mp3",
    content_description={
        "canonical_filename": "episode-001",
        "minimal_size": True,
        "use_moviepy": True,
        "visual_segments": segments  # Or use single visual
    }
)
```

## MoviePy Support (NEW!)

MoviePy is now supported for easier video editing:

- **Automatic fallback**: If MoviePy unavailable, falls back to FFmpeg
- **Better transitions**: Fade, crossfade effects
- **Easier composition**: High-level Python API
- **Installation**: `pip install moviepy`

### MoviePy vs FFmpeg

- **MoviePy**: Easier Python API, better for complex editing, transitions
- **FFmpeg**: More reliable, faster, better for simple cases
- **Default**: MoviePy if available, FFmpeg as fallback

## Phase C: Transcript Parsing for Automatic Visual Timing (NEW!)

### Automatic Visual Generation from Transcripts

The service can now automatically analyze transcripts and generate synchronized visuals:

```python
from services.video_generation_service import VideoGenerationService, VideoOptions

service = VideoGenerationService()

# Generate video with automatic visual timing from transcript
output = await service.generate_video_from_transcript(
    audio_url="https://storage.googleapis.com/.../audio.mp3",
    transcript_url="https://storage.googleapis.com/.../transcript.md",
    canonical_filename="episode-001",
    video_options=VideoOptions(
        minimal_size=True,
        use_moviepy=True
    )
)
```

### How It Works

1. **Parse Transcript**: Extracts segments with timing (handles both timestamped and non-timestamped)
2. **LLM Analysis**: Uses Gemini to identify visual opportunities:
   - Mathematical equations → LaTeX visuals
   - Processes/workflows → Mermaid diagrams
   - Data/concepts → Python visualizations
3. **Automatic Timing**: Estimates timestamps if not provided (based on word count)
4. **Visual Generation**: Creates appropriate visuals for each segment
5. **Video Assembly**: Combines all visuals with audio using MoviePy or FFmpeg

### Transcript Formats Supported

**With Timestamps:**
```markdown
[00:00] **HOST:** Welcome to today's episode.

[00:30] **EXPERT:** The equation E equals mc squared is fundamental.

[01:00] **HOST:** Let's look at the process flow.
```

**Without Timestamps (auto-estimated):**
```markdown
**HOST:** Welcome to today's episode.

**EXPERT:** The equation E equals mc squared is fundamental.

**HOST:** Let's look at the process flow.
```

### Manual Transcript Parsing

You can also parse transcripts manually and extract visual cues:

```python
# Parse transcript
transcript_segments = await service.parse_transcript_with_timing(
    transcript_text=transcript_content,
    audio_duration=600.0,  # 10 minutes
    words_per_minute=150.0  # Average speaking rate
)

# Extract visual cues automatically
visual_segments = await service.extract_visual_cues_from_transcript(
    transcript_segments=transcript_segments,
    audio_duration=600.0
)

# Use extracted visuals
video_options = VideoOptions(
    minimal_size=True,
    visual_segments=visual_segments
)

output = await service.generate_podcast_video(
    audio_url="...",
    video_options=video_options,
    canonical_filename="episode-001"
)
```

### Visual Cue Detection

The LLM automatically detects:

- **Mathematical Content**: 
  - Keywords: "equation", "formula", "theorem", "proof"
  - Patterns: `$...$`, `\[...\]`, common equations
  - Generates: LaTeX visuals

- **Process/Workflow Content**:
  - Keywords: "process", "workflow", "diagram", "steps", "procedure"
  - Patterns: "first...then", "after...before", sequences
  - Generates: Mermaid diagrams

- **Data/Visualization Content**:
  - Keywords: "graph", "plot", "chart", "data", "trend"
  - Patterns: "increase", "decrease", "correlation"
  - Generates: Python matplotlib visualizations

### Fallback: Rule-Based Extraction

If LLM is unavailable, the service falls back to rule-based pattern matching:

```python
# Automatically falls back if LLM fails
visual_segments = await service.extract_visual_cues_from_transcript(
    transcript_segments=transcript_segments
)
# Uses pattern matching for: LaTeX, Mermaid, Python visuals
```

### Integration with Podcast Generation

You can integrate this into the podcast generation pipeline:

```python
# In podcast_generation_service.py
if request.format_type == "video" or request.include_video:
    video_service = VideoGenerationService()
    
    # Get transcript URL from podcast job
    transcript_url = job_data.get('transcript_url')
    
    # Generate video with automatic visuals
    video_output = await video_service.generate_video_from_transcript(
        audio_url=audio_url,
        transcript_url=transcript_url,
        canonical_filename=canonical_filename,
        video_options=VideoOptions(minimal_size=True)
    )
```

## Future Enhancements

- More graphics formats (SVG, Graphviz, etc.)
- Animated graphics sequences
- Scene detection from audio
- Custom visual templates per category
- Visual quality scoring and selection
