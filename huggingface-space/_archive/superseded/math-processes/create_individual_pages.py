#!/usr/bin/env python3
"""
Create individual HTML pages for each mathematics process

Reads process JSON files and creates individual HTML pages with:
- Process flowchart visualization
- Metadata display
- Source information
- Suggestion box
"""

import json
import os
import re
import html
from pathlib import Path
from typing import Dict, Any, List

def clean_mermaid_syntax(mermaid_code: str) -> str:
    """Clean Mermaid syntax to remove invalid patterns."""
    if not mermaid_code:
        return ""
    
    # First, fix unescaped quote patterns (after JSON parsing): /"text"/
    # Handle parentheses nodes: (/"text"/) or (/"text" more text/) -> (text)
    # Match everything up to /) to handle nested parentheses
    mermaid_code = re.sub(r'\(/"([^"]+)"[^/]*?/\)', r'(\1)', mermaid_code)
    
    # Handle bracket nodes: [/"text" /] or [/"text"/] or [/"text" more text/] -> [text]
    # Match everything up to /] to handle nested brackets
    mermaid_code = re.sub(r'\[/"([^"]+)"[^/]*?/\]', r'[\1]', mermaid_code)
    
    # Handle curly brace nodes: {/"text"/} or {/"text" more text/} -> {text}
    # Match everything up to /} to handle nested braces
    mermaid_code = re.sub(r'\{/"([^"]+)"[^/]*?/\}', r'{\1}', mermaid_code)
    
    # Also handle escaped quote patterns (in case they appear): /\"text\"/
    # Handle parentheses nodes: (/\"text\"/) or (/\"text\" more text/) -> (text)
    mermaid_code = re.sub(r'\(/\\"([^"]+)\\"[^/]*?/\)', r'(\1)', mermaid_code)
    
    # Handle bracket nodes: [/\"text\" /] or [/\"text\"/] or [/\"text\" more text/] -> [text]
    mermaid_code = re.sub(r'\[/\\"([^"]+)\\"[^/]*?/\]', r'[\1]', mermaid_code)
    
    # Handle curly brace nodes: {/\"text\"/} or {/\"text\" more text/} -> {text}
    mermaid_code = re.sub(r'\{/\\"([^"]+)\\"[^/]*?/\}', r'{\1}', mermaid_code)
    
    # Remove invalid class assignments like ]:::red, ]::yellow, }::yellow, etc.
    # Also remove ;::color patterns that come after nodes
    mermaid_code = re.sub(r'\]:::(red|yellow|green|blue|purple|orange|pink|gray|grey)', r']', mermaid_code)
    mermaid_code = re.sub(r'\}:::(red|yellow|green|blue|purple|orange|pink|gray|grey)', r'}', mermaid_code)
    mermaid_code = re.sub(r'\):::(red|yellow|green|blue|purple|orange|pink|gray|grey)', r')', mermaid_code)
    mermaid_code = re.sub(r'\]::(red|yellow|green|blue|purple|orange|pink|gray|grey)', r']', mermaid_code)
    mermaid_code = re.sub(r'\}::(red|yellow|green|blue|purple|orange|pink|gray|grey)', r'}', mermaid_code)
    mermaid_code = re.sub(r'\)::(red|yellow|green|blue|purple|orange|pink|gray|grey)', r')', mermaid_code)
    # Remove ;::color patterns that come after closing brackets/braces
    mermaid_code = re.sub(r'([\]\}\)]);::(red|yellow|green|blue|purple|orange|pink|gray|grey)', r'\1', mermaid_code)
    
    # Fix [/"text"/] patterns to [text] (handles all variations with spaces)
    # Pattern: [/"text" / ] or [/"text"/] or [/"text" more text] -> [text] or [text more text]
    # Use a more flexible pattern that matches anything between [/" and ] that contains a quote
    mermaid_code = re.sub(r'\[/"([^"]+)"[^\]]*\]', r'[\1]', mermaid_code)
    
    # Fix {/"text"/} patterns to {text} (handles all variations with spaces)
    mermaid_code = re.sub(r'\{/"([^"]+)"[^\}]*\}', r'{\1}', mermaid_code)
    
    # Fix /"text"\\] patterns (escaped backslashes)
    mermaid_code = re.sub(r'/\\"([^"]+)\\"[\\]+]', r'[\1]', mermaid_code)
    mermaid_code = re.sub(r'/\\"([^"]+)\\"[\\]+\s*/\}\)', r'[\1])', mermaid_code)
    mermaid_code = re.sub(r'/\\"([^"]+)\\"[\\]+\s*/\}', r'[\1]}', mermaid_code)
    
    # Fix pattern where node is defined and immediately re-referenced: ID[...] ID -->
    # Mermaid doesn't like this - should be: ID[...] --> (direct arrow)
    mermaid_code = re.sub(r'([A-Z0-9]+)\[([^\]]+)\]\s+\1\s*-->', r'\1[\2] -->', mermaid_code)
    mermaid_code = re.sub(r'([A-Z0-9]+)\(([^)]+)\)\s+\1\s*-->', r'\1(\2) -->', mermaid_code)
    mermaid_code = re.sub(r'([A-Z0-9]+)\{([^\}]+)\}\s+\1\s*-->', r'\1{\2} -->', mermaid_code)
    
    # Add spaces after node definitions when immediately followed by node IDs or style statements
    # Fix patterns like: )B1 --> or )style or ]B1 --> or ]style or }B1 --> or }style
    # Do this BEFORE converting nested parens so we can match the pattern correctly
    # Ensure space after closing brackets/braces/parens before node IDs or arrows
    mermaid_code = re.sub(r'([\)\]\}])([A-Z0-9])', r'\1 \2', mermaid_code)  # Add space before node ID
    mermaid_code = re.sub(r'([\)\]\}])(style)', r'\1 \2', mermaid_code)  # Add space before style
    # Also ensure space before arrows that come immediately after node definitions
    mermaid_code = re.sub(r'([\)\]\}])(\s*-->)', r'\1 \2', mermaid_code)  # Ensure space before arrow
    # Remove double spaces (normalize to single space)
    mermaid_code = re.sub(r'  +', r' ', mermaid_code)  # Replace multiple spaces with single space
    
    # Fix missing closing brackets for double-bracket nodes: [[...] should be [[...]]
    # Pattern: ID[[text] (missing closing bracket)
    # This happens when LLM generates [[ but only closes with ]
    mermaid_code = re.sub(r'([A-Z0-9]+)\[\[([^\]]+)\](\s|-->|style|$)', r'\1[[\2]]\3', mermaid_code)
    
    # Extract inline style statements and move them to the end
    # Pattern: ... --> NodeID style NodeID fill:... --> ...
    # We need to extract these and put them at the end
    # IMPORTANT: Match style statements but preserve edges that might come before/after
    style_pattern = r'\bstyle\s+([A-Za-z0-9]+)\s+fill:(#[0-9A-Fa-f]{3,6})\s*,\s*color:(#[0-9A-Fa-f]{3,6})\b'
    styles_found = {}
    for match in re.finditer(style_pattern, mermaid_code):
        node_id, fill, color = match.group(1), match.group(2), match.group(3)
        styles_found[node_id] = (fill, color)
    
    # Remove inline style statements from the middle of the code
    # Replace with a space to preserve structure, then clean up multiple spaces
    if styles_found:
        mermaid_code = re.sub(style_pattern, ' ', mermaid_code)
        # Clean up multiple spaces but preserve single spaces (needed for edges)
        mermaid_code = re.sub(r'  +', ' ', mermaid_code)
        mermaid_code = mermaid_code.strip()
    
    # Fix chained arrows on the same line: ...] --> NodeID[...] --> NodeID2[...]
    # Mermaid doesn't support: A --> B --> C on one line
    # Should be: A --> B\nB --> C
    # Pattern: ] --> NodeID[ (closing bracket, arrow, node definition)
    # We need to capture the source node ID and add it back
    def fix_chained_arrow(match):
        # Find the node ID before the arrow
        # Look backwards for the node ID
        before = mermaid_code[:match.start()]
        # Find the last node ID before this match
        node_match = re.search(r'([A-Z0-9]+)\[.*?\]\s*-->\s*$', before, re.MULTILINE)
        if node_match:
            source_id = node_match.group(1)
            target_id = match.group(1)
            return f']\n{source_id} --> {target_id}['
        return f']\n{match.group(1)}['
    
    # Simpler approach: match the pattern and add the connection
    # Pattern: NodeID[...] --> NodeID2[...] --> NodeID3[...]
    # Replace: NodeID[...] --> NodeID2[...]\nNodeID2 --> NodeID3[...]
    mermaid_code = re.sub(r'([A-Z0-9]+)\[([^\]]+)\]\s*-->\s*([A-Z0-9]+)\[', r'\1[\2]\n\1 --> \3[', mermaid_code)
    
    # Fix consecutive node definitions without arrows: ] A2[ or ] B2[
    # Mermaid doesn't allow: A1[text] A2[text] (two definitions back to back)
    # Solution: Add newline before standalone node definitions that follow a closing bracket
    # Pattern: ] [A-Z0-9]+[ (but not if it's part of an arrow: ] --> [)
    # Do this BEFORE space-adding to ensure proper formatting
    # Match: ] followed by whitespace (but not -->) then node definition
    mermaid_code = re.sub(r'\]\s+(?!-->)([A-Z0-9]+)\[', r']\n\1[', mermaid_code)
    
    # Also add newlines before node references that come after closing brackets
    # Pattern: ] B1 --> (closing bracket, space, node reference, arrow)
    # This helps Mermaid parse the structure better
    mermaid_code = re.sub(r'\]\s+([A-Z0-9]+\s*-->)', r']\n\1', mermaid_code)
    
    # Add newlines before all edges (arrows) that aren't already on new lines
    # This ensures each statement is on its own line, like GLMP does
    # Pattern: } B2 --> or ] B2 --> (but preserve existing newlines)
    mermaid_code = re.sub(r'([\]\}])\s+([A-Z0-9]+\s*-->)', r'\1\n\2', mermaid_code)
    mermaid_code = re.sub(r'([\)])\s+([A-Z0-9]+\s*-->)', r'\1\n\2', mermaid_code)
    
    # Add newlines between multiple statements on the same line
    # Pattern: ... --> Node1 Node2 --> (multiple node references/edges on one line)
    # Split by node references followed by arrows, but only when preceded by space or closing bracket/brace
    # This ensures we don't break node IDs that contain numbers
    mermaid_code = re.sub(r'(\s)([A-Z0-9]+\s*-->)', r'\1\n\2', mermaid_code)
    
    # Convert parentheses nodes with nested parentheses to bracket nodes
    # Mermaid can't handle: ID(text with (nested) parens) - it gets confused
    # Solution: Convert to ID["text with (nested) parens"]
    # Use a simpler approach: find all ID(text) patterns and convert if text has parens
    def convert_nested_parens(text):
        """Convert parentheses nodes with nested parens to bracket nodes."""
        result = []
        i = 0
        while i < len(text):
            # Look for node definition pattern: ID(text)
            match = re.match(r'([A-Z0-9]+)\(', text[i:])
            if match:
                node_id = match.group(1)
                start = i + len(node_id) + 1  # Position after ID(
                # Find the matching closing paren
                paren_count = 1
                j = start
                while j < len(text) and paren_count > 0:
                    if text[j] == '(':
                        paren_count += 1
                    elif text[j] == ')':
                        paren_count -= 1
                    j += 1
                
                if paren_count == 0:
                    # Found matching closing paren
                    node_text = text[start:j-1]  # Text between the parens
                    # Check if text contains parentheses
                    if '(' in node_text or ')' in node_text:
                        # Convert to bracket node
                        node_text = node_text.replace('"', '\\"')
                        result.append(f'{node_id}["{node_text}"]')
                    else:
                        # Keep as parentheses node
                        result.append(text[i:j])
                    i = j
                else:
                    # No matching paren found, keep original
                    result.append(text[i])
                    i += 1
            else:
                result.append(text[i])
                i += 1
        
        return ''.join(result)
    
    # Apply the conversion
    mermaid_code = convert_nested_parens(mermaid_code)
    
    # Add extracted styles at the end if we found any
    if styles_found:
        mermaid_code = mermaid_code.rstrip() + "\n\n"
        for node_id, (fill, color) in styles_found.items():
            mermaid_code += f"style {node_id} fill:{fill},color:{color}\n"
    
    # Ensure proper line breaks: graph TD should be on its own line
    mermaid_code = re.sub(r'^(graph\s+TD)\s+', r'\1\n', mermaid_code, flags=re.MULTILINE)
    
    # Split edges to one per line, preserving source node IDs
    # Pattern: NodeID[...] --> TargetID or NodeID(...) --> TargetID or NodeID{...} --> TargetID
    # We need to capture the full pattern and split it properly
    def split_edge_preserving_source(match):
        # Match: (NodeID)(bracket/brace/paren)(content)(closing)(spaces)(-->)(spaces)(TargetID)
        # Group 1: NodeID, Group 2: opening bracket/brace/paren, Group 3: content, 
        # Group 4: closing bracket/brace/paren, Group 5: TargetID
        node_id = match.group(1)
        opening = match.group(2)
        content = match.group(3)
        closing = match.group(4)
        target_id = match.group(5)
        # Return: NodeID[...]\nNodeID --> TargetID
        return f"{node_id}{opening}{content}{closing}\n{node_id} --> {target_id}"
    
    # Match full node definition followed by arrow: NodeID[...] --> TargetID
    # This handles [ ], ( ), { }, [[ ]], and preserves the source node ID
    # Need to handle nested brackets: [[...]] requires matching both opening brackets
    # Pattern: NodeID followed by [[...]] or [...], or (...), or {...}
    def split_edge_preserving_source_fixed(match):
        node_id = match.group(1)
        node_def = match.group(2)  # The full node definition including brackets
        target_id = match.group(3)
        # Return: NodeID[...]\nNodeID --> TargetID
        return f"{node_id}{node_def}\n{node_id} --> {target_id}"
    
    # Match patterns: NodeID[[...]] --> TargetID or NodeID[...] --> TargetID
    # Use non-greedy matching and handle nested brackets
    mermaid_code = re.sub(
        r'([A-Za-z0-9]+)(\[\[[^\]]+\]\]|\[[^\]]+\]|\([^)]+\)|\{[^\}]+\})\s+-->\s+([A-Za-z0-9]+)',
        split_edge_preserving_source_fixed,
        mermaid_code
    )
    
    # Also handle edges that are already on separate lines but missing source ID
    # Pattern: ]\n--> TargetID should become SourceID\nSourceID --> TargetID
    lines = mermaid_code.split('\n')
    fixed_lines = []
    for i, line in enumerate(lines):
        # If line starts with --> and previous line ends with ], ), or }
        if line.strip().startswith('-->') and i > 0:
            prev_line = lines[i-1].strip()
            # Extract node ID from previous line if it's a node definition
            node_match = re.match(r'^([A-Za-z0-9]+)(\[\[?[^\]]*\]|\([^)]*\)|\{[^\}]*\})$', prev_line)
            if node_match:
                node_id = node_match.group(1)
                # Replace --> TargetID with NodeID --> TargetID
                line = line.replace('-->', f'{node_id} -->', 1)
        fixed_lines.append(line)
    mermaid_code = '\n'.join(fixed_lines)
    
    # Normalize whitespace
    mermaid_code = re.sub(r'\n{3,}', '\n\n', mermaid_code)
    mermaid_code = mermaid_code.strip()
    
    return mermaid_code

