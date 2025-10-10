"""Unit tests for template attachment functionality."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from sdwan_orbit.onboarding import DeviceOnboarder
from sdwan_orbit.exceptions import (
    TemplateError,
    AttachmentError,
    DeviceNotFoundError,
)


class TestAttachTemplate:
    """Test device template attachment."""

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

    @patch.object(DeviceOnboarder, "_wait_for_task")
    def test_attach_template_success(self, mock_wait_task, onboarder, mock_session):
        """Test successful template attachment."""
        # Mock template list response
        templates_response = {
            "data": [
                {"templateName": "test_template", "templateId": "template-123"},
                {"templateName": "other_template", "templateId": "template-456"},
            ]
        }
        mock_session.get.return_value.json.return_value = templates_response

        # Mock device details
        mock_device = Mock()
        mock_device.uuid = "device-uuid-123"
        mock_device.device_ip = "10.1.0.1"
        mock_device.host_name = "Edge1"

        mock_device_list = Mock()
        mock_device_list.filter.return_value = mock_device_list
        mock_device_list.single_or_default.return_value = mock_device

        mock_session.endpoints.configuration_device_inventory.get_device_details.return_value = (
            mock_device_list
        )

        # Mock template attachment response
        attach_response = Mock()
        attach_response.status_code = 200
        attach_response.json.return_value = {"id": "task-123"}
        mock_session.post.return_value = attach_response

        mock_wait_task.return_value = True

        # Execute
        variables = {"system_ip": "10.1.0.1", "site_id": 1, "hostname": "Edge1"}
        result = onboarder.attach_template(
            device_uuid="device-uuid-123",
            template_name="test_template",
            variables=variables,
        )

        # Assert
        assert result is True
        mock_session.get.assert_called_once_with("dataservice/template/device")
        mock_session.post.assert_called_once()

        # Verify payload structure
        call_args = mock_session.post.call_args
        assert call_args[0][0] == "dataservice/template/device/config/attachfeature"
        payload = call_args[1]["json"]
        assert payload["deviceTemplateList"][0]["templateId"] == "template-123"
        assert payload["deviceTemplateList"][0]["device"][0]["csv-deviceId"] == "device-uuid-123"

        mock_wait_task.assert_called_once_with("task-123", timeout=600)

    def test_attach_template_not_found(self, onboarder, mock_session):
        """Test template attachment when template doesn't exist."""
        # Mock template list without the target template
        templates_response = {
            "data": [
                {"templateName": "other_template", "templateId": "template-456"},
            ]
        }
        mock_session.get.return_value.json.return_value = templates_response

        # Execute and assert
        with pytest.raises(TemplateError) as exc_info:
            onboarder.attach_template(
                device_uuid="device-uuid-123",
                template_name="nonexistent_template",
                variables={"system_ip": "10.1.0.1", "site_id": 1},
            )

        assert "nonexistent_template" in str(exc_info.value)
        assert "not found" in str(exc_info.value)

    def test_attach_template_device_not_found(self, onboarder, mock_session):
        """Test template attachment when device UUID not found."""
        # Mock template list
        templates_response = {
            "data": [
                {"templateName": "test_template", "templateId": "template-123"},
            ]
        }
        mock_session.get.return_value.json.return_value = templates_response

        # Mock device not found
        mock_device_list = Mock()
        mock_device_list.filter.return_value = mock_device_list
        mock_device_list.single_or_default.return_value = None

        mock_session.endpoints.configuration_device_inventory.get_device_details.return_value = (
            mock_device_list
        )

        # Execute and assert
        with pytest.raises(DeviceNotFoundError) as exc_info:
            onboarder.attach_template(
                device_uuid="nonexistent-uuid",
                template_name="test_template",
                variables={"system_ip": "10.1.0.1", "site_id": 1},
            )

        assert "nonexistent-uuid" in str(exc_info.value)

    @patch.object(DeviceOnboarder, "_wait_for_task")
    def test_attach_template_with_custom_variables(
        self, mock_wait_task, onboarder, mock_session
    ):
        """Test template attachment with custom variables."""
        # Mock template list
        templates_response = {
            "data": [
                {"templateName": "advanced_template", "templateId": "template-789"},
            ]
        }
        mock_session.get.return_value.json.return_value = templates_response

        # Mock device
        mock_device = Mock()
        mock_device.uuid = "device-uuid-456"
        mock_device.device_ip = "10.2.0.1"
        mock_device.host_name = "Edge2"

        mock_device_list = Mock()
        mock_device_list.filter.return_value = mock_device_list
        mock_device_list.single_or_default.return_value = mock_device

        mock_session.endpoints.configuration_device_inventory.get_device_details.return_value = (
            mock_device_list
        )

        # Mock successful attachment
        attach_response = Mock()
        attach_response.status_code = 200
        attach_response.json.return_value = {"id": "task-456"}
        mock_session.post.return_value = attach_response

        mock_wait_task.return_value = True

        # Execute with custom variables
        variables = {
            "system_ip": "10.2.0.1",
            "site_id": 2,
            "vpn0_inet_ip": "192.168.2.10/24",
            "vpn0_mpls_ip": "10.10.2.10/24",
            "/0/GigabitEthernet1/interface/ip/address": "172.16.1.2/24",
        }
        result = onboarder.attach_template(
            device_uuid="device-uuid-456",
            template_name="advanced_template",
            variables=variables,
        )

        # Assert
        assert result is True

        # Verify custom variables are included in payload
        call_args = mock_session.post.call_args
        payload = call_args[1]["json"]
        device_vars = payload["deviceTemplateList"][0]["device"][0]

        assert device_vars["vpn0_inet_ip"] == "192.168.2.10/24"
        assert device_vars["vpn0_mpls_ip"] == "10.10.2.10/24"
        assert (
            device_vars["/0/GigabitEthernet1/interface/ip/address"] == "172.16.1.2/24"
        )

    def test_attach_template_http_error(self, onboarder, mock_session):
        """Test template attachment when HTTP request fails."""
        # Mock template list
        templates_response = {
            "data": [
                {"templateName": "test_template", "templateId": "template-123"},
            ]
        }
        mock_session.get.return_value.json.return_value = templates_response

        # Mock device
        mock_device = Mock()
        mock_device.uuid = "device-uuid-123"
        mock_device.device_ip = "10.1.0.1"
        mock_device.host_name = "Edge1"

        mock_device_list = Mock()
        mock_device_list.filter.return_value = mock_device_list
        mock_device_list.single_or_default.return_value = mock_device

        mock_session.endpoints.configuration_device_inventory.get_device_details.return_value = (
            mock_device_list
        )

        # Mock HTTP error
        attach_response = Mock()
        attach_response.status_code = 500
        attach_response.text = "Internal Server Error"
        mock_session.post.return_value = attach_response

        # Execute and assert
        with pytest.raises(AttachmentError) as exc_info:
            onboarder.attach_template(
                device_uuid="device-uuid-123",
                template_name="test_template",
                variables={"system_ip": "10.1.0.1", "site_id": 1},
            )

        assert "500" in str(exc_info.value)


