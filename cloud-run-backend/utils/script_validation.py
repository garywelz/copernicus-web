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


# Word cap per requested minute. Gary chose 1,200 words for "5-10 minutes" (2026-10-13), i.e. 120 words per minute of the longest length.
# Measured on 15 stored ElevenLabs episodes: 119 to 136 words per minute (median 129) plus about 14.4 s of bumpers, so a script at the cap
# runs 9.3 minutes at the median rate and about 10.3 minutes in the slowest case seen.
MAX_WORDS_PER_MINUTE = 120


def calculate_maximum_words_for_duration(duration: str) -> int:
    """Most words a script may have for the longest length asked for ("5-10 minutes" -> 10 minutes -> 1200 words).

    A single number "N minutes" is treated as the longest length too; when the existing minimum (150 words per minute, 80 percent) is
    already higher than that, the cap is the minimum plus 100 words, so the cap never contradicts the minimum."""
    numbers = re.findall(r"\d+", duration or "")
    longest = int(numbers[-1]) if numbers else 10
    return max(longest * MAX_WORDS_PER_MINUTE, calculate_minimum_words_for_duration(duration or "") + 100)


def length_feedback(word_count: int, max_words: int, min_words: int) -> str:
    return (f"\n\n**YOUR PREVIOUS SCRIPT WAS REJECTED because it was too long: {word_count} words, and the limit is {max_words} words "
            f"(it is read aloud and must stay within the requested length).**\nRewrite it between {min_words} and {max_words} words. Cut "
            "repetition, general background and restatement; keep the specific findings of the papers you name, and keep to the question asked.\n")


def short_feedback(word_count: int, min_words: int, max_words: int) -> str:
    return (f"\n\n**YOUR PREVIOUS SCRIPT WAS REJECTED because it was too short: {word_count} words, and the minimum is {min_words} words.**\n"
            f"Rewrite it between {min_words} and {max_words} words by covering what the papers you name actually found in more detail "
            "(methods, results, limits). Do not pad with general remarks or repetition.\n")


class ScriptTooShortError(Exception):
    """Raised when the script is still under the minimum after the allowed regenerations. Scripts are never padded."""

    def __init__(self, word_count: int, min_words: int):
        self.word_count, self.min_words = word_count, min_words
        super().__init__(f"The generated script has {word_count} words, under the minimum of {min_words}, and regeneration did not "
                         "lengthen it, so no episode was published.")


class ScriptTooLongError(Exception):
    """Raised when the script is still over the word cap after the allowed regenerations."""

    def __init__(self, word_count: int, max_words: int):
        self.word_count, self.max_words = word_count, max_words
        super().__init__(f"The generated script has {word_count} words, over the limit of {max_words}, and regeneration did not bring it "
                         "under the limit, so no episode was published.")


def validate_script_length(script: str, duration: str) -> Tuple[bool, Optional[str], str]:
    """Validate that a script meets the minimum word count for the requested duration.

    A script that is too short is never padded (an older version appended unchecked boilerplate sentences to scripts that were close
    to the minimum); it is regenerated with feedback, and fails if it stays short.

    Returns (is_valid, error_message, script); the script is returned unchanged."""
    if not script or not isinstance(script, str):
        return False, "Script is empty or not a string", script
    min_words = calculate_minimum_words_for_duration(duration)
    word_count = len(script.split())
    if word_count < min_words:
        return False, (
            f"Script is too short: {word_count} words. "
            f"Minimum required: {min_words} words for {duration}. "
            f"Please generate a longer script that fills the full duration."
        ), script
    return True, None, script