def clean_entity_for_display(entity: str) -> str:
    """Clean entity text for safe HTML display."""
    if not entity:
        return ""
    
    original = entity
    
    # Remove malformed quote patterns: /"text"/ -> text, /&quot;text&quot;/ -> text
    entity = re.sub(r'/\\?"([^"]+)"\\?/', r'\1', entity)
    entity = re.sub(r'/&quot;([^&]+)&quot;/', r'\1', entity)
    entity = re.sub(r'^/&quot;([^&]*)', r'\1', entity)  # Handle incomplete patterns at start
    
    # Remove any Mermaid syntax fragments that might have leaked in (but preserve text)
    # Remove style statements
    entity = re.sub(r'\s*style\s+[A-Z0-9]+\s+fill:[^,]+,\s*color:[^\s]+\s*', ' ', entity)
    # Remove arrows and node references: --> NodeID
    entity = re.sub(r'\s*-->\s*[A-Z0-9]+(\[|\{|\(|$)', ' ', entity)
    # Remove conditional arrows: -- Yes --> or -- No -->
    entity = re.sub(r'\s*--\s*(Yes|No)\s*-->\s*', ' ', entity)
    
    # Remove Mermaid node IDs at start: E1 -- Yes, }E1, [A-Z0-9]+ at beginning
    entity = re.sub(r'^[A-Z0-9]+\s*--\s*(Yes|No)\s*', '', entity)
    entity = re.sub(r'^\}[A-Z0-9]+\s*', '', entity)
    entity = re.sub(r'^[A-Z0-9]+\s*[\[\(\{]\s*', '', entity)  # Remove leading ID[
    
    # Remove closing braces/brackets that are Mermaid syntax (at start or end)
    entity = re.sub(r'^[\]\)\}]+', '', entity)
    entity = re.sub(r'[\]\)\}]+$', '', entity)
    
    # Remove any remaining Mermaid node patterns but preserve text inside
    # Pattern: ID[...text...] -> extract just the text
    entity = re.sub(r'[A-Z0-9]+\s*\[([^\]]+)\]', r'\1', entity)
    entity = re.sub(r'[A-Z0-9]+\s*\(([^)]+)\)', r'\1', entity)
    entity = re.sub(r'[A-Z0-9]+\s*\{([^\}]+)\}', r'\1', entity)
    
    # Clean up extra whitespace and normalize
    entity = re.sub(r'\s+', ' ', entity).strip()
    
    # Skip entities that are too short, empty, or look like pure Mermaid syntax
    if len(entity) < 3:
        return ""
    if re.match(r'^[A-Z0-9\s\-]+$', entity) and len(entity) < 10:
        return ""
    
    # HTML escape to prevent XSS and rendering issues
    entity = html.escape(entity)
    
    return entity

