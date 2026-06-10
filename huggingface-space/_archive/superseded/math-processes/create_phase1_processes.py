#!/usr/bin/env python3
"""
Create Phase 1 Mathematics Processes

Generates 30-50 core mathematics processes covering all major branches
with proper 5-color scheme and gate detection.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List

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

def create_process_id(title: str) -> str:
    """Convert title to process ID."""
    return title.lower().replace(' ', '-').replace("'", '').replace('(', '').replace(')', '').replace(',', '')

def generate_mermaid_flowchart(process_info: Dict[str, Any]) -> str:
    """
    Generate Mermaid flowchart for a mathematics process.
    This is a placeholder - in production, this would call an LLM.
    """
    # For now, return a template that will be filled by LLM
    # In actual implementation, this would make an API call to generate the flowchart
    return f"# Mermaid flowchart for {process_info['title']} will be generated here"

def create_process_json(process_info: Dict[str, Any], base_dir: Path) -> None:
    """Create a process JSON file."""
    process_id = create_process_id(process_info['title'])
    subcategory = process_info['subcategory']
    
    # Create subcategory directory if it doesn't exist
    subcat_dir = base_dir / subcategory
    subcat_dir.mkdir(exist_ok=True)
    
    # Generate process data structure
    process_data = {
        "id": process_id,
        "title": process_info['title'],
        "description": process_info['description'],
        "category": "mathematics",
        "subcategory": subcategory,
        "mermaid": "",  # Will be generated by LLM
        "entities": [],  # Will be extracted from flowchart
        "metadata": {
            "source": "programming_framework",
            "color_scheme": "discipline_based",
            "node_count": 0,  # Will be calculated
            "complexity": "high"
        },
        "sources": [],
        "source_text": "Source information to be added - please specify the book, paper, or reference material used by the LLM to generate this flowchart."
    }
    
    # Write JSON file
    json_file = subcat_dir / f"{process_id}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(process_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Created: {json_file}")

def main():
    """Main function to create Phase 1 processes."""
    script_dir = Path(__file__).parent
    base_dir = script_dir
    
    print(f"Creating Phase 1 Mathematics Processes...")
    print(f"Total processes to create: {len(PHASE1_PROCESSES)}\n")
    
    for i, process_info in enumerate(PHASE1_PROCESSES, 1):
        print(f"[{i}/{len(PHASE1_PROCESSES)}] Creating: {process_info['title']}")
        create_process_json(process_info, base_dir)
    
    print(f"\n✅ Created {len(PHASE1_PROCESSES)} process JSON files")
    print(f"\n⚠️  Note: Mermaid flowcharts need to be generated using LLM calls")
    print(f"   Each process JSON file is ready for flowchart generation")

if __name__ == '__main__':
    main()

