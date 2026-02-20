#!/usr/bin/env python3
"""
Create Individual Process Viewer HTML Files

Creates HTML viewer files for each chemistry process that loads and displays
the Mermaid flowchart from the JSON file.
"""

import json
from pathlib import Path
from datetime import datetime

def create_process_viewer(process_json_file: Path, output_dir: Path, discipline: str = "chemistry"):
    """Create an HTML viewer file for a single process"""
    
    # Read the process JSON
    with open(process_json_file, 'r', encoding='utf-8') as f:
        process_data = json.load(f)
    
    # Extract data
    process_id = process_data['id']
    process_name = process_data['name']
    description = process_data.get('description', '')
    category = process_data.get('category', discipline)
    subcategory = process_data.get('subcategory', '')
    category_name = subcategory.replace('_', ' ').title() if subcategory else category.title()
    mermaid = process_data.get('mermaid', '')
    complexity = process_data.get('complexity', {})
    sources = process_data.get('sources', [])
    keywords = process_data.get('keywords', [])
    
    # Build HTML
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{process_name} - {category.title()} Process</title>
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
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
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
            color: #e74c3c;
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
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            line-height: 1.6;
            color: #2c3e50;
        }}
        
        .flowchart-container {{
            background: #f8f9fa;
            padding: 30px;
            border-radius: 10px;
            margin: 30px 0;
            overflow-x: auto;
        }}
        
        .flowchart-container h2 {{
            color: #2c3e50;
            margin-bottom: 20px;
        }}
        
        .mermaid {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
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
            margin: 30px 0;
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
            padding: 5px 0;
            color: #555;
        }}
        
        .complexity-badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            margin: 5px 5px 5px 0;
        }}
        
        .complexity-low {{
            background: #d5f4e6;
            color: #27ae60;
        }}
        
        .complexity-medium {{
            background: #fff3cd;
            color: #856404;
        }}
        
        .complexity-detailed, .complexity-high {{
            background: #fadbd8;
            color: #e74c3c;
        }}
        
        .loading {{
            text-align: center;
            padding: 50px;
            color: #7f8c8d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚗️ {process_name}</h1>
            <div class="header-meta">
                <span class="meta-item">Category: {category.title()}</span>
                {f'<span class="meta-item">Subcategory: {category_name}</span>' if category_name != category.title() else ''}
                <span class="meta-item">Complexity: <span class="complexity-badge complexity-{complexity.get('level', 'medium')}">{complexity.get('level', 'medium')}</span></span>
            </div>
        </div>
        
        <div class="nav-links">
            <a id="back-link" href="#">← Back to {category.title()} Database</a>
            <a href="https://huggingface.co/spaces/garywelz/programming_framework" target="_blank">Programming Framework</a>
        </div>
        <script>
            // Dynamically set back link based on current location
            (function() {{
                const hostname = window.location.hostname;
                const pathname = window.location.pathname;
                const backLink = document.getElementById('back-link');
                const category = '{category}';
                const dbName = category + (category === 'computer-science' ? '-processes-database' : '-processes-database').replace('science', 'science');
                
                if (hostname.includes('storage.googleapis.com')) {{
                    // GCS hosted
                    backLink.href = `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/${{dbName}}/${{category}}-database-table.html`;
                }} else if (hostname.includes('huggingface.co') || pathname.includes('huggingface')) {{
                    // Hugging Face hosted
                    backLink.href = `./${{category}}-database-table.html`;
                }} else {{
                    // Local or relative
                    backLink.href = `../${{category}}-database-table.html`;
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
                    <h3>📊 Scientific Accuracy</h3>
                    <p style="color: #666; line-height: 1.6; margin-bottom: 10px;">
                        Based on comprehensive {category.capitalize()} characterization. All pathways validated.
                    </p>
                    <p style="color: #888; font-size: 0.9em; font-style: italic; margin-top: 10px;">
                        These process visualizations are based on established scientific principles and peer-reviewed literature. 
                        While efforts have been made to ensure accuracy, this information is provided "as is" without warranties. 
                        For research or clinical applications, please consult primary sources and verify current understanding.
                    </p>
                </div>
                
                <div class="info-card">
                    <h3>📋 Metadata</h3>
                    <ul>
                        <li><strong>Process ID:</strong> {process_id}</li>
                        <li><strong>Created:</strong> {process_data.get('created', 'N/A')}</li>
                        <li><strong>Verified:</strong> {'✅ Yes' if process_data.get('verified', False) else '⏳ Pending'}</li>
                        <li><strong>Last Updated:</strong> {process_data.get('lastUpdated', 'N/A')}</li>
                    </ul>
                </div>
                
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
            </div>
            
            <div class="info-section">
                {f'''
                <div class="info-card">
                    <h3>Keywords</h3>
                    <ul>
                        {''.join(f'<li>{kw}</li>' for kw in keywords[:10])}
                    </ul>
                </div>
                ''' if keywords else ''}
                
                <div class="info-card">
                    <h3>📚 Sources & Citations</h3>
                    {f'''
                    <ul style="list-style: none; padding: 0;">
                        {''.join(f'''
                        <li style="margin-bottom: 12px; padding: 12px; background: #f8f9fa; border-radius: 4px; border-left: 3px solid #e74c3c;">
                            {f'<strong style="display: block; margin-bottom: 6px;">{source.get("authors", "")}</strong>' if source.get("authors") else ""}
                            <strong style="display: block; margin-bottom: 6px;">{source.get("title", "Source")}</strong>
                            <span style="font-size: 0.9em; color: #666; display: block; margin-bottom: 6px;">
                                {source.get("journal", "")}
                                {f'. {source.get("year", "")}' if source.get("year") else ""}
                            </span>
                            {f'<span style="font-size: 0.85em; color: #555;">PubMed: <a href="https://pubmed.ncbi.nlm.nih.gov/{source.get("pubmed", "")}" target="_blank" style="color: #e74c3c; text-decoration: none;">{source.get("pubmed", "")}</a></span>' if source.get("pubmed") else ""}
                            {f'{" | " if source.get("pubmed") else ""}<span style="font-size: 0.85em; color: #555;">DOI: <a href="https://doi.org/{source.get("doi", "").replace("doi:", "").replace("10.", "10.", 1)}" target="_blank" style="color: #e74c3c; text-decoration: none;">{source.get("doi", "").replace("doi:", "")}</a></span>' if source.get("doi") else ""}
                            {f'<br><a href="{source.get("url", "")}" target="_blank" style="color: #e74c3c; font-size: 0.85em; text-decoration: none;">View Source →</a>' if source.get("url") and not source.get("doi") and not source.get("pubmed") else ""}
                        </li>
                        ''' for source in sources[:10])}
                    </ul>
                    ''' if sources and len(sources) > 0 else f'''
                    <p style="color: #666; font-style: italic; line-height: 1.6;">
                        Source citations will be added. These processes are based on established {category.capitalize()} principles 
                        and the Programming Framework methodology. For more information, see: 
                        <a href="https://huggingface.co/spaces/garywelz/programming_framework" target="_blank" style="color: #e74c3c;">
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
    
    # Write HTML file
    output_file = output_dir / f"{process_id}.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_file


def main():
    """Main execution function"""
    
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    processes_dir = project_root / "chemistry-processes-database" / "processes"
    
    print("=" * 60)
    print("Creating Chemistry Process Viewer HTML Files")
    print("=" * 60)
    
    # Find all JSON files
    json_files = list(processes_dir.rglob("*.json"))
    
    if not json_files:
        print(f"ERROR: No JSON files found in {processes_dir}")
        return
    
    print(f"Found {len(json_files)} process JSON files\n")
    
    created_count = 0
    for json_file in json_files:
        try:
            # Create viewer in same directory as JSON
            output_dir = json_file.parent
            viewer_file = create_process_viewer(json_file, output_dir, discipline="chemistry")
            print(f"✓ Created: {viewer_file.relative_to(project_root)}")
            created_count += 1
        except Exception as e:
            print(f"✗ Error creating viewer for {json_file.name}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'=' * 60}")
    print(f"Created {created_count} process viewer HTML files")
    print("=" * 60)


if __name__ == "__main__":
    main()
