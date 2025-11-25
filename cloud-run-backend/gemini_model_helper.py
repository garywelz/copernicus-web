"""
Helper module to determine the best available Gemini model with fallback chain.
Tries Gemini 3.0 first, then falls back to 2.5, then 2.0, then 1.5.
"""
from typing import Optional, List

# Model priority order (best to worst)
GEMINI_MODEL_PRIORITY = [
    'models/gemini-3.0-flash',
    'models/gemini-3.0-pro',
    'models/gemini-2.5-flash',
    'models/gemini-2.0-flash-exp',
    'models/gemini-1.5-flash',
]

# Fallback models for different contexts
PODCAST_GENERATION_MODELS = [
    'models/gemini-3.0-flash',
    'models/gemini-3.0-pro',
    'models/gemini-2.5-flash',
    'models/gemini-2.0-flash-exp',
]

RESEARCH_CONTEXT_MODELS = [
    'models/gemini-3.0-flash',
    'models/gemini-3.0-pro',
    'models/gemini-2.5-flash',
    'models/gemini-2.0-flash-exp',
]

PAPER_ANALYSIS_MODELS = [
    'models/gemini-3.0-pro',
    'models/gemini-3.0-flash',
    'models/gemini-2.5-flash',
    'gemini-pro',  # Older format
]

def get_best_available_model(model_list: Optional[List[str]] = None) -> str:
    """
    Returns the best available Gemini model from the priority list.
    This is a placeholder - actual availability should be tested at runtime.
    
    Args:
        model_list: Optional list of models to check. If None, uses PODCAST_GENERATION_MODELS.
    
    Returns:
        Model name string (e.g., 'models/gemini-3.0-flash')
    """
    models_to_check = model_list or PODCAST_GENERATION_MODELS
    
    # For now, return the first (best) model
    # In production, this should test availability and fall back
    return models_to_check[0]

def test_model_availability(client, model_name: str) -> bool:
    """
    Test if a specific Gemini model is available.
    
    Args:
        client: google-genai Client instance
        model_name: Model name to test
    
    Returns:
        True if model is available, False otherwise
    """
    try:
        # Try to generate a minimal response to test availability
        response = client.models.generate_content(
            model=model_name,
            contents="test"
        )
        return response is not None and hasattr(response, 'text')
    except Exception as e:
        error_msg = str(e).lower()
        if "not found" in error_msg or "does not exist" in error_msg:
            return False
        # Other errors might be transient, so we still return False
        return False

def get_model_with_fallback(client, preferred_models: List[str], default: str = 'models/gemini-2.5-flash') -> str:
    """
    Try models in order until one is available, with fallback to default.
    
    Args:
        client: google-genai Client instance
        preferred_models: List of model names to try in order
        default: Fallback model if none are available
    
    Returns:
        Available model name
    """
    for model_name in preferred_models:
        if test_model_availability(client, model_name):
            print(f"✅ Using Gemini model: {model_name}")
            return model_name
        else:
            print(f"⚠️  Model {model_name} not available, trying next...")
    
    print(f"⚠️  Falling back to default model: {default}")
    return default