class TestAttachConfigGroup:
    """Test configuration group attachment."""

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

    def test_attach_config_group_success(self, onboarder, mock_session):
        """Test successful config-group attachment."""
        # Mock config-group list
        config_groups_response = [
            {"name": "test_config_group", "id": "cg-123"},
            {"name": "other_config_group", "id": "cg-456"},
        ]
        mock_session.get.return_value.json.return_value = config_groups_response

        # Mock successful association
        associate_response = Mock()
        associate_response.status_code = 200
        mock_session.post.return_value = associate_response

        # Execute
        variables = {"system_ip": "10.1.0.1", "site_id": 1, "hostname": "Edge1"}
        result = onboarder.attach_config_group(
            device_uuid="device-uuid-123",
            config_group_name="test_config_group",
            variables=variables,
        )

        # Assert
        assert result is True
        mock_session.get.assert_called_once_with("dataservice/v1/config-group")

        # Verify association and variable deployment calls
        assert mock_session.post.call_count == 2  # Associate + deploy variables

    def test_attach_config_group_not_found(self, onboarder, mock_session):
        """Test config-group attachment when config-group doesn't exist."""
        # Mock config-group list without target
        config_groups_response = [
            {"name": "other_config_group", "id": "cg-456"},
        ]
        mock_session.get.return_value.json.return_value = config_groups_response

        # Execute and assert
        with pytest.raises(TemplateError) as exc_info:
            onboarder.attach_config_group(
                device_uuid="device-uuid-123",
                config_group_name="nonexistent_group",
                variables={"system_ip": "10.1.0.1", "site_id": 1},
            )

        assert "nonexistent_group" in str(exc_info.value)
        assert "not found" in str(exc_info.value)
        assert "20.12" in str(exc_info.value)  # Version hint

    def test_attach_config_group_without_variables(self, onboarder, mock_session):
        """Test config-group attachment without variables (empty dict)."""
        # Mock config-group list
        config_groups_response = [
            {"name": "test_config_group", "id": "cg-123"},
        ]
        mock_session.get.return_value.json.return_value = config_groups_response

        # Mock successful association
        associate_response = Mock()
        associate_response.status_code = 200
        mock_session.post.return_value = associate_response

        # Execute with empty variables
        result = onboarder.attach_config_group(
            device_uuid="device-uuid-123",
            config_group_name="test_config_group",
            variables={},
        )

        # Assert
        assert result is True
        # Only association call, no variable deployment
        assert mock_session.post.call_count == 1

    def test_attach_config_group_association_failure(self, onboarder, mock_session):
        """Test config-group attachment when association fails."""
        # Mock config-group list
        config_groups_response = [
            {"name": "test_config_group", "id": "cg-123"},
        ]
        mock_session.get.return_value.json.return_value = config_groups_response

        # Mock association failure
        associate_response = Mock()
        associate_response.status_code = 500
        associate_response.text = "Association failed"
        mock_session.post.return_value = associate_response

        # Execute and assert
        with pytest.raises(AttachmentError) as exc_info:
            onboarder.attach_config_group(
                device_uuid="device-uuid-123",
                config_group_name="test_config_group",
                variables={"system_ip": "10.1.0.1", "site_id": 1},
            )

        assert "500" in str(exc_info.value)
        assert "associate" in str(exc_info.value).lower()


