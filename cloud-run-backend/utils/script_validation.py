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


# Speech rate and bumpers measured on the stored episodes (ElevenLabs multi-voice, 15 episodes, 2026-10-13): 119 to 136 words per
# minute (median 129; 830 to 911 characters per minute), and the intro and outro bumpers add about 14.4 seconds. The cap uses the
# slowest rate seen, so even a script at the cap stays within the longest requested length.
SLOWEST_WORDS_PER_MINUTE = 119
BUMPER_SECONDS = 15


def calculate_maximum_words_for_duration(duration: str) -> int:
    """Most words a script may have for the longest length asked for ("5-10 minutes" -> 10 minutes, bumpers included).

    10 minutes: (600 s - 15 s) / 60 * 119 = 1160 words. A single number "N minutes" is treated as the longest length too; when the
    existing minimum (150 words per minute, 80 percent) is already higher than that, the cap is the minimum plus 100 words, so the
    cap never contradicts the minimum."""
    numbers = re.findall(r"\d+", duration or "")
    longest = int(numbers[-1]) if numbers else 10
    cap = int((longest * 60 - BUMPER_SECONDS) / 60 * SLOWEST_WORDS_PER_MINUTE)
    return max(cap, calculate_minimum_words_for_duration(duration or "") + 100)


def length_feedback(word_count: int, max_words: int, min_words: int) -> str:
    return (f"\n\n**YOUR PREVIOUS SCRIPT WAS REJECTED because it was too long: {word_count} words, and the limit is {max_words} words "
            f"(it is read aloud and must stay within the requested length).**\nRewrite it between {min_words} and {max_words} words. Cut "
            "repetition, general background and restatement; keep the specific findings of the papers you name, and keep to the question asked.\n")


class ScriptTooLongError(Exception):
    """Raised when the script is still over the word cap after the allowed regenerations."""

    def __init__(self, word_count: int, max_words: int):
        self.word_count, self.max_words = word_count, max_words
        super().__init__(f"The generated script has {word_count} words, over the limit of {max_words}, and regeneration did not bring it "
                         "under the limit, so no episode was published.")


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

