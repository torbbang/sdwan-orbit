"""Custom exceptions for ORBIT."""


class OrbitError(Exception):
    """Base exception for all ORBIT errors."""

    pass


class OnboardingError(OrbitError):
    """Raised when device onboarding fails."""

    pass


class CredentialError(OnboardingError):
    """Raised when device authentication fails."""

    pass


class DeviceNotFoundError(OnboardingError):
    """Raised when a device cannot be found in inventory."""

    pass


class OnboardingTimeoutError(OnboardingError):
    """Raised when device onboarding times out."""

    pass


class ConfigurationError(OrbitError):
    """Raised when configuration operation fails."""

    pass


class TemplateError(ConfigurationError):
    """Raised when template operation fails."""

    pass


class PolicyError(ConfigurationError):
    """Raised when policy operation fails."""

    pass


class AttachmentError(ConfigurationError):
    """Raised when template/config-group attachment fails."""

    pass


class BackupRestoreError(OrbitError):
    """Raised when backup or restore operation fails."""

    pass


class BackupError(BackupRestoreError):
    """Raised when backup operation fails."""

    pass


class RestoreError(BackupRestoreError):
    """Raised when restore operation fails."""

    pass


class SessionError(OrbitError):
    """Raised when session management fails."""

    pass


class ConnectionError(SessionError):
    """Raised when connection to vManage fails."""

    pass


class AuthenticationError(SessionError):
    """Raised when authentication fails."""

    pass


class ValidationError(OrbitError):
    """Raised when input validation fails."""

    pass
