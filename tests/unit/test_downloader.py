"""Tests for mcpax.core.downloader."""

import hashlib
from pathlib import Path
from unittest.mock import Mock

import httpx
from pytest_httpx import HTTPXMock

from mcpax.core.downloader import (
    Downloader,
    DownloaderConfig,
    compute_sha512,
    verify_file_hash,
)
from mcpax.core.exceptions import DownloadError, HashMismatchError, MCPAXError
from mcpax.core.models import DownloadTask

# === Exception Tests ===


class TestDownloadError:
    """Tests for DownloadError exception."""

    def test_stores_message_and_url(self) -> None:
        """DownloadError stores message and url."""
        # Arrange & Act
        error = DownloadError("Connection failed", url="https://example.com/file.jar")

        # Assert
        assert str(error) == "Connection failed"
        assert error.url == "https://example.com/file.jar"

    def test_url_defaults_to_none(self) -> None:
        """DownloadError url defaults to None."""
        # Arrange & Act
        error = DownloadError("Unknown error")

        # Assert
        assert error.url is None

    def test_inherits_from_mcpax_error(self) -> None:
        """DownloadError inherits from MCPAXError."""
        # Arrange & Act
        error = DownloadError("Test")

        # Assert
        assert isinstance(error, MCPAXError)


class TestHashMismatchError:
    """Tests for HashMismatchError exception."""

    def test_stores_hash_values(self) -> None:
        """HashMismatchError stores filename and hashes."""
        # Arrange & Act
        error = HashMismatchError(
            filename="sodium.jar",
            expected="abc123" * 20,
            actual="def456" * 20,
        )

        # Assert
        assert error.filename == "sodium.jar"
        assert error.expected == "abc123" * 20
        assert error.actual == "def456" * 20
        assert "sodium.jar" in str(error)

    def test_inherits_from_download_error(self) -> None:
        """HashMismatchError inherits from DownloadError."""
        # Arrange & Act
        error = HashMismatchError("file.jar", "abc", "def")

        # Assert
        assert isinstance(error, DownloadError)


# === Hash Function Tests ===


class TestComputeSha512:
    """Tests for compute_sha512 function."""

    def test_computes_correct_hash(self, tmp_path: Path) -> None:
        """compute_sha512 returns correct hash."""
        # Arrange
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"hello world")
        # Known SHA512 of "hello world"
        expected = (
            "309ecc489c12d6eb4cc40f50c902f2b4d0ed77ee511a7c7a9bcd3ca86d4cd86f"
            "989dd35bc5ff499670da34255b45b0cfd830e81f605dcf7dc5542e93ae9cd76f"
        )

        # Act
        result = compute_sha512(test_file)

        # Assert
        assert result == expected

    def test_handles_large_file(self, tmp_path: Path) -> None:
        """compute_sha512 handles large files correctly."""
        # Arrange
        test_file = tmp_path / "large.bin"
        # Create 1MB file
        test_file.write_bytes(b"x" * (1024 * 1024))

        # Act
        result = compute_sha512(test_file)

        # Assert
        assert len(result) == 128  # SHA512 produces 128 hex characters


class TestVerifyFileHash:
    """Tests for verify_file_hash function."""

    def test_returns_true_for_matching_hash(self, tmp_path: Path) -> None:
        """verify_file_hash returns True when hash matches."""
        # Arrange
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test content")
        expected_hash = compute_sha512(test_file)

        # Act
        result = verify_file_hash(test_file, expected_hash)

        # Assert
        assert result is True

    def test_returns_false_for_mismatched_hash(self, tmp_path: Path) -> None:
        """verify_file_hash returns False when hash doesn't match."""
        # Arrange
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"test content")

        # Act
        result = verify_file_hash(test_file, "wrong_hash")

        # Assert
        assert result is False


# === Downloader Tests ===


