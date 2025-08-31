import functions_framework
import json
import logging
import os
from datetime import datetime
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cloud Run backend URL
BACKEND_URL = "https://copernicus-podcast-api-204731194849.us-central1.run.app"

@functions_framework.http
def generate_podcast(request):
    """HTTP Cloud Function to handle podcast generation requests."""
    
    # Set CORS headers
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
    }
    
    try:
        logger.info("🔥🔥🔥 CLOUD FUNCTION CALLED 🔥🔥🔥")
        logger.info(f"🔥🔥🔥 TIMESTAMP: {datetime.utcnow().isoformat()}")
        logger.info(f"🔥🔥🔥 METHOD: {request.method}")
        logger.info(f"🔥🔥🔥 URL: {request.url}")
        
        if request.method != 'POST':
            return (json.dumps({'error': 'Method not allowed'}), 405, headers)
        
        # Parse request data
        try:
            request_json = request.get_json()
            logger.info(f"🔥🔥🔥 REQUEST DATA: {json.dumps(request_json, indent=2)}")
        except json.JSONDecodeError as json_error:
            logger.error(f"🔥🔥🔥 REQUEST JSON PARSE ERROR: {json_error}")
            return (json.dumps({
                'error': 'Invalid JSON in request',
                'message': 'The request contains malformed JSON data',
                'details': str(json_error)
            }), 400, headers)
        
        if not request_json:
            return (json.dumps({'error': 'No JSON data provided'}), 400, headers)
        
        # Extract form fields
        subject = request_json.get('subject')
        category = request_json.get('category')  # Add category extraction
        duration = request_json.get('duration')
        speakers = request_json.get('speakers')
        difficulty = request_json.get('difficulty')
        additional_notes = request_json.get('additional_notes', '')
        source_links = request_json.get('source_links', [])
        
        # Validate required fields
        if not all([subject, duration, speakers, difficulty]):
            return (json.dumps({'error': 'Missing required fields'}), 400, headers)
        
        # Generate job ID
        job_id = f"job_{int(datetime.utcnow().timestamp() * 1000)}_{os.urandom(4).hex()}"
        logger.info(f"🔥🔥🔥 GENERATED JOB ID: {job_id}")
        
        # Prepare data for Cloud Run backend
        backend_data = {
            'subject': subject,
            'category': category,  # Add category to backend data
            'duration': duration,
            'speakers': speakers,
            'difficulty': difficulty,
            'additional_notes': additional_notes,
            'source_links': source_links,
            'timestamp': int(datetime.utcnow().timestamp() * 1000)
        }
        
        logger.info(f"🔥🔥🔥 SUBMITTING TO CLOUD RUN: {BACKEND_URL}/generate-podcast")
        
        # Convert legacy format to new format for the main endpoint
        converted_data = {
            'topic': subject,
            'category': category or 'Computer Science',
            'expertise_level': {'General': 'beginner', 'Intermediate': 'intermediate', 'Advanced': 'expert', 'Expert': 'expert'}.get(difficulty, 'intermediate'),
            'format_type': {'interview': 'interview', 'monologue': 'monologue', 'discussion': 'interview'}.get(speakers, 'interview'),
            'duration': f"{duration} minutes" if duration.isdigit() else duration,
            'voice_style': 'professional',
            'focus_areas': [additional_notes] if additional_notes else ['methodology', 'implications', 'future_research'],
            'include_citations': True,
            'paradigm_shift_analysis': True
        }
        
        # Submit to Cloud Run backend (using main endpoint)
        try:
            response = requests.post(
                f"{BACKEND_URL}/generate-podcast",
                json=converted_data,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'CopernicusAI-CloudFunction/1.0'
                },
                timeout=60
            )
            
            logger.info(f"🔥🔥🔥 CLOUD RUN RESPONSE STATUS: {response.status_code}")
            logger.info(f"🔥🔥🔥 CLOUD RUN RESPONSE: {response.text}")
            
            if response.status_code == 200:
                try:
                    backend_result = response.json()
                    logger.info(f"🔥🔥🔥 BACKEND JOB ID: {backend_result.get('job_id')}")
                    
                    return (json.dumps({
                        'success': True,
                        'jobId': job_id,
                        'backendJobId': backend_result.get('job_id'),
                        'message': 'Podcast generation job created successfully',
                        'estimatedCompletionTime': '5-10 minutes'
                    }), 200, headers)
                except json.JSONDecodeError as json_error:
                    logger.error(f"🔥🔥🔥 JSON PARSE ERROR: {json_error}")
                    logger.error(f"🔥🔥🔥 RESPONSE TEXT: {response.text}")
                    return (json.dumps({
                        'error': 'Backend returned invalid JSON',
                        'message': 'The backend service returned malformed data',
                        'details': str(json_error)
                    }), 500, headers)
            else:
                logger.error(f"🔥🔥🔥 CLOUD RUN ERROR: {response.status_code} - {response.text}")
                return (json.dumps({
                    'error': f'Backend error: {response.status_code}',
                    'details': response.text
                }), 500, headers)
                
        except requests.exceptions.Timeout:
            logger.error("🔥🔥🔥 CLOUD RUN TIMEOUT")
            return (json.dumps({
                'error': 'Backend request timed out',
                'message': 'The backend is taking too long to respond'
            }), 504, headers)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"🔥🔥🔥 CLOUD RUN REQUEST ERROR: {e}")
            return (json.dumps({
                'error': 'Backend connection failed',
                'message': str(e)
            }), 503, headers)
            
    except Exception as e:
        logger.error(f"🔥🔥🔥 FUNCTION ERROR: {e}")
        return (json.dumps({
            'error': 'Internal server error',
            'message': str(e)
        }), 500, headers)

@functions_framework.http
def health_check(request):
    """Health check endpoint."""
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
    }
    
    return (json.dumps({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'copernicus-podcast-function'
    }), 200, headers)
