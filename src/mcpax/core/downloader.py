"""File download and hash verification."""

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Protocol, Self

import httpx

from mcpax.core.exceptions import DownloadError, HashMismatchError
from mcpax.core.models import DownloadResult, DownloadTask

logger = logging.getLogger(__name__)

# === Progress Callback Protocols ===


class ProgressCallback(Protocol):
    """Protocol for progress update callbacks."""

    def __call__(
        self,
        task_id: object,
        completed: int,
        total: int | None,
    ) -> None:
        """Update progress for a task.

        Args:
            task_id: Identifier for the task (opaque)
            completed: Bytes downloaded so far
            total: Total bytes to download (None if unknown)
        """
        ...


class TaskStartCallback(Protocol):
    """Protocol for task start callbacks."""

    def __call__(
        self,
        slug: str,
        version_number: str,
        total: int | None,
    ) -> object:
        """Called when a task starts. Returns a task_id.

        Args:
            slug: Project slug
            version_number: Version string
            total: Total size in bytes (None if unknown)

        Returns:
            A task_id to be used for progress updates
        """
        ...


class TaskCompleteCallback(Protocol):
    """Protocol for task completion callbacks."""

    def __call__(self, task_id: object, success: bool, error: str | None) -> None:
        """Called when a task completes.

        Args:
            task_id: Identifier returned from TaskStartCallback
            success: Whether the download succeeded
            error: Error message if failed
        """
        ...


# === Hash Functions ===


def compute_sha512(file_path: Path, chunk_size: int = 8192) -> str:
    """Compute SHA512 hash of a file.

    Args:
        file_path: Path to the file.
        chunk_size: Size of chunks to read.

    Returns:
        Hex-encoded SHA512 hash.
    """
    sha512 = hashlib.sha512()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha512.update(chunk)
    return sha512.hexdigest()


def verify_file_hash(file_path: Path, expected_hash: str) -> bool:
    """Verify file hash matches expected value.

    Args:
        file_path: Path to the file.
        expected_hash: Expected SHA512 hash.

    Returns:
        True if hash matches, False otherwise.
    """
    actual_hash = compute_sha512(file_path)
    return actual_hash.lower() == expected_hash.lower()


# === Configuration ===


@dataclass
class DownloaderConfig:
    """Configuration for the Downloader."""

    max_concurrent: int = 5
    chunk_size: int = 8192  # 8KB chunks for streaming
    timeout: float = 300.0  # 5 minutes default
    verify_hash: bool = True


# === Downloader ===


class Downloader:
    """Async file downloader with parallel download support."""

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        config: DownloaderConfig | None = None,
        on_task_start: TaskStartCallback | None = None,
        on_progress: ProgressCallback | None = None,
        on_task_complete: TaskCompleteCallback | None = None,
    ) -> None:
        """Initialize the Downloader.

        Args:
            client: Optional httpx.AsyncClient for dependency injection.
            config: Downloader configuration.
            on_task_start: Callback when a task starts.
            on_progress: Callback for progress updates.
            on_task_complete: Callback when a task completes.
        """
        self._injected_client = client
        self._client: httpx.AsyncClient | None = None
        self._config = config or DownloaderConfig()
        self._on_task_start = on_task_start
        self._on_progress = on_progress
        self._on_task_complete = on_task_complete

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        if self._injected_client is not None:
            self._client = self._injected_client
        else:
            self._client = httpx.AsyncClient(timeout=self._config.timeout)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        if self._injected_client is None and self._client is not None:
            await self._client.aclose()

    async def download_file(self, task: DownloadTask) -> DownloadResult:
        """Download a single file.

        Args:
            task: Download task with URL, destination, and metadata.

        Returns:
            DownloadResult with success status and file path.
        """
        task_id = None
        file_path = None
        error_msg = None

        try:
            # Download the file (task_id will be set in _download_stream)
            file_path, task_id = await self._download_stream(task)

            # Verify hash if expected_hash is provided
            if self._config.verify_hash and task.expected_hash is not None:
                await self._verify_hash(task)

        except (DownloadError, HashMismatchError) as e:
            error_msg = str(e)
        except Exception as e:
            # Log unexpected errors with full traceback
            logger.exception("Unexpected error during download of %s: %s", task.slug, e)
            error_msg = f"Unexpected error: {e}"

        # Complete callback
        success = error_msg is None
        if self._on_task_complete and task_id is not None:
            self._on_task_complete(task_id, success, error_msg)

        return DownloadResult(
            task=task,
            success=success,
            file_path=file_path if success else None,
            error=error_msg,
        )

    async def download_all(
        self,
        tasks: list[DownloadTask],
    ) -> list[DownloadResult]:
        """Download multiple files in parallel.

        Uses asyncio.Semaphore to limit concurrent downloads.

        Args:
            tasks: List of download tasks.

        Returns:
            List of DownloadResult in the same order as input tasks.
        """
        semaphore = asyncio.Semaphore(self._config.max_concurrent)

        async def download_with_semaphore(task: DownloadTask) -> DownloadResult:
            async with semaphore:
                return await self.download_file(task)

        results = await asyncio.gather(
            *[download_with_semaphore(task) for task in tasks],
        )
        return results

    async def _download_stream(
        self,
        task: DownloadTask,
    ) -> tuple[Path, object | None]:
        """Stream download a file.

        Args:
            task: Download task

        Returns:
            Tuple of (downloaded file path, task_id for progress tracking)

        Raises:
            DownloadError: On HTTP or I/O error
        """
        # Ensure parent directory exists
        task.dest.parent.mkdir(parents=True, exist_ok=True)

        if self._client is None:
            msg = "Client not initialized. Use 'async with' context manager."
            raise RuntimeError(msg)

        task_id = None
        file_created = False
        try:
            async with self._client.stream("GET", task.url) as response:
                if response.status_code >= 400:
                    raise DownloadError(
                        f"HTTP {response.status_code}: {response.reason_phrase}",
                        url=task.url,
                    )

                total = int(response.headers.get("content-length", 0)) or None

                # Start task callback with total size
                if self._on_task_start:
                    task_id = self._on_task_start(task.slug, task.version_number, total)

                completed = 0
                with open(task.dest, "wb") as f:
                    file_created = True  # Mark file as created
                    async for chunk in response.aiter_bytes(self._config.chunk_size):
                        f.write(chunk)
                        completed += len(chunk)
                        if self._on_progress and task_id is not None:
                            self._on_progress(task_id, completed, total)

        except httpx.HTTPError as e:
            # Clean up partial file on network error
            if file_created:
                task.dest.unlink(missing_ok=True)
            raise DownloadError(f"HTTP error: {e}", url=task.url) from e
        except OSError as e:
            # Clean up partial file on I/O error
            if file_created:
                task.dest.unlink(missing_ok=True)
            raise DownloadError(f"I/O error: {e}", url=task.url) from e

        return task.dest, task_id

    async def _verify_hash(self, task: DownloadTask) -> None:
        """Verify downloaded file hash.

        Args:
            task: Download task with expected hash

        Raises:
            HashMismatchError: If hash doesn't match.
        """
        if not self._config.verify_hash or task.expected_hash is None:
            return

        actual_hash = await asyncio.to_thread(compute_sha512, task.dest)
        if actual_hash.lower() != task.expected_hash.lower():
            # Clean up invalid file
            task.dest.unlink(missing_ok=True)
            raise HashMismatchError(
                filename=task.dest.name,
                expected=task.expected_hash,
                actual=actual_hash,
            )