class TestDownloaderInit:
    """Tests for Downloader initialization."""

    def test_default_config(self) -> None:
        """Downloader uses default config when not specified."""
        # Arrange & Act
        downloader = Downloader()

        # Assert
        assert downloader._config.max_concurrent == 5
        assert downloader._config.verify_hash is True

    def test_custom_config(self) -> None:
        """Downloader accepts custom config."""
        # Arrange
        config = DownloaderConfig(max_concurrent=10, verify_hash=False)

        # Act
        downloader = Downloader(config=config)

        # Assert
        assert downloader._config.max_concurrent == 10
        assert downloader._config.verify_hash is False


class TestDownloaderContextManager:
    """Tests for Downloader context manager."""

    async def test_creates_client_on_enter(self) -> None:
        """Context manager creates httpx client on enter."""
        # Arrange
        downloader = Downloader()

        # Act
        async with downloader as d:
            # Assert
            assert d._client is not None

    async def test_uses_injected_client(self) -> None:
        """Context manager uses injected client."""
        # Arrange
        injected = httpx.AsyncClient()
        downloader = Downloader(client=injected)

        # Act
        async with downloader as d:
            # Assert
            assert d._client is injected

        # Cleanup
        await injected.aclose()


class TestDownloadFile:
    """Tests for download_file method."""

    async def test_downloads_file_successfully(
        self,
        httpx_mock: HTTPXMock,
        tmp_path: Path,
    ) -> None:
        """download_file saves file to destination."""
        # Arrange
        file_content = b"test file content"
        httpx_mock.add_response(
            url="https://cdn.example.com/test.jar",
            content=file_content,
        )
        task = DownloadTask(
            url="https://cdn.example.com/test.jar",
            dest=tmp_path / "test.jar",
            expected_hash=None,
            slug="test-mod",
            version_number="1.0.0",
        )

        # Act
        async with Downloader() as downloader:
            result = await downloader.download_file(task)

        # Assert
        assert result.success is True
        assert result.file_path == tmp_path / "test.jar"
        assert result.file_path.read_bytes() == file_content

    async def test_creates_parent_directories(
        self,
        httpx_mock: HTTPXMock,
        tmp_path: Path,
    ) -> None:
        """download_file creates parent directories if needed."""
        # Arrange
        httpx_mock.add_response(content=b"content")
        task = DownloadTask(
            url="https://cdn.example.com/test.jar",
            dest=tmp_path / "nested" / "path" / "test.jar",
            expected_hash=None,
            slug="test",
            version_number="1.0",
        )

        # Act
        async with Downloader() as downloader:
            await downloader.download_file(task)

        # Assert
        assert (tmp_path / "nested" / "path" / "test.jar").exists()

    async def test_verifies_hash_when_provided(
        self,
        httpx_mock: HTTPXMock,
        tmp_path: Path,
    ) -> None:
        """download_file verifies hash when expected_hash is set."""
        # Arrange
        content = b"test content"
        expected_hash = hashlib.sha512(content).hexdigest()
        httpx_mock.add_response(content=content)
        task = DownloadTask(
            url="https://cdn.example.com/test.jar",
            dest=tmp_path / "test.jar",
            expected_hash=expected_hash,
            slug="test",
            version_number="1.0",
        )

        # Act
        async with Downloader() as downloader:
            result = await downloader.download_file(task)

        # Assert
        assert result.success is True

    async def test_hash_mismatch_returns_failed_result(
        self,
        httpx_mock: HTTPXMock,
        tmp_path: Path,
    ) -> None:
        """download_file returns failed result on hash mismatch."""
        # Arrange
        httpx_mock.add_response(content=b"actual content")
        task = DownloadTask(
            url="https://cdn.example.com/test.jar",
            dest=tmp_path / "test.jar",
            expected_hash="wrong_hash_value",
            slug="test",
            version_number="1.0",
        )

        # Act
        async with Downloader() as downloader:
            result = await downloader.download_file(task)

        # Assert
        assert result.success is False
        assert "Hash mismatch" in result.error
        assert not task.dest.exists()  # File should be deleted

    async def test_http_error_returns_failed_result(
        self,
        httpx_mock: HTTPXMock,
        tmp_path: Path,
    ) -> None:
        """download_file returns failed result on HTTP error."""
        # Arrange
        httpx_mock.add_response(status_code=404)
        task = DownloadTask(
            url="https://cdn.example.com/nonexistent.jar",
            dest=tmp_path / "test.jar",
            expected_hash=None,
            slug="test",
            version_number="1.0",
        )

        # Act
        async with Downloader() as downloader:
            result = await downloader.download_file(task)

        # Assert
        assert result.success is False
        assert "404" in result.error


