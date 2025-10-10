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
    TemplateError,
    AttachmentError,
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
            DeviceNotFoundError: If edge device not found by serial number
        """
        logger.info(f"Onboarding {len(edges)} edge device(s)")

        device_uuids = []

        for i, edge in enumerate(edges, 1):
            logger.info(
                f"Processing edge {i}/{len(edges)}: serial={edge.serial}, "
                f"system_ip={edge.system_ip}, site_id={edge.site_id}"
            )

            try:
                # Find device by serial number
                device_uuid = self._find_edge_by_serial(edge.serial)

                if not device_uuid:
                    raise DeviceNotFoundError(
                        f"Edge device with serial {edge.serial} not found in vManage inventory. "
                        "Ensure the device has discovered vBond and appears in device inventory."
                    )

                # Check if already onboarded
                if skip_existing:
                    device_details = self.device_inventory.get_device_details("vedges")
                    device = device_details.filter(uuid=device_uuid).single_or_default()

                    if device and device.cert_install_status == "Installed":
                        logger.info(
                            f"Edge {edge.serial} (UUID: {device_uuid}) already has certificate installed, skipping"
                        )
                        device_uuids.append(device_uuid)
                        continue

                # Wait for certificate to be installed (device auto-installs after vBond discovery)
                self._wait_for_certificate(device_uuid, timeout=300)

                device_uuids.append(device_uuid)
                logger.info(f"Edge {edge.serial} certificate installed successfully")

                # Attach template or config group if specified
                if edge.template_name:
                    logger.info(f"Attaching template '{edge.template_name}' to edge {edge.serial}")
                    self.attach_template(
                        device_uuid=device_uuid,
                        template_name=edge.template_name,
                        variables={
                            "system_ip": edge.system_ip,
                            "site_id": edge.site_id,
                            **edge.values,
                        },
                    )
                elif edge.config_group:
                    logger.info(f"Attaching config-group '{edge.config_group}' to edge {edge.serial}")
                    self.attach_config_group(
                        device_uuid=device_uuid,
                        config_group_name=edge.config_group,
                        variables={
                            "system_ip": edge.system_ip,
                            "site_id": edge.site_id,
                            **edge.values,
                        },
                    )
                else:
                    logger.info(f"No template or config-group specified for edge {edge.serial}, skipping attachment")

            except DeviceNotFoundError:
                raise
            except Exception as e:
                raise OnboardingError(
                    f"Failed to onboard edge {edge.serial}: {e}"
                ) from e

        logger.info(f"Successfully onboarded {len(device_uuids)} edge device(s)")
        return device_uuids

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

    def _find_edge_by_serial(self, serial: str) -> Optional[str]:
        """Find edge device by serial number.

        Args:
            serial: Device serial number

        Returns:
            Device UUID or None if not found
        """
        try:
            device_list = self.device_inventory.get_device_details("vedges")
            # Filter by serial number
            for device in device_list:
                if device.serial_number == serial or device.uuid == serial:
                    logger.debug(f"Found edge device: serial={serial}, uuid={device.uuid}")
                    return device.uuid
        except Exception as e:
            logger.debug(f"Error finding edge by serial {serial}: {e}")

        return None

    def _wait_for_certificate(
        self, device_uuid: str, timeout: int = 300, poll_interval: int = 10
    ) -> bool:
        """Wait for device certificate to be installed.

        Args:
            device_uuid: Device UUID
            timeout: Maximum time to wait in seconds (default: 300)
            poll_interval: Seconds between status checks (default: 10)

        Returns:
            True if certificate is installed

        Raises:
            OnboardingTimeoutError: If certificate not installed within timeout
        """
        logger.info(f"Waiting for certificate installation on device {device_uuid}")

        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise OnboardingTimeoutError(
                    f"Timeout waiting for certificate installation on device {device_uuid}"
                )

            try:
                device_details = self.device_inventory.get_device_details("vedges")
                device = device_details.filter(uuid=device_uuid).single_or_default()

                if device and device.cert_install_status == "Installed":
                    logger.info(f"Certificate installed on device {device_uuid}")
                    return True

                # Log progress
                if int(elapsed) % 30 == 0 and elapsed > 0:
                    logger.info(
                        f"Waiting for certificate on {device_uuid}... ({int(elapsed)}s elapsed)"
                    )

            except Exception as e:
                logger.debug(f"Error checking certificate status for {device_uuid}: {e}")

            time.sleep(poll_interval)

    def attach_template(
        self, device_uuid: str, template_name: str, variables: Dict
    ) -> bool:
        """Attach device template to edge device.

        Args:
            device_uuid: Device UUID
            template_name: Name of device template to attach
            variables: Template variable values (must include system_ip, site_id, etc.)

        Returns:
            True if attachment successful

        Raises:
            TemplateError: If template not found
            AttachmentError: If attachment fails
        """
        logger.info(f"Attaching template '{template_name}' to device {device_uuid}")

        try:
            # Get template ID by name
            templates_response = self.session.get("dataservice/template/device").json()
            templates = templates_response.get("data", [])

            template_id = None
            for template in templates:
                if template.get("templateName") == template_name:
                    template_id = template.get("templateId")
                    break

            if not template_id:
                raise TemplateError(
                    f"Device template '{template_name}' not found in vManage"
                )

            logger.debug(f"Found template '{template_name}' with ID {template_id}")

            # Get device details for hostname
            device_details = self.device_inventory.get_device_details("vedges")
            device = device_details.filter(uuid=device_uuid).single_or_default()

            if not device:
                raise DeviceNotFoundError(f"Device {device_uuid} not found")

            # Build attachment payload
            # Template variables need specific naming conventions
            variables_dict = {
                "csv-status": "complete",
                "csv-deviceId": device_uuid,
                "csv-deviceIP": device.device_ip or variables.get("system_ip"),
                "csv-host-name": device.host_name or f"Edge{variables.get('site_id')}",
                "//system/host-name": device.host_name or f"Edge{variables.get('site_id')}",
                "//system/system-ip": variables.get("system_ip"),
                "//system/site-id": str(variables.get("site_id")),
                "csv-templateId": template_id,
            }

            # Add custom variables
            for key, value in variables.items():
                if key not in ["system_ip", "site_id"]:
                    variables_dict[key] = value

            attach_payload = {
                "deviceTemplateList": [
                    {
                        "templateId": template_id,
                        "device": [variables_dict],
                        "isEdited": False,
                        "isMasterEdited": False,
                    }
                ]
            }

            # Attach template
            response = self.session.post(
                "dataservice/template/device/config/attachfeature",
                json=attach_payload,
            )

            if response.status_code not in [200, 201]:
                raise AttachmentError(
                    f"Failed to attach template: {response.status_code} - {response.text}"
                )

            task_id = response.json().get("id")
            logger.info(f"Template attachment initiated, task ID: {task_id}")

            # Wait for task completion
            self._wait_for_task(task_id, timeout=600)

            logger.info(f"Template '{template_name}' attached successfully to {device_uuid}")
            return True

        except (TemplateError, AttachmentError, DeviceNotFoundError):
            raise
        except Exception as e:
            raise AttachmentError(
                f"Failed to attach template '{template_name}': {e}"
            ) from e

    def attach_config_group(
        self, device_uuid: str, config_group_name: str, variables: Dict
    ) -> bool:
        """Attach configuration group to edge device (vManage 20.12+).

        Args:
            device_uuid: Device UUID
            config_group_name: Name of configuration group to attach
            variables: Configuration group variable values

        Returns:
            True if attachment successful

        Raises:
            TemplateError: If config group not found
            AttachmentError: If attachment fails
        """
        logger.info(f"Attaching config-group '{config_group_name}' to device {device_uuid}")

        try:
            # Get configuration group ID by name
            config_groups_response = self.session.get("dataservice/v1/config-group").json()

            config_group_id = None
            for cfg_group in config_groups_response:
                if cfg_group.get("name") == config_group_name:
                    config_group_id = cfg_group.get("id")
                    break

            if not config_group_id:
                raise TemplateError(
                    f"Configuration group '{config_group_name}' not found in vManage. "
                    "Ensure vManage version is 20.12 or higher."
                )

            logger.debug(f"Found config-group '{config_group_name}' with ID {config_group_id}")

            # Build variables payload
            variables_list = []
            for key, value in variables.items():
                variables_list.append({"name": key, "value": value})

            # Associate device with config group
            associate_payload = {
                "devices": [{"id": device_uuid}]
            }

            # First, associate the device
            response = self.session.post(
                f"dataservice/v1/config-group/{config_group_id}/device/associate",
                json=associate_payload,
            )

            if response.status_code not in [200, 201]:
                raise AttachmentError(
                    f"Failed to associate device with config-group: {response.status_code} - {response.text}"
                )

            # Deploy variables if provided
            if variables_list:
                deploy_payload = {
                    "devices": [
                        {
                            "id": device_uuid,
                            "variables": variables_list
                        }
                    ]
                }

                deploy_response = self.session.post(
                    f"dataservice/v1/config-group/{config_group_id}/device/variables",
                    json=deploy_payload,
                )

                if deploy_response.status_code not in [200, 201]:
                    logger.warning(f"Failed to deploy variables: {deploy_response.text}")

            logger.info(f"Config-group '{config_group_name}' attached successfully to {device_uuid}")
            return True

        except (TemplateError, AttachmentError):
            raise
        except Exception as e:
            raise AttachmentError(
                f"Failed to attach config-group '{config_group_name}': {e}"
            ) from e

    def _wait_for_task(
        self, task_id: str, timeout: int = 600, poll_interval: int = 10
    ) -> bool:
        """Wait for vManage task to complete.

        Args:
            task_id: Task ID to monitor
            timeout: Maximum time to wait in seconds
            poll_interval: Seconds between checks

        Returns:
            True if task completed successfully

        Raises:
            AttachmentError: If task fails or times out
        """
        logger.info(f"Waiting for task {task_id} to complete")

        start_time = time.time()
        success_statuses = ["Success", "success"]

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise AttachmentError(f"Timeout waiting for task {task_id}")

            try:
                response = self.session.get(f"dataservice/device/action/status/{task_id}")
                if response.status_code == 200:
                    task_data = response.json()

                    # Check task status
                    status = task_data.get("summary", {}).get("status")
                    if status in success_statuses:
                        logger.info(f"Task {task_id} completed successfully")
                        return True
                    elif status and "fail" in status.lower():
                        raise AttachmentError(f"Task {task_id} failed: {task_data}")

                    # Log progress
                    if int(elapsed) % 30 == 0 and elapsed > 0:
                        logger.info(f"Waiting for task {task_id}... ({int(elapsed)}s elapsed)")

            except AttachmentError:
                raise
            except Exception as e:
                logger.debug(f"Error checking task status: {e}")

            time.sleep(poll_interval)
