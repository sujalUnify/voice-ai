import asyncio
import logging 

logger = logging.getLogger(__name__)

def reap(task: asyncio.Task): 
    try:
        if not task.cancelled(): 
            exc = task.exception() 
            if exc: 
                logger.warning("Cancelled task ended with: %r", exc) 
    except Exception as e: 
        logger.exception("An Unexpected exception ocuured in fire and forget function.")