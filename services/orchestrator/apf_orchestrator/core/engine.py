"""PipelineEngine - core APF execution engine."""
from __future__ import annotations
import asyncio, uuid
from datetime import datetime
from typing import Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from ..db import Pipeline, Stage
from .dag import PIPELINE_STAGES, PipelineDAG


class PipelineEngine:
    def __init__(self, settings, db_engine, redis_client=None):
        self.settings = settings
        self.db_engine = db_engine
        self.session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
        self.redis = redis_client
        self.dag = PipelineDAG()
        self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_PIPELINES)

    async def create_and_start(self, idea, config, user_id=None):
        pipeline_id = str(uuid.uuid4())
        async with self.session_factory() as session:
            session.add(Pipeline(
                id=pipeline_id, idea=idea, status="running",
                config=config, created_at=datetime.utcnow(), updated_at=datetime.utcnow()))
            for sn in PIPELINE_STAGES:
                session.add(Stage(id=str(uuid.uuid4()), pipeline_id=pipeline_id,
                                  stage_name=sn, status="pending", retry_count=0))
            await session.commit()
        asyncio.create_task(self._run_pipeline(pipeline_id, idea, config))
        return pipeline_id

    async def handle_stage_complete(self, pipeline_id, stage_id, stage_name, artifact_url, artifact_hash):
        async with self.session_factory() as s:
            r = await s.execute(select(Stage).where(Stage.id == stage_id))
            st = r.scalar_one_or_none()
            if st:
                st.status = "complete"; st.completed_at = datetime.utcnow()
            await s.execute(update(Pipeline).where(Pipeline.id == pipeline_id)
                            .values(current_stage=stage_name, updated_at=datetime.utcnow()))
            await s.commit()

    async def handle_stage_failed(self, pipeline_id, stage_id, stage_name, error, retry_count):
        if retry_count < 3:
            async with self.session_factory() as s:
                r = await s.execute(select(Stage).where(Stage.id == stage_id))
                st = r.scalar_one_or_none()
                if st:
                    st.status = "pending"; st.retry_count = retry_count + 1; st.error_message = error
                await s.commit()
        else:
            await self._fail_pipeline(pipeline_id, f"Stage {stage_name} failed after 3 retries: {error}")

    async def cancel(self, pipeline_id):
        await self._set_status(pipeline_id, "cancelled")

    async def approve_stage(self, pipeline_id, stage_id, approved, approved_by):
        async with self.session_factory() as s:
            r = await s.execute(select(Stage).where(Stage.id == stage_id))
            st = r.scalar_one_or_none()
            if st:
                st.status = "approved" if approved else "rejected"; st.approved_by = approved_by
            await s.commit()

    async def _run_pipeline(self, pipeline_id, idea, config):
        async with self._semaphore:
            try:
                completed, running, skipped = set(), set(), set()
                while True:
                    async with self.session_factory() as s:
                        r = await s.execute(select(Stage).where(Stage.pipeline_id == pipeline_id))
                        stages = r.scalars().all()
                    for st in stages:
                        if st.status == "complete":
                            completed.add(st.stage_name); running.discard(st.stage_name)
                        elif st.status == "running": running.add(st.stage_name)
                        elif st.status == "skipped": skipped.add(st.stage_name)
                    async with self.session_factory() as s:
                        r = await s.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
                        p = r.scalar_one_or_none()
                        if p and p.status in ("cancelled", "failed"): break
                    if {"devops", "readme"}.issubset(completed | skipped):
                        await self._complete_pipeline(pipeline_id); break
                    ready = self.dag.get_ready_stages(completed, running, skipped)
                    for sn in ready:
                        running.add(sn)
                        asyncio.create_task(self._dispatch_stage(pipeline_id, sn, idea, config, {}))
                    await asyncio.sleep(2)
            except Exception as exc:
                await self._fail_pipeline(pipeline_id, str(exc))

    async def _dispatch_stage(self, pipeline_id, stage_name, idea, config, prior_artifacts):
        async with self.session_factory() as s:
            r = await s.execute(select(Stage).where(
                Stage.pipeline_id == pipeline_id, Stage.stage_name == stage_name))
            st = r.scalar_one_or_none()
            if not st: return
            st.status = "running"; st.started_at = datetime.utcnow(); stage_id = st.id
            await s.commit()
        if self.redis:
            from ..events import StageDispatchEvent
            ev = StageDispatchEvent(pipeline_id=pipeline_id, stage_id=stage_id,
                                    stage_name=stage_name, idea=idea, config=config,
                                    prior_artifacts=prior_artifacts)
            await self.redis.xadd("apf:stage:dispatch", {"data": ev.model_dump_json()})

    async def _complete_pipeline(self, pipeline_id):
        await self._set_status(pipeline_id, "complete")

    async def _fail_pipeline(self, pipeline_id, reason):
        await self._set_status(pipeline_id, "failed")

    async def _set_status(self, pipeline_id, status):
        async with self.session_factory() as s:
            await s.execute(update(Pipeline).where(Pipeline.id == pipeline_id)
                            .values(status=status, updated_at=datetime.utcnow()))
            await s.commit()
