#!/usr/bin/env python3
"""
Create Individual Process Viewer HTML Files (Generic for all disciplines)
"""

import json
from pathlib import Path

def create_process_viewer(process_json_file: Path, output_dir: Path, discipline: str = "chemistry"):
    """Create an HTML viewer file for a single process"""
    
    discipline_config = {
        "chemistry": {
            "name": "Chemistry",
            "database_table": "chemistry-database-table.html",
            "gcs_path": "chemistry-processes-database",
            "color": "#e74c3c"
        },
        "physics": {
            "name": "Physics",
            "database_table": "physics-database-table.html",
            "gcs_path": "physics-processes-database",
            "color": "#3498db"
        },
        "computer_science": {
            "name": "Computer Science",
            "database_table": "computer-science-database-table.html",
            "gcs_path": "computer-science-processes-database",
            "color": "#9b59b6"
        },
        "mathematics": {
            "name": "Mathematics",
            "database_table": "mathematics-database-table.html",
            "gcs_path": "mathematics-processes-database",
            "color": "#e67e22"
        },
        "biology": {
            "name": "Biology",
            "database_table": "biology-database-table.html",
            "gcs_path": "biology-processes-database",
            "color": "#27ae60"
        }
    }
    
    config = discipline_config.get(discipline, discipline_config["chemistry"])
    
    # Read the process JSON
    with open(process_json_file, 'r', encoding='utf-8') as f:
        process_data = json.load(f)
    
    # Extract data
    # IMPORTANT: process JSON filenames (stem) are what the database table links to:
    # `processes/<subcategory>/<process.id>.html`.
    # The JSON's internal `id` field is not always the same as the filename.
    file_id = process_json_file.stem
    process_id = process_data.get('id', file_id)
    process_name = process_data['name']
    description = process_data.get('description', '')
    subcategory = process_data.get('subcategory', '')
    subcategory_name = process_data.get('subcategory_name', subcategory.replace('_', ' ').title())
    mermaid = process_data.get('mermaid', '')
    complexity = process_data.get('complexity', {})
    sources = process_data.get('sources', [])
    keywords = process_data.get('keywords', [])
    
    # Build HTML (same template as chemistry, adapted)
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{process_name} - {config["name"]} Process</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, {config["color"]} 0%, {config["color"]}dd 100%);
            color: white;
            padding: 30px;
        }}
        
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 2em;
            font-weight: 300;
        }}
        
        .header-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-top: 15px;
            font-size: 0.9em;
            opacity: 0.9;
        }}
        
        .meta-item {{
            background: rgba(255,255,255,0.2);
            padding: 5px 12px;
            border-radius: 20px;
        }}
        
        .nav-links {{
            padding: 15px 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #ecf0f1;
        }}
        
        .nav-links a {{
            color: {config["color"]};
            text-decoration: none;
            margin-right: 20px;
            font-weight: 500;
        }}
        
        .nav-links a:hover {{
            text-decoration: underline;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .description {{
            margin-bottom: 30px;
        }}
        
        .description h2 {{
            color: #2c3e50;
            margin-bottom: 15px;
        }}
        
        .flowchart-container {{
            margin: 30px 0;
        }}
        
        .flowchart-container h2 {{
            color: #2c3e50;
            margin-bottom: 15px;
        }}
        
        .mermaid {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #ecf0f1;
            overflow-x: auto;
        }}
        
        .color-legend {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin: 30px 0;
        }}
        
        .color-legend h3 {{
            color: #2c3e50;
            margin-bottom: 15px;
        }}
        
        .color-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        
        .color-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px;
            background: white;
            border-radius: 5px;
        }}
        
        .color-box {{
            width: 30px;
            height: 30px;
            border-radius: 4px;
            border: 1px solid #ddd;
        }}
        
        .info-section {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }}
        
        .info-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
        }}
        
        .info-card h3 {{
            color: #2c3e50;
            margin-bottom: 15px;
        }}
        
        .info-card ul {{
            list-style: none;
            padding: 0;
        }}
        
        .info-card li {{
            padding: 8px 0;
            border-bottom: 1px solid #ecf0f1;
        }}
        
        .info-card li:last-child {{
            border-bottom: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{process_name}</h1>
            <div class="header-meta">
                <span class="meta-item">{config["name"]}</span>
                <span class="meta-item">{subcategory_name}</span>
                <span class="meta-item">Complexity: {complexity.get('level', 'unknown')}</span>
            </div>
        </div>
        
        <div class="nav-links">
            <a id="back-link" href="#">← Back to {config["name"]} Database</a>
            <a href="https://huggingface.co/spaces/garywelz/programming_framework" target="_blank">Programming Framework</a>
        </div>
        <script>
            // Dynamically set back link based on current location
            (function() {{
                const hostname = window.location.hostname;
                const pathname = window.location.pathname;
                const backLink = document.getElementById('back-link');
                
                if (hostname.includes('storage.googleapis.com')) {{
                    // GCS hosted
                    backLink.href = 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/{config["gcs_path"]}/{config["database_table"]}';
                }} else if (hostname.includes('huggingface.co') || pathname.includes('huggingface')) {{
                    // Hugging Face hosted
                    backLink.href = '../{config["database_table"]}';
                }} else {{
                    // Local or relative
                    backLink.href = '../{config["database_table"]}';
                }}
            }})();
        </script>
        
        <div class="content">
            <div class="description">
                <h2>Description</h2>
                <p>{description}</p>
            </div>
            
            <div class="flowchart-container">
                <h2>Process Flowchart</h2>
                <div class="mermaid">
{mermaid}
                </div>
            </div>
            
            <div class="color-legend">
                <h3>🎨 Color Scheme (5-Color System)</h3>
                <div class="color-grid">
                    <div class="color-item">
                        <div class="color-box" style="background: #ff6b6b;"></div>
                        <div>
                            <strong>Red</strong><br>
                            <small>Triggers & Inputs</small>
                        </div>
                    </div>
                    <div class="color-item">
                        <div class="color-box" style="background: #ffd43b;"></div>
                        <div>
                            <strong>Yellow</strong><br>
                            <small>Structures & Objects</small>
                        </div>
                    </div>
                    <div class="color-item">
                        <div class="color-box" style="background: #51cf66;"></div>
                        <div>
                            <strong>Green</strong><br>
                            <small>Processing & Operations</small>
                        </div>
                    </div>
                    <div class="color-item">
                        <div class="color-box" style="background: #74c0fc;"></div>
                        <div>
                            <strong>Blue</strong><br>
                            <small>Intermediates & States</small>
                        </div>
                    </div>
                    <div class="color-item">
                        <div class="color-box" style="background: #b197fc;"></div>
                        <div>
                            <strong>Violet</strong><br>
                            <small>Products & Outputs</small>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="info-section">
                <div class="info-card">
                    <h3>Process Statistics</h3>
                    <ul>
                        <li><strong>Nodes:</strong> {complexity.get('nodes', 0)}</li>
                        <li><strong>Edges:</strong> {complexity.get('edges', 0)}</li>
                        <li><strong>Conditionals:</strong> {complexity.get('conditionals', 0)}</li>
                        <li><strong>AND Gates:</strong> {complexity.get('logicGates', {}).get('andGates', 0)}</li>
                        <li><strong>OR Gates:</strong> {complexity.get('logicGates', {}).get('orGates', 0)}</li>
                        <li><strong>Total Gates:</strong> {complexity.get('logicGates', {}).get('total', 0)}</li>
                    </ul>
                </div>
                
                {f'''
                <div class="info-card">
                    <h3>Keywords</h3>
                    <ul>
                        {''.join(f'<li>{kw}</li>' for kw in keywords[:10])}
                    </ul>
                </div>
                ''' if keywords else ''}
                
                <div class="info-card">
                    <h3>Sources & References</h3>
                    {f'''
                    <ul style="list-style: none; padding: 0;">
                        {''.join(f'''
                        <li style="margin-bottom: 12px; padding: 8px; background: #ffffff; border-radius: 4px;">
                            <strong>{source.get("title", "Source")}</strong>
                            {f'<br><span style="font-size: 0.9em; color: #666;">{source.get("authors", "")}' if source.get("authors") else ""}
                            {f', {source.get("journal", "")}' if source.get("journal") else ""}
                            {f' ({source.get("year", "")})' if source.get("year") else ""}
                            {f'</span>' if source.get("authors") or source.get("journal") or source.get("year") else ""}
                            {f'<br><a href="https://doi.org/{source.get("doi", "").replace("doi:", "")}" target="_blank" style="color: {config["color"]}; font-size: 0.85em;">DOI: {source.get("doi", "").replace("doi:", "")}</a>' if source.get("doi") else ""}
                            {f'<br><a href="{source.get("url", "")}" target="_blank" style="color: {config["color"]}; font-size: 0.85em;">View Source</a>' if source.get("url") and not source.get("doi") else ""}
                        </li>
                        ''' for source in sources[:10])}
                    </ul>
                    ''' if sources and len(sources) > 0 else f'''
                    <p style="color: #666; font-style: italic;">
                        Source citations will be added. These processes are based on established {discipline.replace("_", " ")} principles 
                        and the Programming Framework methodology. For more information, see: 
                        <a href="https://huggingface.co/spaces/garywelz/programming_framework" target="_blank" style="color: {config["color"]};">
                            Programming Framework Documentation
                        </a>
                    </p>
                    '''}
                </div>
            </div>
        </div>
    </div>
    
    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'default',
            flowchart: {{
                useMaxWidth: false,
                htmlLabels: true,
                curve: 'linear',
                nodeSpacing: 30,
                rankSpacing: 30,
                padding: 10
            }},
            themeVariables: {{
                fontFamily: 'Arial Unicode MS, Arial, sans-serif'
            }}
        }});
    </script>
</body>
</html>'''
    
    # Write HTML file in same directory as JSON, matching the JSON filename stem
    output_file = output_dir / f"{file_id}.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_file


def main():
    """Main execution function"""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python create_generic_viewers.py <discipline> <processes_dir>")
        print("Example: python create_generic_viewers.py physics physics-processes-database/processes")
        return
    
    discipline = sys.argv[1]
    processes_dir = Path(sys.argv[2])
    
    print("=" * 60)
    print(f"Creating {discipline.replace('_', ' ').title()} Process Viewer HTML Files")
    print("=" * 60)
    
    json_files = list(processes_dir.rglob("*.json"))
    
    if not json_files:
        print(f"ERROR: No JSON files found in {processes_dir}")
        return
    
    print(f"Found {len(json_files)} process JSON files\n")
    
    for json_file in json_files:
        try:
            output_dir = json_file.parent
            viewer_file = create_process_viewer(json_file, output_dir, discipline)
            print(f"✓ Created: {viewer_file.name}")
        except Exception as e:
            print(f"✗ Error creating viewer for {json_file.name}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\nCreated {len(json_files)} viewer HTML files")

if __name__ == "__main__":
    main()
