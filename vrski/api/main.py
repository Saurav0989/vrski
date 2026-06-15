import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlmodel import Session as DBSession
from vrski.session.db import init_db, get_db
from vrski.api.routes import session, screen, actions, apps, setup, control

try:
    from vrski.utils.logging import configure_logging
    configure_logging()
except Exception:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("vrski.api.main")

_keepalive_task: asyncio.Task = None


async def _keepalive_loop():
    """Pings every active session's emulator every 30 s and reconnects on failure."""
    from vrski.session.manager import SessionManager, _active_drivers
    while True:
        await asyncio.sleep(30)
        for session_id, driver in list(_active_drivers.items()):
            try:
                if hasattr(driver, "is_connected") and not driver.is_connected():
                    logger.warning(f"Keep-alive: session {session_id} lost connection. Reconnecting...")
                    if hasattr(driver, "reconnect"):
                        ok = driver.reconnect()
                        if ok:
                            logger.info(f"Keep-alive: session {session_id} reconnected.")
                        else:
                            logger.error(f"Keep-alive: session {session_id} reconnect failed.")
            except Exception as e:
                logger.error(f"Keep-alive error for session {session_id}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _keepalive_task
    logger.info("Initializing database...")
    init_db()
    _keepalive_task = asyncio.create_task(_keepalive_loop())
    logger.info("Keep-alive task started.")
    yield
    if _keepalive_task:
        _keepalive_task.cancel()
        try:
            await _keepalive_task
        except asyncio.CancelledError:
            pass
    logger.info("Shutting down API server...")


app = FastAPI(
    title="VRSKI Control API",
    description="REST API for agent-native Android runtime",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(session.router, tags=["session"])
app.include_router(screen.router, tags=["screen"])
app.include_router(actions.router, tags=["actions"])
app.include_router(apps.router, tags=["apps"])
app.include_router(setup.router, tags=["setup"])
app.include_router(control.router, tags=["control"])


@app.post("/session/{id}/dismiss_popups", tags=["actions"])
def dismiss_popups_route(id: str):
    """Dismisses any common Android popups currently on screen (permission dialogs,
    update prompts, rate-app dialogs, etc.). Safe to call before any action."""
    from vrski.session.manager import SessionManager
    from vrski.playstore.auth import dismiss_popups
    driver = SessionManager.get_driver(id)
    if not driver:
        return {"success": False, "error": f"No driver for session {id}"}
    dismissed = dismiss_popups(id)
    return {"success": True, "dismissed": dismissed}


@app.get("/sessions", tags=["session"])
def list_sessions_route(db: DBSession = Depends(get_db)):
    """Lists all sessions with their bound device, status, current app, and whether a
    live driver is attached — for managing multiple concurrent sessions/devices."""
    from vrski.session.manager import SessionManager
    return {"success": True, "sessions": SessionManager.list_sessions(db)}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        loc = " -> ".join(str(loc) for loc in error.get("loc", []))
        msg = error.get("msg", "invalid value")
        errors.append(f"{loc}: {msg}")
    error_desc = "; ".join(errors)
    return JSONResponse(
        status_code=422,
        content={"success": False, "error": f"Validation error: {error_desc}"},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc)},
    )


def run():
    import uvicorn
    uvicorn.run("vrski.api.main:app", host="0.0.0.0", port=7070, reload=True)
