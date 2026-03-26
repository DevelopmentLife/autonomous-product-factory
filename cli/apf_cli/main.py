import click
from .commands.run import run_cmd
from .commands.status import status_cmd
from .commands.logs import logs_cmd
from .commands.artifacts import artifacts_cmd
from .commands.config import config_cmd
from .commands.auth import auth_cmd
from .commands.integrations import integrations_cmd


@click.group()
@click.version_option('0.1.0', prog_name='apf')
def cli():
    'Autonomous Product Factory CLI'
    pass


cli.add_command(run_cmd, 'run')
cli.add_command(status_cmd, 'status')
cli.add_command(logs_cmd, 'logs')
cli.add_command(artifacts_cmd, 'artifacts')
cli.add_command(config_cmd, 'config')
cli.add_command(auth_cmd, 'auth')
cli.add_command(integrations_cmd, 'integrations')


if __name__ == '__main__':
    cli()
