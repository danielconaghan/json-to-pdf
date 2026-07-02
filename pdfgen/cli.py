import json
import sys
from pathlib import Path

import click

from .engine import render_pdf


@click.command()
@click.argument("input", type=click.Path(exists=True, path_type=Path))
@click.argument("output", type=click.Path(path_type=Path))
def main(input, output):
    """Render a JSON document config to PDF."""
    try:
        user_config = json.loads(input.read_text())
    except json.JSONDecodeError as e:
        click.echo(f"Error: invalid JSON in {input}: {e}", err=True)
        sys.exit(1)

    output.write_bytes(render_pdf(user_config, base_path=input.parent))
    click.echo(f"Written: {output}")
