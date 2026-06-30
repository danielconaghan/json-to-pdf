import json
import sys
from pathlib import Path

import click

from .fonts import register_fonts
from .merger import deep_merge, load_defaults
from .renderer import render
from .styles import resolve_styles


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

    config = deep_merge(load_defaults(), user_config)
    config["_resolved_styles"] = resolve_styles(config["styles"])
    register_fonts(config.get("fonts", []), base_path=input.parent)
    render(config, str(output), base_path=str(input.parent))

    click.echo(f"Written: {output}")
