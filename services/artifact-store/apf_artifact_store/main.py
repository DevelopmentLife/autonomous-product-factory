from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .store import ArtifactStore
from .api.artifacts import router as artifacts_router
from .api.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    store = ArtifactStore(settings.LOCAL_STORAGE_PATH)
    await store.initialize()
    app.state.store = store
    app.state.settings = settings
    yield


def create_app() -> FastAPI:
    app = FastAPI(title='APF Artifact Store', version='0.1.0', lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])
    app.include_router(health_router)
    app.include_router(artifacts_router)
    return app


app = create_app()
