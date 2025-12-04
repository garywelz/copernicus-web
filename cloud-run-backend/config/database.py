"""Database configuration for Copernicus Podcast API"""

from google.cloud import firestore
from config.constants import GCP_PROJECT_ID
from utils.logging import structured_logger

# Initialize Firestore client
try:
    db = firestore.Client(project=GCP_PROJECT_ID, database="copernicusai")
    structured_logger.info("Firestore client initialized successfully")
except Exception as e:
    structured_logger.error("Failed to initialize Firestore client", error=str(e))
    db = None


