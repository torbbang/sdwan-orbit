"""Unit tests for control plane (controller/validator) onboarding."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sdwan_orbit.onboarding import DeviceOnboarder
from sdwan_orbit.models import ControllerConfig, ValidatorConfig
from sdwan_orbit.exceptions import (
    OnboardingError,
    CredentialError,
    OnboardingTimeoutError,
)


class TestOnboardControllers:
    """Test vSmart controller onboarding."""

    @pytest.fixture
    def mock_session(self):
        """Create mock ManagerSession."""
        session = Mock()
        session.endpoints = Mock()
        session.endpoints.configuration_device_inventory = Mock()
        session.get = Mock()
        return session

    @pytest.fixture
    def onboarder(self, mock_session):
        """Create DeviceOnboarder with mock session."""
        return DeviceOnboarder(mock_session, default_password="admin")

    @patch.object(DeviceOnboarder, "_get_onboarded_ips")
    @patch.object(DeviceOnboarder, "_get_device_uuid_by_ip")
    @patch.object(DeviceOnboarder, "_onboard_control_component")
    def test_onboard_controllers_success(
        self,
        mock_onboard_component,
        mock_get_uuid,
        mock_get_ips,
        onboarder,
        mock_session,
    ):
        """Test successful controller onboarding."""
        # Setup
        controllers = [
            ControllerConfig(ip="172.16.0.101", password="admin"),
            ControllerConfig(ip="172.16.0.102", password="custom"),
        ]

        mock_get_ips.return_value = []  # No devices already onboarded
        mock_onboard_component.side_effect = ["uuid-101", "uuid-102"]

        # Execute
        result = onboarder.onboard_controllers(controllers)

        # Assert
        assert result == ["uuid-101", "uuid-102"]
        assert mock_onboard_component.call_count == 2
        mock_onboard_component.assert_any_call(
            ip="172.16.0.101", password="admin", personality="vsmart"
        )
        mock_onboard_component.assert_any_call(
            ip="172.16.0.102", password="custom", personality="vsmart"
        )

    @patch.object(DeviceOnboarder, "_get_onboarded_ips")
    @patch.object(DeviceOnboarder, "_get_device_uuid_by_ip")
    def test_onboard_controllers_skip_existing(
        self, mock_get_uuid, mock_get_ips, onboarder, mock_session
    ):
        """Test skipping already onboarded controllers."""
        # Setup
        controllers = [
            ControllerConfig(ip="172.16.0.101", password="admin"),
            ControllerConfig(ip="172.16.0.102", password="admin"),
        ]

        # First controller already onboarded
        mock_get_ips.return_value = ["172.16.0.101"]
        mock_get_uuid.return_value = "existing-uuid-101"

        # Execute with skip_existing=True
        with patch.object(
            onboarder, "_onboard_control_component"
        ) as mock_onboard_component:
            mock_onboard_component.return_value = "uuid-102"
            result = onboarder.onboard_controllers(controllers, skip_existing=True)

        # Assert - only second controller onboarded
        assert result == ["existing-uuid-101", "uuid-102"]
        mock_onboard_component.assert_called_once_with(
            ip="172.16.0.102", password="admin", personality="vsmart"
        )

    @patch.object(DeviceOnboarder, "_get_onboarded_ips")
    @patch.object(DeviceOnboarder, "_onboard_control_component")
    def test_onboard_controllers_error(
        self, mock_onboard_component, mock_get_ips, onboarder, mock_session
    ):
        """Test controller onboarding with error."""
        # Setup
        controllers = [ControllerConfig(ip="172.16.0.101", password="admin")]

        mock_get_ips.return_value = []
        mock_onboard_component.side_effect = Exception("Connection failed")

        # Execute and assert
        with pytest.raises(OnboardingError) as exc_info:
            onboarder.onboard_controllers(controllers)

        assert "172.16.0.101" in str(exc_info.value)
        assert "Connection failed" in str(exc_info.value)


class TestOnboardValidators:
    """Test vBond validator onboarding."""

    @pytest.fixture
    def mock_session(self):
        """Create mock ManagerSession."""
        session = Mock()
        session.endpoints = Mock()
        session.endpoints.configuration_device_inventory = Mock()
        session.get = Mock()
        return session

    @pytest.fixture
    def onboarder(self, mock_session):
        """Create DeviceOnboarder with mock session."""
        return DeviceOnboarder(mock_session, default_password="admin")

    @patch.object(DeviceOnboarder, "_get_onboarded_ips")
    @patch.object(DeviceOnboarder, "_get_device_uuid_by_ip")
    @patch.object(DeviceOnboarder, "_onboard_control_component")
    def test_onboard_validators_success(
        self,
        mock_onboard_component,
        mock_get_uuid,
        mock_get_ips,
        onboarder,
        mock_session,
    ):
        """Test successful validator onboarding."""
        # Setup
        validators = [ValidatorConfig(ip="172.16.0.201", password="admin")]

        mock_get_ips.return_value = []
        mock_onboard_component.return_value = "uuid-201"

        # Execute
        result = onboarder.onboard_validators(validators)

        # Assert
        assert result == ["uuid-201"]
        mock_onboard_component.assert_called_once_with(
            ip="172.16.0.201", password="admin", personality="vbond"
        )


class TestWaitForOnboarding:
    """Test device onboarding wait functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create mock ManagerSession."""
        session = Mock()
        session.endpoints = Mock()
        session.endpoints.configuration_device_inventory = Mock()
        return session

    @pytest.fixture
    def onboarder(self, mock_session):
        """Create DeviceOnboarder with mock session."""
        return DeviceOnboarder(mock_session)

    @patch.object(DeviceOnboarder, "_is_device_ready")
    def test_wait_for_onboarding_already_ready(
        self, mock_is_ready, onboarder, mock_session
    ):
        """Test waiting when devices are already ready."""
        # Setup
        device_uuids = ["uuid-1", "uuid-2"]

        mock_device_details = Mock()
        mock_session.endpoints.configuration_device_inventory.get_device_details.return_value = (
            mock_device_details
        )

        mock_is_ready.return_value = True

        # Execute
        result = onboarder.wait_for_onboarding(device_uuids, timeout=60)

        # Assert
        assert result is True
        assert mock_is_ready.call_count >= 2

    def test_wait_for_onboarding_empty_list(self, onboarder, mock_session):
        """Test waiting with empty device list."""
        # Execute
        result = onboarder.wait_for_onboarding([], timeout=60)

        # Assert
        assert result is True

    @patch("time.sleep")
    @patch.object(DeviceOnboarder, "_is_device_ready")
    def test_wait_for_onboarding_timeout(
        self, mock_is_ready, mock_sleep, onboarder, mock_session
    ):
        """Test onboarding timeout."""
        # Setup
        device_uuids = ["uuid-timeout"]

        mock_device_details = Mock()
        mock_session.endpoints.configuration_device_inventory.get_device_details.return_value = (
            mock_device_details
        )

        mock_is_ready.return_value = False

        # Mock time to force timeout
        with patch("time.time") as mock_time:
            mock_time.side_effect = [0, 700]  # Start, then past timeout

            # Execute and assert
            with pytest.raises(OnboardingTimeoutError) as exc_info:
                onboarder.wait_for_onboarding(device_uuids, timeout=600)

            assert "1 device(s)" in str(exc_info.value)


class TestOnboardControlComponent:
    """Test control component onboarding helper."""

    @pytest.fixture
    def mock_session(self):
        """Create mock ManagerSession."""
        session = Mock()
        session.endpoints = Mock()
        session.endpoints.configuration_device_inventory = Mock()
        return session

    @pytest.fixture
    def onboarder(self, mock_session):
        """Create DeviceOnboarder with mock session."""
        return DeviceOnboarder(mock_session, default_password="admin")

    @patch.object(DeviceOnboarder, "_get_device_uuid_by_ip")
    def test_onboard_control_component_with_default_password(
        self, mock_get_uuid, onboarder, mock_session
    ):
        """Test onboarding with default password success."""
        # Setup
        mock_session.endpoints.configuration_device_inventory.create_device = Mock()
        mock_get_uuid.return_value = "uuid-123"

        # Execute
        result = onboarder._onboard_control_component(
            ip="172.16.0.101", password="custom", personality="vsmart"
        )

        # Assert
        assert result == "uuid-123"
        # Should try default password first
        mock_session.endpoints.configuration_device_inventory.create_device.assert_called_once()

    @patch.object(DeviceOnboarder, "_get_device_uuid_by_ip")
    def test_onboard_control_component_credential_fallback(
        self, mock_get_uuid, onboarder, mock_session
    ):
        """Test credential fallback when default fails."""
        from catalystwan.exceptions import ManagerHTTPError

        # Setup - default password fails, custom succeeds
        def create_device_side_effect(payload):
            if payload.password == "admin":
                raise ManagerHTTPError("401 Unauthorized", error_info={"code": 401})
            # Custom password succeeds
            return None

        mock_session.endpoints.configuration_device_inventory.create_device.side_effect = (
            create_device_side_effect
        )
        mock_get_uuid.return_value = "uuid-123"

        # Execute
        result = onboarder._onboard_control_component(
            ip="172.16.0.101", password="custom123", personality="vsmart"
        )

        # Assert
        assert result == "uuid-123"
        assert (
            mock_session.endpoints.configuration_device_inventory.create_device.call_count
            == 2
        )

    @patch.object(DeviceOnboarder, "_get_device_uuid_by_ip")
    def test_onboard_control_component_both_passwords_fail(
        self, mock_get_uuid, onboarder, mock_session
    ):
        """Test when both default and custom passwords fail."""
        from catalystwan.exceptions import ManagerHTTPError

        # Setup - both passwords fail
        mock_session.endpoints.configuration_device_inventory.create_device.side_effect = (
            ManagerHTTPError("401 Unauthorized", error_info={"code": 401})
        )

        # Execute and assert
        with pytest.raises(CredentialError) as exc_info:
            onboarder._onboard_control_component(
                ip="172.16.0.101", password="wrong", personality="vsmart"
            )

        assert "172.16.0.101" in str(exc_info.value)

    @patch.object(DeviceOnboarder, "_get_device_uuid_by_ip")
    def test_onboard_control_component_uuid_not_found(
        self, mock_get_uuid, onboarder, mock_session
    ):
        """Test when UUID cannot be found after onboarding."""
        # Setup
        mock_session.endpoints.configuration_device_inventory.create_device = Mock()
        mock_get_uuid.return_value = None  # UUID not found

        # Execute and assert
        with pytest.raises(OnboardingError) as exc_info:
            onboarder._onboard_control_component(
                ip="172.16.0.101", password="admin", personality="vsmart"
            )

        assert "172.16.0.101" in str(exc_info.value)
        assert "UUID not found" in str(exc_info.value)


class TestHelperMethods:
    """Test helper methods."""

    @pytest.fixture
    def mock_session(self):
        """Create mock ManagerSession."""
        session = Mock()
        session.endpoints = Mock()
        session.endpoints.configuration_device_inventory = Mock()
        session.get = Mock()
        return session

    @pytest.fixture
    def onboarder(self, mock_session):
        """Create DeviceOnboarder with mock session."""
        return DeviceOnboarder(mock_session)

    def test_is_device_ready(self, onboarder):
        """Test device ready check."""
        # Test ready device
        ready_device = {
            "reachability": "reachable",
            "certificate-status": "certinstalled",
        }
        assert onboarder._is_device_ready(ready_device) is True

        # Test not reachable
        not_reachable = {
            "reachability": "unreachable",
            "certificate-status": "certinstalled",
        }
        assert onboarder._is_device_ready(not_reachable) is False

        # Test no certificate
        no_cert = {"reachability": "reachable", "certificate-status": "pending"}
        assert onboarder._is_device_ready(no_cert) is False

    def test_get_device_uuid_by_ip(self, onboarder, mock_session):
        """Test getting device UUID by IP."""
        # Setup mock devices
        mock_device1 = Mock()
        mock_device1.device_ip = "172.16.0.101"
        mock_device1.uuid = "uuid-101"

        mock_device2 = Mock()
        mock_device2.device_ip = "172.16.0.102"
        mock_device2.uuid = "uuid-102"

        mock_device_list = [mock_device1, mock_device2]
        mock_session.endpoints.configuration_device_inventory.get_device_details.return_value = (
            mock_device_list
        )

        # Test finding existing device
        result = onboarder._get_device_uuid_by_ip("172.16.0.101")
        assert result == "uuid-101"

        # Test device not found
        result = onboarder._get_device_uuid_by_ip("172.16.0.999")
        assert result is None
