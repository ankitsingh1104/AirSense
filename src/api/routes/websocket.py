import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.api.services.cache import cache

router = APIRouter()
logger = logging.getLogger(__name__)

connected_clients: set[WebSocket] = set()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


async def get_cached_snapshot(app) -> list:
    redis_client = getattr(app.state, "redis", None)
    if redis_client:
        try:
            payload = await redis_client.get("globe:snapshot")
            if payload:
                return json.loads(payload) if isinstance(payload, str) else payload
        except Exception:
            pass

    payload = await cache.get("globe:snapshot")
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except Exception:
            return []
    return payload or []


@router.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        snapshot = await get_cached_snapshot(websocket.app)
        await websocket.send_json(
            {
                "type": "snapshot",
                "data": snapshot,
                "ts": _now_iso(),
            }
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.discard(websocket)
    except Exception:
        connected_clients.discard(websocket)


async def broadcast_update(app, updated_countries: list):
    """Broadcast update payload to all currently connected WebSocket clients."""
    if not connected_clients:
        return

    message = {
        "type": "update",
        "data": updated_countries,
        "count": len(updated_countries),
        "ts": _now_iso(),
    }

    dead = set()
    for ws in connected_clients.copy():
        try:
            await ws.send_json(message)
        except Exception:
            dead.add(ws)
    connected_clients.difference_update(dead)
