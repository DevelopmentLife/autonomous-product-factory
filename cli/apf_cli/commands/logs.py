import asyncio, json
import click
from ..client import get_client


@click.command()
@click.argument('pipeline_id')
@click.argument('stage', required=False)
def logs_cmd(pipeline_id, stage):
    'Tail logs for a pipeline.'
    asyncio.run(_logs(pipeline_id, stage))


async def _logs(pipeline_id, stage):
    async with get_client() as client:
        url = f'/api/v1/pipelines/{pipeline_id}/stages'
        resp = await client.get(url)
        resp.raise_for_status()
        click.echo(json.dumps(resp.json(), indent=2))
