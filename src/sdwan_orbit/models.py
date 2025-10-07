"""Pydantic models for device definitions and validation."""

from typing import Optional
from pydantic import BaseModel, Field, field_validator
from pathlib import Path
import yaml


class ManagerConfig(BaseModel):
    """vManage connection configuration."""

    url: str = Field(..., description="vManage URL (https://ip:port)")
    username: str = Field(..., description="Username for vManage")
    password: str = Field(..., description="Password for vManage")
    port: int = Field(default=443, description="vManage port")
    verify: bool = Field(default=False, description="Verify SSL certificate")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URL starts with http:// or https://."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class ControllerConfig(BaseModel):
    """vSmart controller configuration."""

    ip: str = Field(..., description="Management IP address")
    password: Optional[str] = Field(default="admin", description="Initial password")
    site_id: Optional[int] = Field(default=None, description="Site ID")
    system_ip: Optional[str] = Field(default=None, description="System IP address")
    hostname: Optional[str] = Field(default=None, description="Device hostname")


class ValidatorConfig(BaseModel):
    """vBond validator configuration."""

    ip: str = Field(..., description="Management IP address")
    password: Optional[str] = Field(default="admin", description="Initial password")
    site_id: Optional[int] = Field(default=None, description="Site ID")
    system_ip: Optional[str] = Field(default=None, description="System IP address")
    hostname: Optional[str] = Field(default=None, description="Device hostname")


class EdgeConfig(BaseModel):
    """WAN Edge device configuration."""

    serial: str = Field(..., description="Device serial number")
    system_ip: str = Field(..., description="System IP address")
    site_id: int = Field(..., description="Site ID")
    template_name: Optional[str] = Field(
        default=None, description="Device template name to attach"
    )
    config_group: Optional[str] = Field(
        default=None, description="Configuration group name to attach (20.12+)"
    )
    values: dict = Field(
        default_factory=dict, description="Additional template variable values"
    )


class DeviceInventory(BaseModel):
    """Complete device inventory for onboarding."""

    manager: ManagerConfig = Field(..., description="vManage connection details")
    controllers: list[ControllerConfig] = Field(
        default_factory=list, description="vSmart controllers"
    )
    validators: list[ValidatorConfig] = Field(
        default_factory=list, description="vBond validators"
    )
    edges: list[EdgeConfig] = Field(default_factory=list, description="WAN Edge devices")

    @classmethod
    def from_yaml(cls, path: Path) -> "DeviceInventory":
        """Load device inventory from YAML file.

        Args:
            path: Path to YAML file

        Returns:
            DeviceInventory instance

        Raises:
            FileNotFoundError: If file doesn't exist
            ValidationError: If YAML is invalid
        """
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        with open(path, "r") as f:
            data = yaml.safe_load(f)

        return cls(**data)

    @classmethod
    def from_dict(cls, data: dict) -> "DeviceInventory":
        """Create inventory from dictionary.

        Args:
            data: Dictionary with device information

        Returns:
            DeviceInventory instance

        Raises:
            ValidationError: If data is invalid
        """
        return cls(**data)

    def to_yaml(self, path: Path) -> None:
        """Save device inventory to YAML file.

        Args:
            path: Path to save YAML file
        """
        with open(path, "w") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False, sort_keys=False)

    def to_dict(self) -> dict:
        """Convert inventory to dictionary.

        Returns:
            Dictionary representation
        """
        return self.model_dump()

    @property
    def total_devices(self) -> int:
        """Get total number of devices.

        Returns:
            Total device count
        """
        return len(self.controllers) + len(self.validators) + len(self.edges)

    @property
    def control_components(self) -> int:
        """Get number of control plane components.

        Returns:
            Number of controllers and validators
        """
        return len(self.controllers) + len(self.validators)
