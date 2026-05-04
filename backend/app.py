import sys

from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from nodes import reset_database

from nodes import router_nodes
from auth import router_user
from websockets_nodes import router_ws_nodes
from nodes.node_process import *

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from auth.limiter import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await reset_database()
    yield

sys.path.append("")

app = FastAPI(title="Bully Cluster",lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

origins = [
    "http://localhost:5173",
    "http://localhost"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router_user.router)
app.include_router(router_nodes.router)
app.include_router(router_ws_nodes.router)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")