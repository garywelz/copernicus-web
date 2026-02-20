#!/usr/bin/env python3
"""
Generate Phase 1 Mathematics Processes with LLM-Generated Flowcharts

Uses Vertex AI (Gemini) to generate Mermaid flowcharts for each process,
applies the 5-color scheme, extracts entities, and creates complete JSON files.
"""

import json
import os
import sys
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add cloud-run-backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'cloud-run-backend'))

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False
    print("⚠️  Vertex AI not available. Install: pip install google-cloud-aiplatform")

from generate_metadata import count_mermaid_nodes, analyze_mermaid_gates

# Phase 1 Process Definitions
PHASE1_PROCESSES = [
    # Algebra
    {"subcategory": "abstract_algebra", "title": "Group Operation Verification", "description": "Verify that a binary operation forms a group by checking closure, associativity, identity, and inverse properties"},
    {"subcategory": "linear_algebra", "title": "Matrix Multiplication Algorithm", "description": "Step-by-step process for multiplying two matrices"},
    {"subcategory": "linear_algebra", "title": "Gaussian Elimination Process", "description": "Systematic method for solving systems of linear equations"},
    {"subcategory": "polynomial_algebra", "title": "Polynomial Long Division", "description": "Divide one polynomial by another using long division algorithm"},
    
    # Analysis
    {"subcategory": "calculus", "title": "Differentiation Using Chain Rule", "description": "Process for finding derivatives of composite functions"},
    {"subcategory": "calculus", "title": "Integration by Substitution", "description": "Method for evaluating integrals using u-substitution"},
    {"subcategory": "real_analysis", "title": "Limit Evaluation Process", "description": "Systematic approach to evaluating limits of functions"},
    {"subcategory": "differential_equations", "title": "Solving First-Order Linear ODE", "description": "Method for solving first-order linear ordinary differential equations"},
    {"subcategory": "numerical_analysis", "title": "Newton's Method for Root Finding", "description": "Iterative numerical method for finding roots of functions"},
    
    # Geometry
    {"subcategory": "euclidean_geometry", "title": "Triangle Area Calculation", "description": "Calculate area of triangle using various formulas"},
    {"subcategory": "differential_geometry", "title": "Curvature Calculation", "description": "Compute curvature of a curve in space"},
    {"subcategory": "topology", "title": "Graph Isomorphism Testing", "description": "Determine if two graphs are isomorphic"},
    {"subcategory": "computational_geometry", "title": "Convex Hull Algorithm", "description": "Find the convex hull of a set of points"},
    
    # Number Theory
    {"subcategory": "elementary_number_theory", "title": "Prime Factorization Algorithm", "description": "Decompose a number into its prime factors"},
    {"subcategory": "elementary_number_theory", "title": "Chinese Remainder Theorem", "description": "Solve systems of congruences using CRT"},
    {"subcategory": "computational_number_theory", "title": "Modular Exponentiation", "description": "Efficiently compute large powers modulo n"},
    {"subcategory": "computational_number_theory", "title": "Miller-Rabin Primality Test", "description": "Probabilistic test for determining if a number is prime"},
    
    # Probability & Statistics
    {"subcategory": "probability_theory", "title": "Bayes' Theorem Application", "description": "Update probabilities using conditional probability"},
    {"subcategory": "statistics", "title": "Hypothesis Testing Procedure", "description": "Statistical test for hypothesis validation"},
    {"subcategory": "statistics", "title": "Linear Regression Calculation", "description": "Compute linear regression line from data points"},
    {"subcategory": "stochastic_processes", "title": "Monte Carlo Simulation", "description": "Estimate values using random sampling"},
    
    # Combinatorics
    {"subcategory": "combinatorics", "title": "Permutation Generation", "description": "Generate all permutations of a set"},
    {"subcategory": "combinatorics", "title": "Binomial Coefficient Calculation", "description": "Compute combinations using binomial coefficients"},
    {"subcategory": "graph_theory", "title": "Dijkstra's Shortest Path Algorithm", "description": "Find shortest path between nodes in weighted graph"},
    {"subcategory": "graph_theory", "title": "Minimum Spanning Tree (Kruskal)", "description": "Find minimum spanning tree using Kruskal's algorithm"},
    
    # Logic & Foundations
    {"subcategory": "proof_methods", "title": "Proof by Contradiction", "description": "Prove statement by assuming its negation leads to contradiction"},
    {"subcategory": "proof_methods", "title": "Direct Proof Construction", "description": "Construct direct logical proof of statement"},
    {"subcategory": "set_theory", "title": "Set Union and Intersection", "description": "Perform set operations on collections"},
    {"subcategory": "computability_theory", "title": "Recursive Function Definition", "description": "Define functions using recursion"},
    
    # Applied Mathematics
    {"subcategory": "optimization", "title": "Gradient Descent Algorithm", "description": "Iterative optimization method for finding minima"},
    {"subcategory": "optimization", "title": "Simplex Method for Linear Programming", "description": "Solve linear programming problems using simplex algorithm"},
    {"subcategory": "cryptography", "title": "RSA Encryption Process", "description": "Encrypt message using RSA public-key cryptography"},
    {"subcategory": "cryptography", "title": "RSA Decryption Process", "description": "Decrypt message using RSA private key"},
    
    # Numerical Methods
    {"subcategory": "numerical_linear_algebra", "title": "LU Decomposition", "description": "Factor matrix into lower and upper triangular matrices"},
    {"subcategory": "numerical_integration", "title": "Trapezoidal Rule Integration", "description": "Approximate definite integral using trapezoidal rule"},
    {"subcategory": "numerical_optimization", "title": "Newton-Raphson Root Finding", "description": "Find roots using Newton-Raphson iteration"},
]