def clean_entities(entities: List[str]) -> List[str]:
    """Clean a list of entities for display."""
    cleaned = []
    for entity in entities:
        cleaned_entity = clean_entity_for_display(entity)
        if cleaned_entity:  # Only add non-empty entities
            cleaned.append(cleaned_entity)
    return cleaned[:20]  # Limit to 20 entities

def create_process_page(process_data: Dict[str, Any], output_dir: Path) -> None:
    """Create an individual HTML page for a process."""
    process_id = process_data.get('id', 'unknown')
    process_name = process_data.get('title', process_data.get('name', 'Unknown Process'))
    description = process_data.get('description', '')
    subcategory = process_data.get('subcategory', 'general')
    category = process_data.get('category', 'mathematics')
    mermaid_code = process_data.get('mermaid', '')
    # Clean Mermaid syntax before embedding
    mermaid_code = clean_mermaid_syntax(mermaid_code)
    raw_entities = process_data.get('entities', [])
    entities = clean_entities(raw_entities)  # Clean entities for safe display
    metadata = process_data.get('metadata', {})
    node_count = metadata.get('node_count', 0)
    complexity = metadata.get('complexity', 'medium')
    
    # Get source information (to be added to JSON files)
    sources = process_data.get('sources', [])
    source_text = process_data.get('source_text', '')
    
    # Create HTML page
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{process_name} - Mathematics Process</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        .gradient-bg {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        .mermaid-container {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            margin: 20px 0;
        }}
    </style>
