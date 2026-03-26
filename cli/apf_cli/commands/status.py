import asyncio, json as _json
import click
from ..client import get_client


@click.command()
@click.argument('pipeline_id', required=False)
@click.option('--json-output', is_flag=True)
def status_cmd(pipeline_id, json_output):
    'Show pipeline status.'
    asyncio.run(_status(pipeline_id, json_output))


async def _status(pipeline_id, json_output):
    async with get_client() as client:
        if pipeline_id:
            resp = await client.get(f'/api/v1/pipelines/{pipeline_id}')
        else:
            resp = await client.get('/api/v1/pipelines')
        resp.raise_for_status()
        data = resp.json()
        if json_output:
            click.echo(_json.dumps(data, indent=2))
        elif pipeline_id:
            click.echo(f"ID:     {data['id']}")
            click.echo(f"Status: {data['status']}")
            click.echo(f"Stage:  {data.get('current_stage', 'N/A')}")
        else:
            for p in data.get('items', []):
                click.echo(f"{p['id'][:8]}  {p['status']:12} {p['idea'][:60]}")
