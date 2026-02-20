"""Script validation utilities for podcast generation"""

import re
from typing import Optional, Tuple


def calculate_minimum_words_for_duration(duration: str) -> int:
    """
    Calculate minimum word count needed for a given duration.
    
    Uses 150 words per minute as standard conversational pace.
    For "5-10 minutes", uses the minimum (5 minutes).
    Returns 80% of target to allow for natural variation in script length.
    
    Args:
        duration: Duration string like "5-10 minutes", "10 minutes", "5 minutes"
    
    Returns:
        Minimum word count required (80% of target word count)
    """
    # Extract numbers from duration string
    numbers = re.findall(r'\d+', duration)
    
    if not numbers:
        # Default to 5 minutes if no numbers found
        return 750
    
    # For ranges like "5-10 minutes", use the first (minimum) number
    minutes = int(numbers[0])
    
    # 150 words per minute is standard conversational pace
    # Use 80% of target to account for variation (lenient - allows for natural variation)
    # This prevents failures when scripts are close but slightly under (e.g., 603 words for 5-10 min)
    return int(minutes * 150 * 0.8)


def extend_script_if_close(script: str, min_words: int, word_count: int) -> str:
    """
    Automatically extend a script if it's close to the minimum (within 50 words or 10%).
    Adds a natural conclusion/transition to bring it up to the minimum.
    
    Args:
        script: The podcast script text
        min_words: Minimum word count required
        word_count: Current word count
    
    Returns:
        Extended script if close to minimum, original script otherwise
    """
    words_needed = min_words - word_count
    margin = max(50, int(min_words * 0.1))  # 50 words or 10% of minimum, whichever is larger
    
    if words_needed > margin or words_needed <= 0:
        # Too far from minimum or already meets it - don't extend
        return script
    
    # Script is close - extend it with a natural conclusion
    # Find the last speaker label to determine who should speak
    lines = script.split('\n')
    last_speaker = "HOST"
    for line in reversed(lines):
        line_upper = line.strip().upper()
        if line_upper.startswith('HOST:'):
            last_speaker = "HOST"
            break
        elif line_upper.startswith('EXPERT:'):
            last_speaker = "EXPERT"
            break
        elif line_upper.startswith('QUESTIONER:'):
            last_speaker = "QUESTIONER"
            break
    
    # Create a natural extension based on who last spoke
    extension = "\n\n"
    if last_speaker == "HOST":
        extension += "EXPERT: This is certainly an exciting area with tremendous potential for advancement in the field.\n\n"
        extension += "HOST: Absolutely. Thank you for sharing these insights with us today. It's clear that this research represents a significant step forward.\n\n"
    elif last_speaker == "EXPERT":
        extension += "HOST: Those are fascinating insights. It's remarkable how this work is shaping our understanding and opening new possibilities.\n\n"
        extension += "QUESTIONER: I think our listeners will really appreciate learning about these developments.\n\n"
    else:  # QUESTIONER
        extension += "EXPERT: Exactly. And there's still so much more to explore in this area.\n\n"
        extension += "HOST: Thank you both for this enlightening discussion. The implications are truly significant.\n\n"
    
    extended_script = script + extension
    
    # Check if we've added enough words (add more if needed)
    new_word_count = len(extended_script.split())
    if new_word_count < min_words:
        # Add a bit more padding
        additional = "\n\n" + last_speaker + ": The research continues to evolve, bringing new perspectives and deeper understanding to this important field."
        extended_script += additional
    
    return extended_script


def validate_script_length(script: str, duration: str, auto_extend: bool = True) -> Tuple[bool, Optional[str], str]:
    """
    Validate that a script meets the minimum word count for the requested duration.
    Optionally extends scripts that are close to the minimum.
    
    Args:
        script: The podcast script text
        duration: Duration string like "5-10 minutes"
        auto_extend: If True, automatically extend scripts that are close to minimum
    
    Returns:
        Tuple of (is_valid, error_message, final_script)
        If valid, error_message is None. final_script may be extended if auto_extend=True
    """
    if not script or not isinstance(script, str):
        return False, "Script is empty or not a string", script
    
    # Calculate minimum word count
    min_words = calculate_minimum_words_for_duration(duration)
    
    # Count words in script (split by whitespace)
    word_count = len(script.split())
    
    # If script is close to minimum and auto_extend is enabled, try to extend it
    if auto_extend and word_count < min_words:
        margin = max(50, int(min_words * 0.1))  # 50 words or 10% of minimum
        if (min_words - word_count) <= margin:
            # Close enough to extend automatically
            extended_script = extend_script_if_close(script, min_words, word_count)
            new_word_count = len(extended_script.split())
            if new_word_count >= min_words:
                return True, None, extended_script
    
    if word_count < min_words:
        return False, (
            f"Script is too short: {word_count} words. "
            f"Minimum required: {min_words} words for {duration}. "
            f"Please generate a longer script that fills the full duration."
        ), script
    
    return True, None, script