class TestDownloadAll:
    """Tests for download_all method."""

    async def test_downloads_multiple_files(
        self,
        httpx_mock: HTTPXMock,
        tmp_path: Path,
    ) -> None:
        """download_all downloads multiple files."""
        # Arrange
        httpx_mock.add_response(url="https://example.com/a.jar", content=b"a")
        httpx_mock.add_response(url="https://example.com/b.jar", content=b"b")
        tasks = [
            DownloadTask(
                url="https://example.com/a.jar",
                dest=tmp_path / "a.jar",
                expected_hash=None,
                slug="mod-a",
                version_number="1.0",
            ),
            DownloadTask(
                url="https://example.com/b.jar",
                dest=tmp_path / "b.jar",
                expected_hash=None,
                slug="mod-b",
                version_number="2.0",
            ),
        ]

        # Act
        async with Downloader() as downloader:
            results = await downloader.download_all(tasks)

        # Assert
        assert len(results) == 2
        assert all(r.success for r in results)

    async def test_handles_partial_failures(
        self,
        httpx_mock: HTTPXMock,
        tmp_path: Path,
    ) -> None:
        """download_all continues after individual failures."""
        # Arrange
        httpx_mock.add_response(url="https://example.com/a.jar", content=b"a")
        httpx_mock.add_response(url="https://example.com/b.jar", status_code=500)
        httpx_mock.add_response(url="https://example.com/c.jar", content=b"c")
        tasks = [
            DownloadTask(
                url=f"https://example.com/{x}.jar",
                dest=tmp_path / f"{x}.jar",
                expected_hash=None,
                slug=f"mod-{x}",
                version_number="1.0",
            )
            for x in ["a", "b", "c"]
        ]

        # Act
        async with Downloader() as downloader:
            results = await downloader.download_all(tasks)

        # Assert
        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True