# Color scheme mapping
COLOR_SCHEME = {
    "trigger": {"color": "#ff6b6b", "text": "#fff", "name": "Triggers & Inputs"},
    "structure": {"color": "#ffd43b", "text": "#000", "name": "Structures & Objects"},
    "operation": {"color": "#51cf66", "text": "#fff", "name": "Processing & Operations"},
    "intermediate": {"color": "#74c0fc", "text": "#fff", "name": "Intermediates & States"},
    "product": {"color": "#b197fc", "text": "#fff", "name": "Products & Outputs"},
}

def create_process_id(title: str) -> str:
    """Convert title to process ID."""
    return title.lower().replace(' ', '-').replace("'", '').replace('(', '').replace(')', '').replace(',', '').replace(' ', '-')

def generate_mermaid_prompt(process_info: Dict[str, Any]) -> str:
    """Generate prompt for LLM to create Mermaid flowchart."""
    return f"""You are a mathematics process modeler. Create a detailed Mermaid flowchart for the following mathematics process.

Process Title: {process_info['title']}
Description: {process_info['description']}
Subcategory: {process_info['subcategory']}

Requirements:
1. Create a comprehensive flowchart showing all steps, decisions, and flows
2. Use node IDs like A1, B1, C1, etc. (use numbers to avoid conflicts)
3. Classify each node according to the 5-color scheme:
   - Red (#ff6b6b, white text): Triggers & Inputs - Initial conditions, inputs, starting materials
   - Yellow (#ffd43b, black text): Structures & Objects - Data structures, algorithms, logical constructs
   - Green (#51cf66, white text): Processing & Operations - Transformations, computations, operations
   - Blue (#74c0fc, white text): Intermediates & States - Intermediate products, temporary states
   - Purple (#b197fc, white text): Products & Outputs - Final outputs, results

4. Include decision points, loops, and branching logic where appropriate
5. Make the flowchart detailed enough to understand the complete process
6. Use proper Mermaid syntax: graph TD for top-down flowcharts
7. Add style statements for each node using: style NodeID fill:#COLOR,color:#TEXTCOLOR

Output ONLY the Mermaid code, starting with "graph TD" and including all style statements at the end."""

def extract_entities_from_mermaid(mermaid_code: str) -> List[str]:
    """Extract entity names from Mermaid flowchart."""
    if not mermaid_code:
        return []
    
    # Extract node labels from patterns like A1[Label] or A1(Label) or A1{Label}
    node_pattern = r'[A-Za-z0-9_]+\s*[\[\(\{]([^\]]+)[\]\)\}]'
    entities = re.findall(node_pattern, mermaid_code)
    
    # Remove duplicates and clean up
    unique_entities = list(set(entities))
    return unique_entities[:50]  # Limit to 50 entities

def initialize_vertex_ai():
    """Initialize Vertex AI client."""
    if not VERTEX_AI_AVAILABLE:
        return None
    
    try:
        project_id = os.getenv("GCP_PROJECT_ID", "regal-scholar-453620-r7")
        region = os.getenv("VERTEX_AI_REGION", "us-central1")
        
        vertexai.init(project=project_id, location=region)
        model = GenerativeModel("gemini-2.0-flash-exp")
        return model
    except Exception as e:
        print(f"⚠️  Failed to initialize Vertex AI: {e}")
        return None