class TestWaitForTask:
    """Test vManage task monitoring."""

    @pytest.fixture
    def mock_session(self):
        """Create mock ManagerSession."""
        session = Mock()
        session.get = Mock()
        return session

    @pytest.fixture
    def onboarder(self, mock_session):
        """Create DeviceOnboarder with mock session."""
        return DeviceOnboarder(mock_session)

    def test_wait_for_task_success(self, onboarder, mock_session):
        """Test waiting for task when it succeeds immediately."""
        # Mock successful task response
        task_response = Mock()
        task_response.status_code = 200
        task_response.json.return_value = {
            "summary": {"status": "Success"}
        }
        mock_session.get.return_value = task_response

        # Execute
        result = onboarder._wait_for_task("task-123", timeout=60)

        # Assert
        assert result is True
        mock_session.get.assert_called_with("dataservice/device/action/status/task-123")

    @patch("time.sleep")
    def test_wait_for_task_success_after_delay(
        self, mock_sleep, onboarder, mock_session
    ):
        """Test waiting for task that succeeds after some time."""
        # Mock task responses: in_progress, in_progress, success
        response1 = Mock()
        response1.status_code = 200
        response1.json.return_value = {"summary": {"status": "in_progress"}}

        response2 = Mock()
        response2.status_code = 200
        response2.json.return_value = {"summary": {"status": "in_progress"}}

        response3 = Mock()
        response3.status_code = 200
        response3.json.return_value = {"summary": {"status": "Success"}}

        mock_session.get.side_effect = [response1, response2, response3]

        # Execute
        result = onboarder._wait_for_task("task-456", timeout=600, poll_interval=10)

        # Assert
        assert result is True
        assert mock_session.get.call_count == 3

    def test_wait_for_task_failure(self, onboarder, mock_session):
        """Test waiting for task when it fails."""
        # Mock failed task response
        task_response = Mock()
        task_response.status_code = 200
        task_response.json.return_value = {
            "summary": {"status": "Failure", "error": "Template validation failed"}
        }
        mock_session.get.return_value = task_response

        # Execute and assert
        with pytest.raises(AttachmentError) as exc_info:
            onboarder._wait_for_task("task-789", timeout=60)

        assert "task-789" in str(exc_info.value)
        assert "fail" in str(exc_info.value).lower()

    @patch("time.sleep")
    def test_wait_for_task_timeout(self, mock_sleep, onboarder, mock_session):
        """Test task timeout."""
        # Mock task that never completes
        task_response = Mock()
        task_response.status_code = 200
        task_response.json.return_value = {"summary": {"status": "in_progress"}}
        mock_session.get.return_value = task_response

        # Mock time to force timeout
        with patch("time.time") as mock_time:
            mock_time.side_effect = [0, 700]  # Start time, then past timeout

            # Execute and assert
            with pytest.raises(AttachmentError) as exc_info:
                onboarder._wait_for_task("task-timeout", timeout=600)

            assert "timeout" in str(exc_info.value).lower()
            assert "task-timeout" in str(exc_info.value)
