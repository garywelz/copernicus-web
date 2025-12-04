"""Step tracking utilities for execution monitoring"""

import time
from contextlib import asynccontextmanager
from typing import Optional
from utils.logging import structured_logger


@asynccontextmanager
async def with_step(step_name: str, job_id: str = None, **context):
    """Context manager for tracking execution steps with timing"""
    start_time = time.time()
    step_id = f"{step_name}_{int(start_time * 1000)}"
    
    structured_logger.info(f"Starting step: {step_name}", 
                          job_id=job_id, 
                          step=step_name, 
                          step_id=step_id,
                          **context)
    
    try:
        yield step_id
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        structured_logger.error(f"Step failed: {step_name}", 
                               job_id=job_id,
                               step=step_name,
                               step_id=step_id,
                               duration_ms=duration_ms,
                               error=str(e),
                               error_type=type(e).__name__,
                               **context)
        raise
    else:
        duration_ms = int((time.time() - start_time) * 1000)
        structured_logger.info(f"Step completed: {step_name}", 
                              job_id=job_id,
                              step=step_name,
                              step_id=step_id,
                              duration_ms=duration_ms,
                              **context)

