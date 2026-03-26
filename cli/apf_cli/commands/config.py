import click


@click.group()
def config_cmd():
    'Manage APF configuration.'
    pass


@config_cmd.command('init')
def config_init():
    'Initialize APF configuration interactively.'
    click.echo('APF Configuration Wizard')
    api_url = click.prompt('Orchestrator URL', default='http://localhost:8000')
    token = click.prompt('API Token (blank for none)', default='', hide_input=True)
    click.echo(f'APF_API_URL={api_url}')
    if token:
        click.echo(f'APF_TOKEN={token}')
    click.echo('Add these to your .env file.')


@config_cmd.command('validate')
def config_validate():
    'Validate current APF configuration.'
    from ..config_schema import get_cli_settings
    settings = get_cli_settings()
    click.echo(f'API URL: {settings.APF_API_URL}')
    click.echo(f'Token:   {"set" if settings.APF_TOKEN else "not set"}')
