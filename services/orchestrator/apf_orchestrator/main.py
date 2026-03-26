from contextlib import asynccontextmanager
import uuid
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select
from .config import get_settings
from .db import make_engine, init_db, User
from .core.engine import PipelineEngine
from .core.auth import hash_password
from .api import health, auth, pipelines, stages, connectors, websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine = make_engine(settings.DATABASE_URL)
    await init_db(engine)
    sf = async_sessionmaker(engine, expire_on_commit=False)
    app.state.db_engine = engine
    app.state.session_factory = sf
    app.state.pipeline_engine = PipelineEngine(settings, engine)
    async with sf() as s:
        result = await s.execute(select(User).where(User.email == 'admin@apf.local'))
        if not result.scalar_one_or_none():
            s.add(User(id=str(uuid.uuid4()), email='admin@apf.local',
                       hashed_password=hash_password(settings.APF_ADMIN_PASSWORD),
                       role='admin', is_active=True, created_at=datetime.utcnow()))
            await s.commit()
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title='APF Orchestrator', version='0.1.0', lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS,
                       allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(pipelines.router)
    app.include_router(stages.router)
    app.include_router(connectors.router)
    app.include_router(websocket.router)
    return app


app = create_app()
