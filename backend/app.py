from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from nodes.state import reset_database

from nodes import router_nodes
from auth import router_user
from websockets_nodes import router_ws_nodes


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await reset_database()
    yield


app = FastAPI(title="Bully Cluster",lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router_user.router)
app.include_router(router_nodes.router)
app.include_router(router_ws_nodes.router)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")