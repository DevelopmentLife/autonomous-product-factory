import asyncio
import click
from ..client import get_client


@click.command()
@click.argument('idea')
@click.option('--from-stage', default=None, help='Resume from a specific stage')
@click.option('--json-output', is_flag=True, help='Output as JSON')
def run_cmd(idea, from_stage, json_output):
    'Run a pipeline for the given IDEA.'
    asyncio.run(_run(idea, from_stage, json_output))


async def _run(idea, from_stage, json_output):
    async with get_client() as client:
        resp = await client.post('/api/v1/pipelines', json={'idea': idea})
        resp.raise_for_status()
        data = resp.json()
        if json_output:
            import json
            click.echo(json.dumps(data, indent=2))
        else:
            click.echo(f"Pipeline started: {data['id']}")
            click.echo(f"Status: {data['status']}")
            click.echo(f"Run: apf status {data['id']}")
