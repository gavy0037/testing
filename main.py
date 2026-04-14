from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from api.lobby_endpoint import lobby_router
from api.login_endpoint import login_router
from api.challenge_endpoint import game_router

app = FastAPI(title="Hello , test Title")
app.add_middleware(SessionMiddleware, secret_key="null-pointers-secret-key-2026")

# 1. Register the API and WebSocket routes first
# This ensures /upload and /ws/lobby are handled before static files
app.include_router(lobby_router)
app.include_router(login_router)
app.include_router(game_router)

# 2. Mount Static Files
# directory="../frontend" matches your structure where main.py 
# is in a 'backend' folder and html files are in a peer 'frontend' folder.
app.mount("/", StaticFiles(directory="../frontend", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)