def generate_flowchart_with_llm(process_info: Dict[str, Any], model) -> Optional[str]:
    """Generate Mermaid flowchart using LLM."""
    if not model:
        return None
    
    try:
        prompt = generate_mermaid_prompt(process_info)
        response = model.generate_content(prompt)
        
        # Extract Mermaid code from response
        mermaid_code = response.text.strip()
        
        # Clean up - remove markdown code blocks if present
        if mermaid_code.startswith("```"):
            lines = mermaid_code.split('\n')
            # Remove first line (```mermaid or ```)
            if lines[0].startswith("```"):
                lines = lines[1:]
            # Remove last line (```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            mermaid_code = '\n'.join(lines)
        
        return mermaid_code.strip()
    except Exception as e:
        print(f"   ❌ Error generating flowchart: {e}")
        return None

def create_process_json(process_info: Dict[str, Any], base_dir: Path, model) -> bool:
    """Create a complete process JSON file with LLM-generated flowchart."""
    process_id = create_process_id(process_info['title'])
    subcategory = process_info['subcategory']
    
    # Create subcategory directory if it doesn't exist
    subcat_dir = base_dir / subcategory
    subcat_dir.mkdir(exist_ok=True)
    
    json_file = subcat_dir / f"{process_id}.json"
    
    # Skip if file already exists
    if json_file.exists():
        print(f"   ⏭️  Skipping (already exists): {json_file.name}")
        return False
    
    print(f"   🔄 Generating flowchart...")
    
    # Generate Mermaid flowchart
    mermaid_code = generate_flowchart_with_llm(process_info, model)
    
    if not mermaid_code:
        print(f"   ❌ Failed to generate flowchart")
        return False
    
    # Extract entities
    entities = extract_entities_from_mermaid(mermaid_code)
    
    # Calculate node count and gates
    node_count = count_mermaid_nodes(mermaid_code)
    gate_analysis = analyze_mermaid_gates(mermaid_code)
    
    # Determine complexity based on node count
    if node_count < 20:
        complexity = "low"
    elif node_count < 40:
        complexity = "medium"
    else:
        complexity = "high"
    
    # Create process data structure
    process_data = {
        "id": process_id,
        "title": process_info['title'],
        "description": process_info['description'],
        "category": "mathematics",
        "subcategory": subcategory,
        "mermaid": mermaid_code,
        "entities": entities,
        "metadata": {
            "source": "programming_framework",
            "color_scheme": "discipline_based",
            "node_count": node_count,
            "complexity": complexity
        },
        "sources": [],
        "source_text": "Source information to be added - please specify the book, paper, or reference material used by the LLM to generate this flowchart."
    }
    
    # Write JSON file
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(process_data, f, indent=2, ensure_ascii=False)
    
    print(f"   ✅ Created: {json_file.name} ({node_count} nodes, {gate_analysis['and_gates']} AND, {gate_analysis['or_gates']} OR)")
    
    # Small delay to avoid rate limiting
    time.sleep(1)
    
    return True

def main():
    """Main function to generate all Phase 1 processes."""
    script_dir = Path(__file__).parent
    base_dir = script_dir
    
    print("=" * 70)
    print("Phase 1 Mathematics Process Generation")
    print("=" * 70)
    print(f"Total processes to generate: {len(PHASE1_PROCESSES)}\n")
    
    # Initialize Vertex AI
    model = initialize_vertex_ai()
    if not model:
        print("❌ Cannot proceed without Vertex AI. Please configure GCP credentials.")
        return
    
    successful = 0
    failed = 0
    skipped = 0
    
    for i, process_info in enumerate(PHASE1_PROCESSES, 1):
        print(f"\n[{i}/{len(PHASE1_PROCESSES)}] {process_info['title']}")
        print(f"   Subcategory: {process_info['subcategory']}")
        
        if create_process_json(process_info, base_dir, model):
            successful += 1
        else:
            # Check if it was skipped or failed
            process_id = create_process_id(process_info['title'])
            subcat_dir = base_dir / process_info['subcategory']
            json_file = subcat_dir / f"{process_id}.json"
            if json_file.exists():
                skipped += 1
            else:
                failed += 1
    
    print("\n" + "=" * 70)
    print("Generation Complete")
    print("=" * 70)
    print(f"✅ Successful: {successful}")
    print(f"⏭️  Skipped: {skipped}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {len(PHASE1_PROCESSES)}")
    
    if successful > 0:
        print(f"\n🔄 Regenerating metadata...")
        from generate_metadata import main as generate_metadata_main
        generate_metadata_main()
        
        print(f"\n🔄 Creating individual HTML pages...")
        from create_individual_pages import main as create_pages_main
        create_pages_main()

if __name__ == '__main__':
    main()

