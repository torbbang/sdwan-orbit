"""Session management for SD-WAN Manager with retry logic."""

import time
import logging
from typing import Optional
from catalystwan.session import create_manager_session, ManagerSession
from catalystwan.exceptions import ManagerRequestException
from sdwan_orbit.exceptions import (
    ConnectionError as OrbitConnectionError,
    AuthenticationError,
    SessionError,
)


logger = logging.getLogger(__name__)


class SessionManager:
    """Manages SD-WAN Manager session with automatic retry logic."""

    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        port: int = 443,
        verify: bool = False,
        max_retries: int = 120,
        retry_interval: int = 30,
    ):
        """Initialize SessionManager.

        Args:
            url: vManage URL (with or without https://)
            username: Username for authentication
            password: Password for authentication
            port: vManage port (default: 443)
            verify: Verify SSL certificate (default: False)
            max_retries: Maximum number of connection retries (default: 120 = 1 hour with 30s interval)
            retry_interval: Seconds between retries (default: 30)
        """
        self.url = url if url.startswith("http") else f"https://{url}"
        self.username = username
        self.password = password
        self.port = port
        self.verify = verify
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        self._session: Optional[ManagerSession] = None

    @property
    def session(self) -> Optional[ManagerSession]:
        """Get current session.

        Returns:
            Current ManagerSession or None
        """
        return self._session

    def connect(self, timeout: Optional[int] = None) -> ManagerSession:
        """Connect to vManage with retry logic.

        Args:
            timeout: Override max_retries with custom timeout in seconds

        Returns:
            ManagerSession instance

        Raises:
            ConnectionError: If connection fails after all retries
            AuthenticationError: If authentication fails (non-retryable)
            SessionError: For other session-related errors
        """
        if timeout:
            max_retries = timeout // self.retry_interval
        else:
            max_retries = self.max_retries

        logger.info(f"Connecting to vManage at {self.url}:{self.port}")

        retries = 0
        last_exception = None

        while retries < max_retries:
            try:
                self._session = create_manager_session(
                    url=self.url,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    verify=self.verify,
                )
                logger.info("Successfully connected to vManage")
                return self._session

            except ConnectionRefusedError as e:
                last_exception = e
                retries += 1
                if retries % 10 == 0:
                    logger.info(
                        f"Waiting for vManage API (attempt {retries}/{max_retries})..."
                    )
                time.sleep(self.retry_interval)

            except (ConnectionError, ManagerRequestException) as e:
                last_exception = e
                # Check if it's an authentication error (non-retryable)
                if "401" in str(e) or "Unauthorized" in str(e):
                    raise AuthenticationError(
                        f"Authentication failed for user '{self.username}'"
                    ) from e

                retries += 1
                if retries % 10 == 0:
                    logger.info(
                        f"Waiting for vManage API (attempt {retries}/{max_retries})..."
                    )
                time.sleep(self.retry_interval)

            except Exception as e:
                # Catch-all for unexpected errors
                raise SessionError(f"Unexpected error connecting to vManage: {e}") from e

        # If we get here, we've exhausted all retries
        raise OrbitConnectionError(
            f"Failed to connect to vManage after {max_retries} attempts. "
            f"Last error: {last_exception}"
        )

    def close(self) -> None:
        """Close the current session.

        Raises:
            SessionError: If there's an error closing the session
        """
        if self._session:
            try:
                # Catalystwan sessions handle cleanup automatically
                # but we can explicitly clear the reference
                logger.debug("Closing vManage session")
                self._session = None
            except Exception as e:
                raise SessionError(f"Error closing session: {e}") from e
        else:
            logger.debug("No active session to close")

    def is_connected(self) -> bool:
        """Check if session is active.

        Returns:
            True if session exists and is active
        """
        return self._session is not None

    def __enter__(self) -> "SessionManager":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
