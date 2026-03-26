import click


@click.group()
def artifacts_cmd():
    'Manage pipeline artifacts.'
    pass


@artifacts_cmd.command('list')
@click.argument('pipeline_id')
def artifacts_list(pipeline_id):
    'List artifacts for a pipeline.'
    import asyncio, json
    from ..client import get_client
    async def _list():
        async with get_client() as client:
            resp = await client.get(f'/api/v1/pipelines/{pipeline_id}/artifacts')
            resp.raise_for_status()
            for a in resp.json():
                click.echo(f"{a['stage_name']:16} v{a['version']} {a['artifact_id'][:12]}...")
    asyncio.run(_list())
