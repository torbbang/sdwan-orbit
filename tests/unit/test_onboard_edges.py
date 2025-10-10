"""Unit tests for edge device onboarding."""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from sdwan_orbit.onboarding import DeviceOnboarder
from sdwan_orbit.models import EdgeConfig
from sdwan_orbit.exceptions import (
    DeviceNotFoundError,
    OnboardingError,
    OnboardingTimeoutError,
)


class TestOnboardEdges:
    """Test edge device onboarding functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create mock ManagerSession."""
        session = Mock()
        session.endpoints = Mock()
        session.endpoints.configuration_device_inventory = Mock()
        session.get = Mock()
        session.post = Mock()
        return session

    @pytest.fixture
    def onboarder(self, mock_session):
        """Create DeviceOnboarder with mock session."""
        return DeviceOnboarder(mock_session, default_password="admin")

    def test_find_edge_by_serial_found(self, onboarder, mock_session):
        """Test finding edge device by serial number when it exists."""
        # Setup mock device list
        mock_device = Mock()
        mock_device.serial_number = "C8K-TEST-1234"
        mock_device.uuid = "edge-uuid-1234"

        mock_device_list = Mock()
        mock_device_list.__iter__ = Mock(return_value=iter([mock_device]))

        mock_session.endpoints.configuration_device_inventory.get_device_details.return_value = (
            mock_device_list
        )

        # Execute
        result = onboarder._find_edge_by_serial("C8K-TEST-1234")

        # Assert
        assert result == "edge-uuid-1234"
        mock_session.endpoints.configuration_device_inventory.get_device_details.assert_called_once_with(
            "vedges"
        )

    def test_find_edge_by_serial_not_found(self, onboarder, mock_session):
        """Test finding edge device when serial doesn't exist."""
        # Setup empty device list
        mock_device_list = Mock()
        mock_device_list.__iter__ = Mock(return_value=iter([]))

        mock_session.endpoints.configuration_device_inventory.get_device_details.return_value = (
            mock_device_list
        )

        # Execute
        result = onboarder._find_edge_by_serial("NON-EXISTENT-SERIAL")

        # Assert
        assert result is None

    def test_find_edge_by_uuid(self, onboarder, mock_session):
        """Test finding edge device using UUID instead of serial."""
        # Setup mock device
        mock_device = Mock()
        mock_device.serial_number = "C8K-OTHER-5678"
        mock_device.uuid = "edge-uuid-5678"

        mock_device_list = Mock()
        mock_device_list.__iter__ = Mock(return_value=iter([mock_device]))

        mock_session.endpoints.configuration_device_inventory.get_device_details.return_value = (
            mock_device_list
        )

        # Execute - search by UUID
        result = onboarder._find_edge_by_serial("edge-uuid-5678")

        # Assert
        assert result == "edge-uuid-5678"

    def test_onboard_edges_device_not_found(self, onboarder, mock_session):
        """Test onboarding when edge device is not in vManage inventory."""
        # Setup edge config
        edge = EdgeConfig(serial="C8K-NOT-FOUND", system_ip="10.1.0.1", site_id=1)

        # Mock device not found
        mock_device_list = Mock()
        mock_device_list.__iter__ = Mock(return_value=iter([]))
        mock_session.endpoints.configuration_device_inventory.get_device_details.return_value = (
            mock_device_list
        )

        # Execute and assert
        with pytest.raises(DeviceNotFoundError) as exc_info:
            onboarder.onboard_edges([edge])

        assert "C8K-NOT-FOUND" in str(exc_info.value)
        assert "not found in vManage inventory" in str(exc_info.value)

    def test_onboard_edges_skip_existing(self, onboarder, mock_session):
        """Test skipping already onboarded devices."""
        # Setup edge config
        edge = EdgeConfig(serial="C8K-EXISTS", system_ip="10.1.0.1", site_id=1)

        # Mock device with certificate already installed
        mock_device = Mock()
        mock_device.serial_number = "C8K-EXISTS"
        mock_device.uuid = "edge-uuid-exists"
        mock_device.cert_install_status = "Installed"

        mock_device_list = Mock()
        mock_device_list.__iter__ = Mock(return_value=iter([mock_device]))
        mock_device_list.filter = Mock(return_value=mock_device_list)
        mock_device_list.single_or_default = Mock(return_value=mock_device)

        mock_session.endpoints.configuration_device_inventory.get_device_details.return_value = (
            mock_device_list
        )

        # Execute
        result = onboarder.onboard_edges([edge], skip_existing=True)

        # Assert - device UUID returned but no certificate wait called
        assert result == ["edge-uuid-exists"]

    @patch.object(DeviceOnboarder, "_wait_for_certificate")
    def test_onboard_edges_certificate_only(
        self, mock_wait_cert, onboarder, mock_session
    ):
        """Test onboarding edge without template or config-group (certificate only)."""
        # Setup edge config without template or config_group
        edge = EdgeConfig(serial="C8K-CERT-ONLY", system_ip="10.1.0.1", site_id=1)

        # Mock device found
        mock_device = Mock()
        mock_device.serial_number = "C8K-CERT-ONLY"
        mock_device.uuid = "edge-uuid-cert"
        mock_device.cert_install_status = None

        mock_device_list = Mock()
        mock_device_list.__iter__ = Mock(return_value=iter([mock_device]))
        mock_device_list.filter = Mock(return_value=mock_device_list)
        mock_device_list.single_or_default = Mock(return_value=mock_device)

        mock_session.endpoints.configuration_device_inventory.get_device_details.return_value = (
            mock_device_list
        )

        mock_wait_cert.return_value = True

        # Execute
        result = onboarder.onboard_edges([edge], skip_existing=False)

        # Assert
        assert result == ["edge-uuid-cert"]
        mock_wait_cert.assert_called_once_with("edge-uuid-cert", timeout=300)

    @patch.object(DeviceOnboarder, "_wait_for_certificate")
    @patch.object(DeviceOnboarder, "attach_template")
    def test_onboard_edges_with_template(
        self, mock_attach_template, mock_wait_cert, onboarder, mock_session
    ):
        """Test onboarding edge with template attachment."""
        # Setup edge config with template
        edge = EdgeConfig(
            serial="C8K-WITH-TMPL",
            system_ip="10.1.0.1",
            site_id=1,
            template_name="test_template",
            values={"hostname": "edge1"},
        )

        # Mock device found
        mock_device = Mock()
        mock_device.serial_number = "C8K-WITH-TMPL"
        mock_device.uuid = "edge-uuid-tmpl"
        mock_device.cert_install_status = None

        mock_device_list = Mock()
        mock_device_list.__iter__ = Mock(return_value=iter([mock_device]))
        mock_device_list.filter = Mock(return_value=mock_device_list)
        mock_device_list.single_or_default = Mock(return_value=mock_device)

        mock_session.endpoints.configuration_device_inventory.get_device_details.return_value = (
            mock_device_list
        )

        mock_wait_cert.return_value = True
        mock_attach_template.return_value = True

        # Execute
        result = onboarder.onboard_edges([edge], skip_existing=False)

        # Assert
        assert result == ["edge-uuid-tmpl"]
        mock_wait_cert.assert_called_once()
        mock_attach_template.assert_called_once_with(
            device_uuid="edge-uuid-tmpl",
            template_name="test_template",
            variables={"system_ip": "10.1.0.1", "site_id": 1, "hostname": "edge1"},
        )

    @patch.object(DeviceOnboarder, "_wait_for_certificate")
    @patch.object(DeviceOnboarder, "attach_config_group")
    def test_onboard_edges_with_config_group(
        self, mock_attach_cg, mock_wait_cert, onboarder, mock_session
    ):
        """Test onboarding edge with config-group attachment."""
        # Setup edge config with config group
        edge = EdgeConfig(
            serial="C8K-WITH-CG",
            system_ip="10.2.0.1",
            site_id=2,
            config_group="test_config_group",
            values={"hostname": "edge2"},
        )

        # Mock device found
        mock_device = Mock()
        mock_device.serial_number = "C8K-WITH-CG"
        mock_device.uuid = "edge-uuid-cg"
        mock_device.cert_install_status = None

        mock_device_list = Mock()
        mock_device_list.__iter__ = Mock(return_value=iter([mock_device]))
        mock_device_list.filter = Mock(return_value=mock_device_list)
        mock_device_list.single_or_default = Mock(return_value=mock_device)

        mock_session.endpoints.configuration_device_inventory.get_device_details.return_value = (
            mock_device_list
        )

        mock_wait_cert.return_value = True
        mock_attach_cg.return_value = True

        # Execute
        result = onboarder.onboard_edges([edge], skip_existing=False)

        # Assert
        assert result == ["edge-uuid-cg"]
        mock_wait_cert.assert_called_once()
        mock_attach_cg.assert_called_once_with(
            device_uuid="edge-uuid-cg",
            config_group_name="test_config_group",
            variables={"system_ip": "10.2.0.1", "site_id": 2, "hostname": "edge2"},
        )

    @patch.object(DeviceOnboarder, "_wait_for_certificate")
    def test_onboard_edges_multiple_devices(
        self, mock_wait_cert, onboarder, mock_session
    ):
        """Test onboarding multiple edge devices."""
        # Setup multiple edge configs
        edges = [
            EdgeConfig(serial=f"C8K-MULTI-{i}", system_ip=f"10.{i}.0.1", site_id=i)
            for i in range(1, 4)
        ]

        # Mock devices found
        def get_device_details_side_effect(device_type):
            mock_devices = []
            for i in range(1, 4):
                mock_device = Mock()
                mock_device.serial_number = f"C8K-MULTI-{i}"
                mock_device.uuid = f"edge-uuid-{i}"
                mock_device.cert_install_status = None
                mock_devices.append(mock_device)

            mock_device_list = Mock()
            mock_device_list.__iter__ = Mock(return_value=iter(mock_devices))
            mock_device_list.filter = Mock(return_value=mock_device_list)
            # Return different devices for single_or_default based on call count
            mock_device_list.single_or_default = Mock(
                side_effect=mock_devices + mock_devices
            )
            return mock_device_list

        mock_session.endpoints.configuration_device_inventory.get_device_details.side_effect = (
            get_device_details_side_effect
        )

        mock_wait_cert.return_value = True

        # Execute
        result = onboarder.onboard_edges(edges, skip_existing=False)

        # Assert
        assert len(result) == 3
        assert result == ["edge-uuid-1", "edge-uuid-2", "edge-uuid-3"]
        assert mock_wait_cert.call_count == 3


