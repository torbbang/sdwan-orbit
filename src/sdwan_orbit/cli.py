"""CLI interface for ORBIT."""

import logging
import sys
from pathlib import Path
import click
from rich.console import Console
from rich.logging import RichHandler
from sdwan_orbit import Orbit
from sdwan_orbit.exceptions import OrbitError


console = Console()


def setup_logging(verbose: int) -> None:
    """Setup logging configuration.

    Args:
        verbose: Verbosity level (0=WARNING, 1=INFO, 2=DEBUG)
    """
    level = logging.WARNING
    if verbose == 1:
        level = logging.INFO
    elif verbose >= 2:
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


@click.group()
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase verbosity (-v for INFO, -vv for DEBUG)",
)
@click.version_option(version="0.1.0", prog_name="orbit")
def cli(verbose: int) -> None:
    """ORBIT - Onboarding, Registration, Bootstrap & Integration Toolkit for Cisco SD-WAN."""
    setup_logging(verbose)


@cli.command()
@click.argument("device_file", type=click.Path(exists=True, path_type=Path))
@click.option("--skip-existing/--no-skip-existing", default=True, help="Skip already onboarded devices")
@click.option("--wait/--no-wait", default=True, help="Wait for devices to be ready")
@click.option("--timeout", default=600, type=int, help="Timeout in seconds for waiting")
def onboard(device_file: Path, skip_existing: bool, wait: bool, timeout: int) -> None:
    """Onboard devices from device inventory file."""
    try:
        console.print(f"[bold]Loading device inventory from {device_file}[/bold]")

        with Orbit.from_file(device_file) as orch:
            console.print("[bold green]Connected to vManage[/bold green]")

            results = orch.onboard(
                skip_existing=skip_existing,
                wait_for_ready=wait,
                timeout=timeout,
            )

            # Display results
            console.print("\n[bold green]✓ Onboarding complete![/bold green]\n")
            console.print(f"Controllers: {len(results['controllers'])}")
            console.print(f"Validators: {len(results['validators'])}")
            console.print(f"Edges: {len(results['edges'])}")

    except OrbitError as e:
        console.print(f"[bold red]✗ Onboarding failed:[/bold red] {e}", style="red")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]✗ Unexpected error:[/bold red] {e}", style="red")
        sys.exit(1)


@cli.command()
@click.option("--manager", "-m", required=True, help="vManage URL")
@click.option("--username", "-u", required=True, help="vManage username")
@click.option("--password", "-p", required=True, help="vManage password")
@click.option("--port", default=443, type=int, help="vManage port")
@click.argument("output_dir", type=click.Path(path_type=Path))
def backup(manager: str, username: str, password: str, port: int, output_dir: Path) -> None:
    """Backup configuration to directory."""
    try:
        console.print(f"[bold]Starting backup to {output_dir}[/bold]")

        # Create minimal inventory for backup operation
        inventory_data = {
            "manager": {
                "url": manager,
                "username": username,
                "password": password,
                "port": port,
            }
        }

        with Orbit.from_dict(inventory_data) as orch:
            orch.backup(output_dir)
            console.print(f"[bold green]✓ Backup complete![/bold green] Saved to {output_dir}")

    except OrbitError as e:
        console.print(f"[bold red]✗ Backup failed:[/bold red] {e}", style="red")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]✗ Unexpected error:[/bold red] {e}", style="red")
        sys.exit(1)


@cli.command()
@click.option("--manager", "-m", required=True, help="vManage URL")
@click.option("--username", "-u", required=True, help="vManage username")
@click.option("--password", "-p", required=True, help="vManage password")
@click.option("--port", default=443, type=int, help="vManage port")
@click.option("--attach/--no-attach", default=False, help="Attach templates/policies after restore")
@click.argument("backup_dir", type=click.Path(exists=True, path_type=Path))
def restore(
    manager: str, username: str, password: str, port: int, attach: bool, backup_dir: Path
) -> None:
    """Restore configuration from backup directory."""
    try:
        console.print(f"[bold]Starting restore from {backup_dir}[/bold]")

        # Create minimal inventory for restore operation
        inventory_data = {
            "manager": {
                "url": manager,
                "username": username,
                "password": password,
                "port": port,
            }
        }

        with Orbit.from_dict(inventory_data) as orch:
            orch.restore(backup_dir, attach=attach)
            console.print(f"[bold green]✓ Restore complete![/bold green]")

    except OrbitError as e:
        console.print(f"[bold red]✗ Restore failed:[/bold red] {e}", style="red")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]✗ Unexpected error:[/bold red] {e}", style="red")
        sys.exit(1)


if __name__ == "__main__":
    cli()
