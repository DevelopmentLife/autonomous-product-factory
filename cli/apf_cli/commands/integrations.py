import asyncio
import click
from ..client import get_client


@click.group()
def integrations_cmd():
    'Manage APF integrations.'
    pass


@integrations_cmd.command('list')
def integrations_list():
    'List all integrations.'
    async def _list():
        async with get_client() as client:
            resp = await client.get('/api/v1/connectors')
            resp.raise_for_status()
            for c in resp.json():
                status = 'enabled' if c['enabled'] else 'disabled'
                click.echo(f"{c['type']:16} {status}")
    asyncio.run(_list())


@integrations_cmd.command('enable')
@click.argument('name')
def integrations_enable(name):
    'Enable an integration.'
    async def _enable():
        async with get_client() as client:
            resp = await client.put(f'/api/v1/connectors/{name}', json={'enabled': True})
            resp.raise_for_status()
            click.echo(f'Enabled: {name}')
    asyncio.run(_enable())


@integrations_cmd.command('disable')
@click.argument('name')
def integrations_disable(name):
    'Disable an integration.'
    async def _disable():
        async with get_client() as client:
            resp = await client.delete(f'/api/v1/connectors/{name}')
            resp.raise_for_status()
            click.echo(f'Disabled: {name}')
    asyncio.run(_disable())