class TestWaitForCertificate:
    """Test certificate waiting functionality."""

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

    def test_wait_for_certificate_already_installed(self, onboarder, mock_session):
        """Test when certificate is already installed."""
        # Mock device with certificate installed
        mock_device = Mock()
        mock_device.cert_install_status = "Installed"

        mock_device_list = Mock()
        mock_device_list.filter = Mock(return_value=mock_device_list)
        mock_device_list.single_or_default = Mock(return_value=mock_device)

        mock_session.endpoints.configuration_device_inventory.get_device_details.return_value = (
            mock_device_list
        )

        # Execute
        result = onboarder._wait_for_certificate("test-uuid", timeout=60)

        # Assert
        assert result is True

    @patch("time.sleep")
    def test_wait_for_certificate_timeout(self, mock_sleep, onboarder, mock_session):
        """Test certificate installation timeout."""
        # Mock device without certificate
        mock_device = Mock()
        mock_device.cert_install_status = None

        mock_device_list = Mock()
        mock_device_list.filter = Mock(return_value=mock_device_list)
        mock_device_list.single_or_default = Mock(return_value=mock_device)

        mock_session.endpoints.configuration_device_inventory.get_device_details.return_value = (
            mock_device_list
        )

        # Mock time to force timeout
        with patch("time.time") as mock_time:
            mock_time.side_effect = [0, 400]  # Start time, then past timeout

            # Execute and assert
            with pytest.raises(OnboardingTimeoutError) as exc_info:
                onboarder._wait_for_certificate("test-uuid", timeout=300)

            assert "test-uuid" in str(exc_info.value)