class TestDownloaderCallbacks:
    """Tests for Downloader callback functionality."""

    async def test_on_task_start_called_with_correct_args(
        self,
        httpx_mock: HTTPXMock,
        tmp_path: Path,
    ) -> None:
        """on_task_start is called with slug, version_number, and total size."""
        # Arrange
        on_task_start = Mock(return_value="task-id-123")
        httpx_mock.add_response(
            content=b"test content",
            headers={"content-length": "12"},
        )
        task = DownloadTask(
            url="https://example.com/test.jar",
            dest=tmp_path / "test.jar",
            expected_hash=None,
            slug="test-mod",
            version_number="1.0.0",
        )

        # Act
        async with Downloader(on_task_start=on_task_start) as downloader:
            await downloader.download_file(task)

        # Assert
        on_task_start.assert_called_once_with("test-mod", "1.0.0", 12)

    async def test_on_progress_called_during_download(
        self,
        httpx_mock: HTTPXMock,
        tmp_path: Path,
    ) -> None:
        """on_progress is called with task_id, completed, and total."""
        # Arrange
        task_id = "task-id-123"
        on_task_start = Mock(return_value=task_id)
        on_progress = Mock()
        httpx_mock.add_response(
            content=b"test content",
            headers={"content-length": "12"},
        )
        task = DownloadTask(
            url="https://example.com/test.jar",
            dest=tmp_path / "test.jar",
            expected_hash=None,
            slug="test-mod",
            version_number="1.0.0",
        )

        # Act
        async with Downloader(
            on_task_start=on_task_start,
            on_progress=on_progress,
        ) as downloader:
            await downloader.download_file(task)

        # Assert
        assert on_progress.call_count > 0
        # Check that last call has correct arguments
        last_call_args = on_progress.call_args[0]
        assert last_call_args[0] == task_id
        assert last_call_args[1] == 12  # completed bytes
        assert last_call_args[2] == 12  # total bytes

    async def test_on_task_complete_called_on_success(
        self,
        httpx_mock: HTTPXMock,
        tmp_path: Path,
    ) -> None:
        """on_task_complete is called with success=True on successful download."""
        # Arrange
        task_id = "task-id-123"
        on_task_start = Mock(return_value=task_id)
        on_task_complete = Mock()
        httpx_mock.add_response(content=b"test content")
        task = DownloadTask(
            url="https://example.com/test.jar",
            dest=tmp_path / "test.jar",
            expected_hash=None,
            slug="test-mod",
            version_number="1.0.0",
        )

        # Act
        async with Downloader(
            on_task_start=on_task_start,
            on_task_complete=on_task_complete,
        ) as downloader:
            await downloader.download_file(task)

        # Assert
        on_task_complete.assert_called_once_with(task_id, True, None)

    async def test_on_task_complete_called_on_failure(
        self,
        httpx_mock: HTTPXMock,
        tmp_path: Path,
    ) -> None:
        """on_task_complete is called with success=False on hash mismatch."""
        # Arrange
        task_id = "task-id-123"
        on_task_start = Mock(return_value=task_id)
        on_task_complete = Mock()
        httpx_mock.add_response(content=b"actual content")
        task = DownloadTask(
            url="https://example.com/test.jar",
            dest=tmp_path / "test.jar",
            expected_hash="wrong_hash_value",  # Hash mismatch error
            slug="test-mod",
            version_number="1.0.0",
        )

        # Act
        async with Downloader(
            on_task_start=on_task_start,
            on_task_complete=on_task_complete,
        ) as downloader:
            await downloader.download_file(task)

        # Assert
        assert on_task_complete.call_count == 1
        call_args = on_task_complete.call_args[0]
        assert call_args[0] == task_id
        assert call_args[1] is False
        assert call_args[2] is not None  # error message should be present
        assert "Hash mismatch" in call_args[2]

    async def test_on_task_complete_not_called_on_early_http_error(
        self,
        httpx_mock: HTTPXMock,
        tmp_path: Path,
    ) -> None:
        """on_task_complete is not called when HTTP error occurs before task starts."""
        # Arrange
        on_task_start = Mock(return_value="task-id-123")
        on_task_complete = Mock()
        httpx_mock.add_response(status_code=404)
        task = DownloadTask(
            url="https://example.com/test.jar",
            dest=tmp_path / "test.jar",
            expected_hash=None,
            slug="test-mod",
            version_number="1.0.0",
        )

        # Act
        async with Downloader(
            on_task_start=on_task_start,
            on_task_complete=on_task_complete,
        ) as downloader:
            result = await downloader.download_file(task)

        # Assert
        assert result.success is False
        # on_task_start should not be called because error occurs in stream
        on_task_start.assert_not_called()
        # on_task_complete should not be called because task_id is None
        on_task_complete.assert_not_called()

    async def test_callbacks_not_called_when_not_provided(
        self,
        httpx_mock: HTTPXMock,
        tmp_path: Path,
    ) -> None:
        """Download works correctly when no callbacks are provided."""
        # Arrange
        httpx_mock.add_response(content=b"test content")
        task = DownloadTask(
            url="https://example.com/test.jar",
            dest=tmp_path / "test.jar",
            expected_hash=None,
            slug="test-mod",
            version_number="1.0.0",
        )

        # Act & Assert (should not raise)
        async with Downloader() as downloader:
            result = await downloader.download_file(task)
            assert result.success is True
