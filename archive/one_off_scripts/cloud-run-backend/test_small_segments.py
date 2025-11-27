#!/usr/bin/env python3
"""
Test script for small segment audio combination
Based on Google Cloud Assist recommendations
"""

import asyncio
import logging
from elevenlabs_voice_service import ElevenLabsVoiceService
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_small_segments():
    """Test audio combination with a small number of segments"""
    
    # Initialize the service
    voice_service = ElevenLabsVoiceService()
    
    # Create test segments (simulate small audio files)
    test_segments = []
    for i in range(5):  # Only 5 segments for testing
        # Create a small dummy MP3 segment (just for testing the combination logic)
        # In real usage, these would be actual ElevenLabs audio data
        dummy_segment = b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\x00" * 1000  # Minimal MP3 header + dummy data
        test_segments.append(dummy_segment)
        logger.info(f"Created test segment {i+1}: {len(dummy_segment)} bytes")
    
    try:
        logger.info(f"🧪 Testing audio combination with {len(test_segments)} small segments")
        
        # Test the temp file approach directly
        result = await voice_service._combine_audio_segments_with_temp_files(test_segments)
        
        logger.info(f"✅ Test successful! Combined audio size: {len(result)} bytes")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def test_memory_monitoring():
    """Test memory monitoring during audio processing"""
    import psutil
    
    logger.info("📊 Testing memory monitoring")
    
    # Monitor initial memory
    initial_memory = psutil.virtual_memory().percent
    logger.info(f"Initial memory usage: {initial_memory:.1f}%")
    
    # Create some objects to test memory tracking
    test_data = []
    for i in range(100):
        test_data.append(b"test data " * 1000)
        if i % 20 == 0:
            memory = psutil.virtual_memory().percent
            logger.info(f"Memory after {i} objects: {memory:.1f}%")
    
    # Clean up
    del test_data
    import gc
    gc.collect()
    
    final_memory = psutil.virtual_memory().percent
    logger.info(f"Final memory usage: {final_memory:.1f}%")
    logger.info(f"Memory change: {final_memory - initial_memory:.1f}%")

if __name__ == "__main__":
    print("🧪 Running small segment audio combination tests...")
    
    # Test memory monitoring first
    asyncio.run(test_memory_monitoring())
    
    # Test small segment combination
    success = asyncio.run(test_small_segments())
    
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Tests failed - check logs for details")



