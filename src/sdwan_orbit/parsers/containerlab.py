"""Parser for containerlab topology information."""

import json
import subprocess
import logging
from typing import Dict, Any
from sdwan_orbit.models import DeviceInventory
from sdwan_orbit.exceptions import ValidationError


logger = logging.getLogger(__name__)


def parse_containerlab(
    lab_name: str,
    manager_url: str,
    manager_username: str = "admin",
    manager_password: str = "admin",
    manager_port: int = 443,
) -> DeviceInventory:
    """Parse containerlab topology and create device inventory.

    Args:
        lab_name: Containerlab lab name
        manager_url: vManage URL
        manager_username: vManage username (default: 'admin')
        manager_password: vManage password (default: 'admin')
        manager_port: vManage port (default: 443)

    Returns:
        DeviceInventory instance

    Raises:
        ValidationError: If parsing fails
        subprocess.CalledProcessError: If containerlab inspect fails
    """
    logger.info(f"Parsing containerlab topology: {lab_name}")

    # TODO: Implement containerlab parsing
    # 1. Run: containerlab inspect --name <lab_name> --format json
    # 2. Extract device information from JSON
    # 3. Map to DeviceInventory structure
    # 4. Identify controllers, validators, edges based on node labels/kind

    raise NotImplementedError(
        "Containerlab parser not yet implemented. "
        "Use manual device inventory file instead."
    )


def _run_containerlab_inspect(lab_name: str) -> Dict[str, Any]:
    """Run containerlab inspect command and return parsed JSON.

    Args:
        lab_name: Lab name

    Returns:
        Parsed JSON output

    Raises:
        subprocess.CalledProcessError: If command fails
        json.JSONDecodeError: If output is not valid JSON
    """
    cmd = ["containerlab", "inspect", "--name", lab_name, "--format", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)