class TestEdgeOnboardingIntegration:
    """Integration-style tests for full edge onboarding flow."""

    @pytest.fixture
    def mock_session(self):
        """Create mock ManagerSession."""
        session = Mock()
        session.endpoints = Mock()
        session.endpoints.configuration_device_inventory = Mock()
        session.get = Mock()
        session.post = Mock()
        return session

    @pytest.fixture
    def onboarder(self, mock_session):
        """Create DeviceOnboarder with mock session."""
        return DeviceOnboarder(mock_session)

    @patch.object(DeviceOnboarder, "_wait_for_certificate")
    @patch.object(DeviceOnboarder, "attach_template")
    def test_full_edge_onboarding_workflow(
        self, mock_attach_template, mock_wait_cert, onboarder, mock_session
    ):
        """Test complete edge onboarding workflow from discovery to template attachment."""
        # Setup
        edge = EdgeConfig(
            serial="C8K-FULL-TEST",
            system_ip="10.99.0.1",
            site_id=99,
            template_name="full_test_template",
            values={"hostname": "edge99", "vpn0_inet_ip": "192.168.99.10/24"},
        )

        # Mock device discovery
        mock_device = Mock()
        mock_device.serial_number = "C8K-FULL-TEST"
        mock_device.uuid = "edge-uuid-full"
        mock_device.cert_install_status = None

        mock_device_list = Mock()
        mock_device_list.__iter__ = Mock(return_value=iter([mock_device]))
        mock_device_list.filter = Mock(return_value=mock_device_list)
        mock_device_list.single_or_default = Mock(return_value=mock_device)

        mock_session.endpoints.configuration_device_inventory.get_device_details.return_value = (
            mock_device_list
        )

        mock_wait_cert.return_value = True
        mock_attach_template.return_value = True

        # Execute
        result = onboarder.onboard_edges([edge], skip_existing=False)

        # Assert complete flow
        assert result == ["edge-uuid-full"]

        # Verify discovery was called
        mock_session.endpoints.configuration_device_inventory.get_device_details.assert_called()

        # Verify certificate wait
        mock_wait_cert.assert_called_once_with("edge-uuid-full", timeout=300)

        # Verify template attachment
        mock_attach_template.assert_called_once_with(
            device_uuid="edge-uuid-full",
            template_name="full_test_template",
            variables={
                "system_ip": "10.99.0.1",
                "site_id": 99,
                "hostname": "edge99",
                "vpn0_inet_ip": "192.168.99.10/24",
            },
        )
