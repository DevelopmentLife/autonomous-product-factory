import asyncio
import click
from ..client import get_client


@click.group()
def auth_cmd():
    'Authenticate with APF.'
    pass


@auth_cmd.command('login')
@click.option('--email', prompt=True)
@click.option('--password', prompt=True, hide_input=True)
def auth_login(email, password):
    'Log in and get API token.'
    async def _login():
        async with get_client() as client:
            resp = await client.post('/api/v1/auth/login',
                                      data={'username': email, 'password': password})
            if resp.status_code == 200:
                token = resp.json()['access_token']
                click.echo(f'Token: {token}')
                click.echo('Set: export APF_TOKEN=<token>')
            else:
                click.echo(f'Login failed: {resp.status_code}', err=True)
    asyncio.run(_login())


@auth_cmd.command('whoami')
def auth_whoami():
    'Show current authenticated user.'
    async def _whoami():
        async with get_client() as client:
            resp = await client.get('/api/v1/auth/whoami')
            resp.raise_for_status()
            d = resp.json()
            click.echo(f"User: {d['email']} ({d['role']})")
    asyncio.run(_whoami())
