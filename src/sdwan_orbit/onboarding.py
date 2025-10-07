"""Device onboarding logic for controllers, validators, and edges."""

import time
import logging
import re
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
from catalystwan.session import ManagerSession
from catalystwan.endpoints.configuration_device_inventory import DeviceCreationPayload
from catalystwan.exceptions import ManagerHTTPError
from sdwan_orbit.models import ControllerConfig, ValidatorConfig, EdgeConfig
from sdwan_orbit.exceptions import (
    OnboardingError,
    CredentialError,
    DeviceNotFoundError,
    OnboardingTimeoutError,
)


logger = logging.getLogger(__name__)


class DeviceOnboarder:
    """Handles onboarding of control plane and edge devices."""

    def __init__(
        self,
        session: ManagerSession,
        default_password: str = "admin",
        parallel_workers: int = 5,
    ):
        """Initialize DeviceOnboarder.

        Args:
            session: Active ManagerSession
            default_password: Default device password to try (default: 'admin')
            parallel_workers: Number of parallel workers for operations (default: 5)
        """
        self.session = session
        self.default_password = default_password
        self.parallel_workers = parallel_workers
        self.device_inventory = session.endpoints.configuration_device_inventory

    def onboard_controllers(
        self, controllers: List[ControllerConfig], skip_existing: bool = True
    ) -> List[str]:
        """Onboard vSmart controllers.

        Args:
            controllers: List of controller configurations
            skip_existing: Skip controllers that are already onboarded (default: True)

        Returns:
            List of device UUIDs

        Raises:
            OnboardingError: If onboarding fails
        """
        logger.info(f"Onboarding {len(controllers)} controller(s)")

        # Get already onboarded devices
        already_onboarded = self._get_onboarded_ips() if skip_existing else []

        device_uuids = []
        for i, controller in enumerate(controllers, 1):
            logger.info(f"Processing controller {i}/{len(controllers)}: {controller.ip}")

            if controller.ip in already_onboarded:
                logger.info(f"Controller {controller.ip} already onboarded, skipping")
                # Get UUID of existing device
                uuid = self._get_device_uuid_by_ip(controller.ip)
                if uuid:
                    device_uuids.append(uuid)
                continue

            try:
                uuid = self._onboard_control_component(
                    ip=controller.ip,
                    password=controller.password or self.default_password,
                    personality="vsmart",
                )
                device_uuids.append(uuid)
                logger.info(f"Successfully onboarded controller {controller.ip}")
            except Exception as e:
                raise OnboardingError(
                    f"Failed to onboard controller {controller.ip}: {e}"
                ) from e

        return device_uuids

    def onboard_validators(
        self, validators: List[ValidatorConfig], skip_existing: bool = True
    ) -> List[str]:
        """Onboard vBond validators.

        Args:
            validators: List of validator configurations
            skip_existing: Skip validators that are already onboarded (default: True)

        Returns:
            List of device UUIDs

        Raises:
            OnboardingError: If onboarding fails
        """
        logger.info(f"Onboarding {len(validators)} validator(s)")

        # Get already onboarded devices
        already_onboarded = self._get_onboarded_ips() if skip_existing else []

        device_uuids = []
        for i, validator in enumerate(validators, 1):
            logger.info(f"Processing validator {i}/{len(validators)}: {validator.ip}")

            if validator.ip in already_onboarded:
                logger.info(f"Validator {validator.ip} already onboarded, skipping")
                # Get UUID of existing device
                uuid = self._get_device_uuid_by_ip(validator.ip)
                if uuid:
                    device_uuids.append(uuid)
                continue

            try:
                uuid = self._onboard_control_component(
                    ip=validator.ip,
                    password=validator.password or self.default_password,
                    personality="vbond",
                )
                device_uuids.append(uuid)
                logger.info(f"Successfully onboarded validator {validator.ip}")
            except Exception as e:
                raise OnboardingError(
                    f"Failed to onboard validator {validator.ip}: {e}"
                ) from e

        return device_uuids

    def onboard_edges(
        self, edges: List[EdgeConfig], skip_existing: bool = True
    ) -> List[str]:
        """Onboard WAN Edge devices.

        Note: Assumes edges have already discovered vBond and are waiting in vManage.
        This method handles the vManage side: accepting devices, attaching templates, etc.

        Args:
            edges: List of edge configurations
            skip_existing: Skip edges that are already onboarded (default: True)

        Returns:
            List of device UUIDs

        Raises:
            OnboardingError: If onboarding fails
        """
        logger.info(f"Onboarding {len(edges)} edge device(s)")

        # TODO: Implement edge onboarding logic
        # This requires:
        # 1. Wait for edges to appear in device inventory
        # 2. Accept devices / generate certificates
        # 3. Attach templates or config groups
        # 4. Wait for sync complete

        logger.warning("Edge onboarding not yet implemented")
        return []

    def wait_for_onboarding(
        self, device_uuids: List[str], timeout: int = 600, poll_interval: int = 10
    ) -> bool:
        """Wait for devices to complete onboarding.

        Args:
            device_uuids: List of device UUIDs to wait for
            timeout: Maximum time to wait in seconds (default: 600)
            poll_interval: Seconds between status checks (default: 10)

        Returns:
            True if all devices are ready

        Raises:
            OnboardingTimeoutError: If devices don't come up within timeout
        """
        if not device_uuids:
            logger.info("No devices to wait for")
            return True

        logger.info(f"Waiting for {len(device_uuids)} device(s) to complete onboarding")

        start_time = time.time()
        devices_ready = set()

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                pending = len(device_uuids) - len(devices_ready)
                raise OnboardingTimeoutError(
                    f"Timeout waiting for {pending} device(s) to complete onboarding"
                )

            # Check status of each device
            for uuid in device_uuids:
                if uuid in devices_ready:
                    continue

                try:
                    device_details = self.device_inventory.get_device_details(uuid)
                    if self._is_device_ready(device_details):
                        devices_ready.add(uuid)
                        logger.info(
                            f"Device {uuid} ready ({len(devices_ready)}/{len(device_uuids)})"
                        )
                except Exception as e:
                    logger.debug(f"Error checking device {uuid}: {e}")

            # All devices ready?
            if len(devices_ready) == len(device_uuids):
                logger.info("All devices ready")
                return True

            # Log progress
            if int(elapsed) % 30 == 0:
                pending = len(device_uuids) - len(devices_ready)
                logger.info(
                    f"Waiting for {pending} device(s)... ({int(elapsed)}s elapsed)"
                )

            time.sleep(poll_interval)

    def _onboard_control_component(
        self, ip: str, password: str, personality: str
    ) -> str:
        """Onboard a single control component (controller or validator).

        Args:
            ip: Device management IP
            password: Device password (will try this and 'admin')
            personality: Device personality ('vsmart' or 'vbond')

        Returns:
            Device UUID

        Raises:
            CredentialError: If authentication fails with all passwords
            OnboardingError: If onboarding fails
        """
        # Try default password first
        try:
            logger.debug(f"Trying default credentials for {ip}")
            self.device_inventory.create_device(
                payload=DeviceCreationPayload(
                    device_ip=ip,
                    username="admin",
                    password=self.default_password,
                    generateCSR=False,
                    personality=personality,
                )
            )
        except ManagerHTTPError as e:
            # Default failed, try provided password
            logger.debug(f"Default credentials failed, trying custom password for {ip}")
            try:
                self.device_inventory.create_device(
                    payload=DeviceCreationPayload(
                        device_ip=ip,
                        username="admin",
                        password=password,
                        generateCSR=False,
                        personality=personality,
                    )
                )
            except ManagerHTTPError as e2:
                raise CredentialError(
                    f"Failed to authenticate to {ip} with default and custom passwords"
                ) from e2

        # Get device UUID
        uuid = self._get_device_uuid_by_ip(ip)
        if not uuid:
            raise OnboardingError(f"Device {ip} onboarded but UUID not found")

        return uuid

    def _get_onboarded_ips(self) -> List[str]:
        """Get list of already onboarded device IPs.

        Returns:
            List of IP addresses
        """
        ips = []
        try:
            devices = self.device_inventory.get_device_details("controllers")
            for device in devices:
                # Try to get VPN 0 IP from config
                try:
                    config_response = self.session.get(
                        f"dataservice/template/config/attached/{device.uuid}"
                    )
                    if config_response.status_code == 200:
                        config = config_response.json().get("config", "")

                        # Match IPv4 on VPN 0
                        match = re.search(
                            r"vpn 0[\s\S]+?ip\saddress\s(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})",
                            config,
                        )
                        if match:
                            ips.append(match.group(1))
                        else:
                            # Fallback to device_ip
                            if device.device_ip:
                                ips.append(device.device_ip)

                        # Match IPv6 on VPN 0
                        match = re.search(r"vpn 0[\s\S]+?ipv6\saddress\s([0-9a-fA-F:]+)", config)
                        if match:
                            ips.append(match.group(1))
                except Exception as e:
                    logger.debug(f"Error getting config for device {device.uuid}: {e}")
                    if device.device_ip:
                        ips.append(device.device_ip)
        except Exception as e:
            logger.warning(f"Error getting onboarded devices: {e}")

        return ips

    def _get_device_uuid_by_ip(self, ip: str) -> Optional[str]:
        """Get device UUID by IP address.

        Args:
            ip: Device IP address

        Returns:
            Device UUID or None if not found
        """
        try:
            devices = self.device_inventory.get_device_details("controllers")
            for device in devices:
                if device.device_ip == ip:
                    return device.uuid
        except Exception as e:
            logger.debug(f"Error finding device by IP {ip}: {e}")

        return None

    def _is_device_ready(self, device_details: Dict) -> bool:
        """Check if device is ready (reachable and certificates installed).

        Args:
            device_details: Device details from API

        Returns:
            True if device is ready
        """
        # Check reachability
        reachable = device_details.get("reachability") == "reachable"

        # Check certificate status
        cert_status = device_details.get("certificate-status")
        cert_valid = cert_status in ["certinstalled", "installed"]

        return reachable and cert_valid
