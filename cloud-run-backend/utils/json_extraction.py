"""Improved JSON extraction that handles nested structures properly"""

import json
import re
from typing import Optional, Dict, Any


def extract_json_object(text: str) -> Optional[str]:
    """
    Extract a complete JSON object from text, handling nested structures.
    Uses brace matching to find the complete object, not just non-greedy regex.
    """
    # First try to find markdown code block
    markdown_match = re.search(r'```json\s*(\{.*?)\s*```', text, re.DOTALL)
    if markdown_match:
        json_start = markdown_match.start(1)
        text_to_search = text[json_start:]
    else:
        # Find first opening brace
        json_start = text.find('{')
        if json_start == -1:
            return None
        text_to_search = text[json_start:]
    
    # Now find the matching closing brace by counting braces
    brace_count = 0
    in_string = False
    escape_next = False
    
    for i, char in enumerate(text_to_search):
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    # Found the matching closing brace
                    return text_to_search[:i+1]
    
    return None


def _extract_json_from_response_improved(text: str) -> dict:
    """
    Improved JSON extraction that properly handles nested structures
    """
    # Try improved extraction first
    json_str = extract_json_object(text)
    
    if not json_str:
        # Fallback to original regex method
        json_match = re.search(r'```json\s*(\{.*?\})\s*```|(\{.*?\})', text, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON object found in the AI's response.")
        json_str = json_match.group(1) or json_match.group(2)
    
    # Continue with existing parsing logic
    def clean_json_string(s):
        """Clean JSON string by removing or replacing invalid control characters"""
        import string
        cleaned = ""
        for char in s:
            if char in string.printable or char in '\n\t\r':
                cleaned += char
            else:
                cleaned += ' '
        cleaned = cleaned.replace('\x00', '')
        cleaned = re.sub(r'\\"([^"]*?)\\""', r'\\"\1\\"', cleaned)
        cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
        cleaned = re.sub(r'\\([^"\\/bfnrtu])', r'\1', cleaned)
        return cleaned
    
    def _extract_essential_json(json_str: str) -> dict:
        title_match = re.search(r'"title"\s*:\s*"([^"]+)"', json_str)
        script_match = re.search(r'"script"\s*:\s*"([^"]*)"', json_str, re.DOTALL)
        
        if title_match and script_match:
            title = title_match.group(1)
            script = script_match.group(1)
            script = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', script)
            script = script.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"')
            return {"title": title, "script": script}
        else:
            raise ValueError("Could not extract essential JSON structure")
    
    parsing_attempts = [
        lambda: json.loads(json_str),
        lambda: json.loads(clean_json_string(json_str)),
        lambda: json.loads(re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', json_str)),
        lambda: json.loads(re.sub(r'[^\x20-\x7E\n\t\r]', '', json_str)),
        lambda: json.loads(re.sub(r',(\s*[}\]])', r'\1', clean_json_string(json_str))),
        lambda: _extract_essential_json(json_str)
    ]
    
    for i, attempt in enumerate(parsing_attempts, 1):
        try:
            return attempt()
        except json.JSONDecodeError:
            if i == len(parsing_attempts):
                raise ValueError(f"Failed to decode extracted JSON after {len(parsing_attempts)} attempts")
        except Exception:
            if i == len(parsing_attempts):
                raise
    
    raise ValueError("JSON extraction failed")

