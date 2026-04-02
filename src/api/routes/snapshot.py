import logging
from fastapi import APIRouter
from src.api.services.cache import cache

router = APIRouter()
logger = logging.getLogger(__name__)

# Cache key for snapshot data
SNAPSHOT_CACHE_KEY = "globe:snapshot"

@router.get("/globe/snapshot")
async def get_globe_snapshot():
    """
    Return pre-built globe snapshot from cache.
    On first call, returns empty array; scheduler populates on startup.
    """
    
    # Try to get from cache
    try:
        cached = await cache.get(SNAPSHOT_CACHE_KEY)
        if cached:
            logger.debug("Returning cached globe snapshot with %d countries", len(cached) if isinstance(cached, list) else 0)
            return cached if cached else []
    except Exception as e:
        logger.debug(f"Cache retrieval error: {e}")
    
    # Fallback: return empty array (scheduler will populate)
    logger.warning("Snapshot not found in cache; returning empty array")
    return []



