"""Script validation utilities for podcast generation"""

import re
from typing import Optional, Tuple


def calculate_minimum_words_for_duration(duration: str) -> int:
    """
    Calculate minimum word count needed for a given duration.
    
    Uses 150 words per minute as standard conversational pace.
    For "5-10 minutes", uses the minimum (5 minutes = 750 words).
    
    Args:
        duration: Duration string like "5-10 minutes", "10 minutes", "5 minutes"
    
    Returns:
        Minimum word count required
    """
    # Extract numbers from duration string
    numbers = re.findall(r'\d+', duration)
    
    if not numbers:
        # Default to 5 minutes if no numbers found
        return 750
    
    # For ranges like "5-10 minutes", use the first (minimum) number
    minutes = int(numbers[0])
    
    # 150 words per minute is standard conversational pace
    # Use 90% of target to account for variation (more lenient)
    return int(minutes * 150 * 0.9)


def validate_script_length(script: str, duration: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that a script meets the minimum word count for the requested duration.
    
    Args:
        script: The podcast script text
        duration: Duration string like "5-10 minutes"
    
    Returns:
        Tuple of (is_valid, error_message)
        If valid, error_message is None
    """
    if not script or not isinstance(script, str):
        return False, "Script is empty or not a string"
    
    # Calculate minimum word count
    min_words = calculate_minimum_words_for_duration(duration)
    
    # Count words in script (split by whitespace)
    word_count = len(script.split())
    
    if word_count < min_words:
        return False, (
            f"Script is too short: {word_count} words. "
            f"Minimum required: {min_words} words for {duration}. "
            f"Please generate a longer script that fills the full duration."
        )
    
    return True, None

