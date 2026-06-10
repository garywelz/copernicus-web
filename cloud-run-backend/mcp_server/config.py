"""
MCP Server Configuration

Configuration constants for the CopernicusAI Knowledge Engine MCP Server.

Copyright (c) 2025 Gary Welz / CopernicusAI
Licensed under MIT License
"""

import os

# Google Cloud Configuration
GCP_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "regal-scholar-453620-r7")
# NOTE: This project uses a named Firestore database ("copernicusai").
# If this is left as "(default)", MCP tools (vector search, paper tools, etc.)
# will read from an empty/default DB and return no results even when content exists.
FIRESTORE_DATABASE = os.getenv("FIRESTORE_DATABASE", "copernicusai")

# Firestore Collection Names
COLLECTION_PAPERS = "research_papers"
COLLECTION_PODCASTS = "episodes"
COLLECTION_EPISODES = "episodes"  # Alias for COLLECTION_PODCASTS
COLLECTION_GLMP_PROCESSES = "glmp_processes"
COLLECTION_MATH_PROCESSES = "math_processes"
COLLECTION_CHEMISTRY_PROCESSES = "chemistry_processes"
COLLECTION_PHYSICS_PROCESSES = "physics_processes"
COLLECTION_COMPUTER_SCIENCE_PROCESSES = "computer_science_processes"
COLLECTION_BIOLOGY_PROCESSES = "biology_processes"

# Query Limits
DEFAULT_QUERY_LIMIT = 10
MAX_QUERY_LIMIT = 100

# Google Cloud Storage Configuration
GCS_BUCKET_NAME = os.getenv("GCP_AUDIO_BUCKET", "regal-scholar-453620-r7-podcast-storage")
GLMP_BUCKET_PATH = os.getenv("GLMP_BUCKET_PATH", "glmp-v2/processes")

# MCP Server Metadata
MCP_SERVER_NAME = "copernicusai-knowledge-engine"
MCP_SERVER_VERSION = "1.0.0"