</head>
<body class="bg-gray-50">
    <!-- Header -->
    <header class="gradient-bg text-white">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            <div class="text-center">
                <div class="text-4xl mb-4">🔢</div>
                <h1 class="text-4xl font-bold mb-4">{process_name}</h1>
                <p class="text-lg opacity-90">Mathematics Process Visualization</p>
                <div class="mt-4">
                    <a href="https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/math-processes-database/mathematics-database-table.html" 
                       class="text-white hover:text-gray-200 underline">
                        ← Back to Mathematics Processes Database
                    </a>
                </div>
            </div>
        </div>
    </header>

    <!-- Main Content -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <!-- Process Information -->
        <div class="bg-white rounded-xl shadow-lg p-8 mb-8">
            <h2 class="text-2xl font-bold text-gray-900 mb-4">Process Information</h2>
            
            <div class="grid md:grid-cols-2 gap-6 mb-6">
                <div>
                    <h3 class="font-semibold text-gray-800 mb-2">Category</h3>
                    <p class="text-gray-600">{category}</p>
                </div>
                <div>
                    <h3 class="font-semibold text-gray-800 mb-2">Subcategory</h3>
                    <p class="text-gray-600">{subcategory.replace('_', ' ').title()}</p>
                </div>
                <div>
                    <h3 class="font-semibold text-gray-800 mb-2">Complexity</h3>
                    <p class="text-gray-600">{complexity}</p>
                </div>
                <div>
                    <h3 class="font-semibold text-gray-800 mb-2">Nodes</h3>
                    <p class="text-gray-600">{node_count}</p>
                </div>
            </div>
            
            {f'<div class="mb-6"><h3 class="font-semibold text-gray-800 mb-2">Description</h3><p class="text-gray-600">{description}</p></div>' if description else ''}
            
            {f'''<div class="mb-6">
                <h3 class="font-semibold text-gray-800 mb-2">Source Information</h3>
                <p class="text-gray-600">{source_text if source_text else 'Source information to be added'}</p>
                {f'<ul class="list-disc list-inside text-gray-600 mt-2">' + ''.join([f'<li>{source}</li>' for source in sources]) + '</ul>' if sources else ''}
            </div>'''}
        </div>

        <!-- Flowchart Visualization -->
        <div class="bg-white rounded-xl shadow-lg p-8 mb-8">
            <h2 class="text-2xl font-bold text-gray-900 mb-4">Process Flowchart</h2>
            <div class="mermaid-container">
                <div class="mermaid">
{mermaid_code}
                </div>
            </div>
        </div>

        <!-- Entities/Concepts -->
        {f'''<div class="bg-white rounded-xl shadow-lg p-8 mb-8">
            <h2 class="text-2xl font-bold text-gray-900 mb-4">Key Concepts</h2>
            <div class="flex flex-wrap gap-2">
                {''.join([f'<span class="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm">{entity}</span>' for entity in entities[:20]])}
            </div>
        </div>''' if entities else ''}

        <!-- Suggestion Box -->
        <div class="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl shadow-lg p-8 mb-8">
            <h2 class="text-2xl font-bold text-gray-900 mb-4">💡 Suggest Improvements</h2>
            <p class="text-gray-700 mb-4">
                Have suggestions for improving this process visualization? Found an error or want to add more detail? 
                We'd love to hear from you!
            </p>
            <a href="https://forms.gle/YOUR_FORM_ID" 
               target="_blank"
               class="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition text-lg font-medium">
                Suggest Improvements →
            </a>
        </div>
    </div>

    <!-- Footer -->
    <footer class="bg-gray-800 text-white py-8 mt-12">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <p class="text-sm opacity-75">Part of the Copernicus AI Knowledge Engine</p>
            <p class="text-xs opacity-50 mt-2">&copy; 2025 Gary Welz. All rights reserved.</p>
        </div>
    </footer>

    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
    </script>
</body>
</html>"""
    
    # Write HTML file
    output_file = output_dir / f"{process_id}.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Created: {output_file}")

def main():
    """Main function to create all process pages."""
    base_dir = Path(__file__).parent
    output_dir = base_dir / 'processes'
    output_dir.mkdir(exist_ok=True)
    
    # Scan all process JSON files
    subdirs = [d for d in base_dir.iterdir() if d.is_dir() and not d.name.startswith('.') and d.name != 'processes']
    
    for subdir in subdirs:
        json_files = list(subdir.glob('*.json'))
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    process_data = json.load(f)
                create_process_page(process_data, output_dir)
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
    
    print(f"\n✅ Created individual process pages in: {output_dir}")

if __name__ == '__main__':
    main()

