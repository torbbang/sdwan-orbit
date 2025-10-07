"""Configuration backup and restore using sastre."""

import json
import logging
import os
from pathlib import Path
from typing import List, Optional
from cisco_sdwan.base.rest_api import Rest
from cisco_sdwan.tasks.implementation import BackupArgs, TaskBackup, RestoreArgs, TaskRestore
from sdwan_orbit.exceptions import BackupError, RestoreError


logger = logging.getLogger(__name__)


class ConfigurationManager:
    """Handles backup and restore of SD-WAN configurations using sastre."""

    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        port: int = 443,
        verify: bool = False,
    ):
        """Initialize ConfigurationManager.

        Args:
            url: vManage URL (with or without https://)
            username: Username for authentication
            password: Password for authentication
            port: vManage port (default: 443)
            verify: Verify SSL certificate (default: False)
        """
        self.url = url if url.startswith("http") else f"https://{url}"
        self.username = username
        self.password = password
        self.port = port
        self.verify = verify

    def backup(
        self,
        workdir: Path,
        save_running: bool = False,
        tags: Optional[List[str]] = None,
        backup_mrf: bool = True,
    ) -> bool:
        """Backup templates, policies, and config groups.

        Args:
            workdir: Directory to save backup
            save_running: Save running config (default: False)
            tags: Sastre tags to backup (default: ['all'])
            backup_mrf: Backup MRF regions/subregions if available (default: True)

        Returns:
            True if backup successful

        Raises:
            BackupError: If backup fails
        """
        if tags is None:
            tags = ["all"]

        workdir = Path(workdir)
        workdir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting backup to {workdir}")

        try:
            with Rest(
                base_url=f"{self.url}:{self.port}",
                username=self.username,
                password=self.password,
                verify=self.verify,
            ) as api:
                # Run sastre backup
                task = TaskBackup()
                task_args = BackupArgs(
                    save_running=save_running,
                    no_rollover=True,
                    workdir=str(workdir),
                    tags=tags,
                )

                logger.info("Running sastre backup...")
                task_output = task.runner(task_args, api)

                if task_output:
                    for entry in task_output:
                        logger.debug(str(entry))

                # Backup MRF regions if supported
                if backup_mrf:
                    self._backup_mrf_regions(api, workdir)

                logger.info("Backup completed successfully")
                return True

        except Exception as e:
            raise BackupError(f"Backup failed: {e}") from e

    def restore(
        self,
        workdir: Path,
        attach: bool = False,
        tags: Optional[List[str]] = None,
        restore_mrf: bool = True,
    ) -> bool:
        """Restore templates, policies, and config groups.

        Args:
            workdir: Directory containing backup
            attach: Attach templates/policies after restore (default: False)
            tags: Sastre tags to restore (default: ['all'])
            restore_mrf: Restore MRF regions/subregions if available (default: True)

        Returns:
            True if restore successful

        Raises:
            RestoreError: If restore fails
        """
        if tags is None:
            tags = ["all"]

        workdir = Path(workdir)
        if not workdir.exists():
            raise RestoreError(f"Backup directory not found: {workdir}")

        logger.info(f"Starting restore from {workdir}")

        try:
            with Rest(
                base_url=f"{self.url}:{self.port}",
                username=self.username,
                password=self.password,
                verify=self.verify,
            ) as api:
                # Restore MRF regions first if they exist
                if restore_mrf:
                    self._restore_mrf_regions(api, workdir)

                # Run sastre restore
                task = TaskRestore()
                task_args = RestoreArgs(
                    workdir=str(workdir),
                    tags=tags,
                    attach=attach,
                )

                logger.info("Running sastre restore...")
                task_output = task.runner(task_args, api)

                if task_output:
                    for entry in task_output:
                        logger.debug(str(entry))

                logger.info("Restore completed successfully")
                return True

        except Exception as e:
            raise RestoreError(f"Restore failed: {e}") from e

    def _backup_mrf_regions(self, api: Rest, workdir: Path) -> None:
        """Backup MRF regions and subregions (20.7+).

        Args:
            api: Rest API instance
            workdir: Backup directory
        """
        try:
            # Check vManage version
            version = api.server_version
            major = int(version.split(".")[0])
            minor = int(version.split(".")[1])

            if major < 20 or (major == 20 and minor < 7):
                logger.debug("vManage version < 20.7, skipping MRF backup")
                return

            logger.info("Backing up MRF regions and subregions...")

            # Get network hierarchy
            network_hierarchy = api.get("v1/network-hierarchy")

            # Filter regions and subregions
            mrf_regions = [
                region
                for region in network_hierarchy
                if region.get("data", {}).get("label") == "REGION"
            ]
            mrf_subregions = [
                region
                for region in network_hierarchy
                if region.get("data", {}).get("label") == "SUB_REGION"
            ]

            if not mrf_regions:
                logger.debug("No MRF regions found")
                return

            # Save regions
            regions_dir = workdir / "mrf" / "regions"
            regions_dir.mkdir(parents=True, exist_ok=True)

            for region in mrf_regions:
                if region["data"]["hierarchyId"]["regionId"] != 0:
                    region_data = {
                        "name": region["name"],
                        "uuid": region["uuid"],
                        "data": {
                            "parentUuid": region["data"]["parentUuid"],
                            "label": region["data"]["label"],
                            "hierarchyId": {"regionId": region["data"]["hierarchyId"]["regionId"]},
                        },
                    }

                    if "description" in region:
                        region_data["description"] = region["description"]
                    if "isSecondary" in region["data"]:
                        region_data["data"]["isSecondary"] = region["data"]["isSecondary"]

                    region_file = regions_dir / f"{region['name']}.json"
                    with open(region_file, "w") as f:
                        json.dump(region_data, f, indent=2)

            # Save subregions
            if mrf_subregions:
                subregions_dir = workdir / "mrf" / "subregions"
                subregions_dir.mkdir(parents=True, exist_ok=True)

                for subregion in mrf_subregions:
                    subregion_data = {
                        "name": subregion["name"],
                        "uuid": subregion["uuid"],
                        "data": {
                            "parentUuid": subregion["data"]["parentUuid"],
                            "label": subregion["data"]["label"],
                            "hierarchyId": {
                                "subRegionId": subregion["data"]["hierarchyId"]["subRegionId"]
                            },
                        },
                    }

                    if "description" in subregion:
                        subregion_data["description"] = subregion["description"]

                    subregion_file = subregions_dir / f"{subregion['name']}.json"
                    with open(subregion_file, "w") as f:
                        json.dump(subregion_data, f, indent=2)

            logger.info(
                f"Backed up {len(mrf_regions)} regions and {len(mrf_subregions)} subregions"
            )

        except Exception as e:
            logger.warning(f"Error backing up MRF regions: {e}")

    def _restore_mrf_regions(self, api: Rest, workdir: Path) -> None:
        """Restore MRF regions and subregions (20.7+).

        Args:
            api: Rest API instance
            workdir: Backup directory
        """
        mrf_dir = workdir / "mrf"
        if not mrf_dir.exists():
            logger.debug("No MRF backup found, skipping")
            return

        try:
            logger.info("Restoring MRF regions and subregions...")

            # Restore regions first
            regions_dir = mrf_dir / "regions"
            if regions_dir.exists():
                for region_file in sorted(regions_dir.glob("*.json")):
                    with open(region_file, "r") as f:
                        region_data = json.load(f)

                    try:
                        api.post("v1/network-hierarchy", region_data)
                        logger.debug(f"Restored region: {region_data['name']}")
                    except Exception as e:
                        logger.warning(f"Error restoring region {region_data['name']}: {e}")

            # Restore subregions
            subregions_dir = mrf_dir / "subregions"
            if subregions_dir.exists():
                for subregion_file in sorted(subregions_dir.glob("*.json")):
                    with open(subregion_file, "r") as f:
                        subregion_data = json.load(f)

                    try:
                        api.post("v1/network-hierarchy", subregion_data)
                        logger.debug(f"Restored subregion: {subregion_data['name']}")
                    except Exception as e:
                        logger.warning(f"Error restoring subregion {subregion_data['name']}: {e}")

            logger.info("MRF restore completed")

        except Exception as e:
            logger.warning(f"Error restoring MRF regions: {e}")
