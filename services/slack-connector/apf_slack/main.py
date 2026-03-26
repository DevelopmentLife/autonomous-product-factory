from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from .config import get_settings
from .notifications import (
    stage_started_blocks, stage_complete_blocks,
    pipeline_complete_blocks, approval_required_blocks,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = get_settings()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title='APF Slack Connector', version='0.1.0', lifespan=lifespan)

    @app.post('/slack/events')
    async def slack_events(req: Request):
        return Response(content='OK', status_code=200)

    @app.post('/notify/stage-started')
    async def notify_stage_started(body: dict, req: Request):
        settings = req.app.state.settings
        if not settings.SLACK_BOT_TOKEN:
            return {'skipped': True}
        from .notifications import post_message
        await post_message(settings.SLACK_BOT_TOKEN, settings.SLACK_CHANNEL,
                            f'Stage started: {body.get("stage_name")}',
                            stage_started_blocks(body.get('pipeline_id', ''), body.get('stage_name', '')))
        return {'sent': True}

    @app.post('/notify/pipeline-complete')
    async def notify_pipeline_complete(body: dict, req: Request):
        settings = req.app.state.settings
        if not settings.SLACK_BOT_TOKEN:
            return {'skipped': True}
        from .notifications import post_message
        await post_message(settings.SLACK_BOT_TOKEN, settings.SLACK_CHANNEL,
                            'Pipeline complete!',
                            pipeline_complete_blocks(body.get('pipeline_id', ''), body.get('pr_url', '')))
        return {'sent': True}

    @app.get('/healthz')
    async def healthz():
        return {'status': 'ok', 'service': 'slack-connector'}

    return app


app = create_app()
