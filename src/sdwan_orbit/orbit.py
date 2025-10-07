"""Main ORBIT orchestrator class."""

import logging
from pathlib import Path
from typing import Dict, List, Optional
from sdwan_orbit.models import DeviceInventory
from sdwan_orbit.session import SessionManager
from sdwan_orbit.onboarding import DeviceOnboarder
from sdwan_orbit.backup import ConfigurationManager
from sdwan_orbit.exceptions import OrbitError


logger = logging.getLogger(__name__)


class Orbit:
    """Main orchestrator for SD-WAN device onboarding and configuration management."""

    def __init__(self, inventory: DeviceInventory):
        """Initialize Orbit orchestrator.

        Args:
            inventory: Device inventory with manager and device configurations
        """
        self.inventory = inventory
        self.session_mgr = SessionManager(
            url=inventory.manager.url,
            username=inventory.manager.username,
            password=inventory.manager.password,
            port=inventory.manager.port,
            verify=inventory.manager.verify,
        )
        self.session = None
        self.onboarder = None
        self.config_mgr = None

    @classmethod
    def from_file(cls, path: Path) -> "Orbit":
        """Create Orbit instance from device inventory file.

        Args:
            path: Path to YAML device inventory file

        Returns:
            Orbit instance

        Raises:
            FileNotFoundError: If file doesn't exist
            ValidationError: If file is invalid
        """
        logger.info(f"Loading device inventory from {path}")
        inventory = DeviceInventory.from_yaml(Path(path))
        return cls(inventory)

    @classmethod
    def from_dict(cls, data: Dict) -> "Orbit":
        """Create Orbit instance from dictionary.

        Args:
            data: Device inventory as dictionary

        Returns:
            Orbit instance

        Raises:
            ValidationError: If data is invalid
        """
        inventory = DeviceInventory.from_dict(data)
        return cls(inventory)

    @classmethod
    def from_containerlab(cls, lab_name: str, **manager_kwargs) -> "Orbit":
        """Create Orbit instance from containerlab topology.

        Args:
            lab_name: Containerlab lab name
            **manager_kwargs: vManage connection details (url, username, password, etc.)

        Returns:
            Orbit instance

        Raises:
            NotImplementedError: Parser not yet implemented
        """
        # TODO: Implement containerlab parser
        raise NotImplementedError("Containerlab parser not yet implemented")

    def onboard(
        self, skip_existing: bool = True, wait_for_ready: bool = True, timeout: int = 600
    ) -> Dict[str, List[str]]:
        """Onboard all devices.

        Args:
            skip_existing: Skip devices that are already onboarded (default: True)
            wait_for_ready: Wait for devices to complete onboarding (default: True)
            timeout: Maximum time to wait for devices in seconds (default: 600)

        Returns:
            Dictionary with device UUIDs:
            {
                'controllers': [...],
                'validators': [...],
                'edges': [...]
            }

        Raises:
            OrbitError: If onboarding fails
        """
        logger.info(
            f"Starting onboarding: {self.inventory.control_components} control components, "
            f"{len(self.inventory.edges)} edges"
        )

        # Connect to vManage
        if not self.session:
            self.session = self.session_mgr.connect()
            self.onboarder = DeviceOnboarder(self.session)

        results = {"controllers": [], "validators": [], "edges": []}

        try:
            # Onboard controllers
            if self.inventory.controllers:
                logger.info(f"Onboarding {len(self.inventory.controllers)} controller(s)")
                controller_uuids = self.onboarder.onboard_controllers(
                    self.inventory.controllers, skip_existing=skip_existing
                )
                results["controllers"] = controller_uuids

            # Onboard validators
            if self.inventory.validators:
                logger.info(f"Onboarding {len(self.inventory.validators)} validator(s)")
                validator_uuids = self.onboarder.onboard_validators(
                    self.inventory.validators, skip_existing=skip_existing
                )
                results["validators"] = validator_uuids

            # Wait for control plane to be ready
            if wait_for_ready:
                control_uuids = results["controllers"] + results["validators"]
                if control_uuids:
                    logger.info("Waiting for control plane to be ready...")
                    self.onboarder.wait_for_onboarding(control_uuids, timeout=timeout)

            # Onboard edges
            if self.inventory.edges:
                logger.info(f"Onboarding {len(self.inventory.edges)} edge device(s)")
                edge_uuids = self.onboarder.onboard_edges(
                    self.inventory.edges, skip_existing=skip_existing
                )
                results["edges"] = edge_uuids

                # Wait for edges to be ready
                if wait_for_ready and edge_uuids:
                    logger.info("Waiting for edge devices to be ready...")
                    self.onboarder.wait_for_onboarding(edge_uuids, timeout=timeout)

            logger.info(
                f"Onboarding complete: {len(results['controllers'])} controllers, "
                f"{len(results['validators'])} validators, {len(results['edges'])} edges"
            )

            return results

        except Exception as e:
            raise OrbitError(f"Onboarding failed: {e}") from e

    def backup(self, output_dir: Path, backup_mrf: bool = True) -> bool:
        """Backup configuration to directory.

        Args:
            output_dir: Directory to save backup
            backup_mrf: Backup MRF regions if available (default: True)

        Returns:
            True if backup successful

        Raises:
            BackupError: If backup fails
        """
        logger.info(f"Starting backup to {output_dir}")

        if not self.config_mgr:
            self.config_mgr = ConfigurationManager(
                url=self.inventory.manager.url,
                username=self.inventory.manager.username,
                password=self.inventory.manager.password,
                port=self.inventory.manager.port,
                verify=self.inventory.manager.verify,
            )

        return self.config_mgr.backup(Path(output_dir), backup_mrf=backup_mrf)

    def restore(self, backup_dir: Path, attach: bool = False, restore_mrf: bool = True) -> bool:
        """Restore configuration from backup.

        Args:
            backup_dir: Directory containing backup
            attach: Attach templates/policies after restore (default: False)
            restore_mrf: Restore MRF regions if available (default: True)

        Returns:
            True if restore successful

        Raises:
            RestoreError: If restore fails
        """
        logger.info(f"Starting restore from {backup_dir}")

        if not self.config_mgr:
            self.config_mgr = ConfigurationManager(
                url=self.inventory.manager.url,
                username=self.inventory.manager.username,
                password=self.inventory.manager.password,
                port=self.inventory.manager.port,
                verify=self.inventory.manager.verify,
            )

        return self.config_mgr.restore(Path(backup_dir), attach=attach, restore_mrf=restore_mrf)

    def cleanup(self) -> None:
        """Close connections and cleanup resources."""
        logger.info("Cleaning up...")
        if self.session_mgr:
            self.session_mgr.close()
        self.session = None
        self.onboarder = None
        self.config_mgr = None

    def __enter__(self) -> "Orbit":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.cleanup()
