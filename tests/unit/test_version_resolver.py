"""Tests for version compatibility resolution."""

from datetime import UTC, datetime

import pytest

from mcpax.core.models import Loader, ProjectType, ReleaseChannel
from mcpax.core.version_resolver import VersionCriteria, VersionResolver
from tests.conftest import _make_version


def _criteria(**overrides) -> VersionCriteria:
    defaults = {
        "minecraft_version": "1.21.4",
        "mod_loader": Loader.FABRIC,
        "project_type": ProjectType.MOD,
        "channel": ReleaseChannel.RELEASE,
    }
    return VersionCriteria(**{**defaults, **overrides})


class TestVersionResolverFilterCompatibleVersions:
    """Tests for filtering compatible versions."""

    def test_returns_versions_matching_minecraft_loader_and_channel(self) -> None:
        versions = [
            _make_version("wrong-mc", game_versions=["1.20.1"], loaders=["fabric"]),
            _make_version("wrong-loader", loaders=["forge"]),
            _make_version("alpha", version_type=ReleaseChannel.ALPHA),
            _make_version("release", loaders=["fabric"]),
        ]

        result = VersionResolver().filter_compatible_versions(
            versions,
            _criteria(),
        )

        assert [version.version_number for version in result] == ["release"]

    def test_sorts_compatible_versions_newest_first(self) -> None:
        versions = [
            _make_version(
                "older",
                date_published=datetime(2024, 1, 1, tzinfo=UTC),
            ),
            _make_version(
                "newer",
                date_published=datetime(2024, 2, 1, tzinfo=UTC),
            ),
        ]

        result = VersionResolver().filter_compatible_versions(
            versions,
            _criteria(),
        )

        assert [version.version_number for version in result] == ["newer", "older"]

    @pytest.mark.parametrize(
        ("channel", "expected"),
        [
            (ReleaseChannel.RELEASE, ["release"]),
            (ReleaseChannel.BETA, ["beta", "release"]),
            (ReleaseChannel.ALPHA, ["alpha", "beta", "release"]),
        ],
    )
    def test_channel_includes_versions_up_to_requested_instability(
        self,
        channel: ReleaseChannel,
        expected: list[str],
    ) -> None:
        versions = [
            _make_version(
                "release",
                version_type=ReleaseChannel.RELEASE,
                date_published=datetime(2024, 1, 1, tzinfo=UTC),
            ),
            _make_version(
                "beta",
                version_type=ReleaseChannel.BETA,
                date_published=datetime(2024, 1, 2, tzinfo=UTC),
            ),
            _make_version(
                "alpha",
                version_type=ReleaseChannel.ALPHA,
                date_published=datetime(2024, 1, 3, tzinfo=UTC),
            ),
        ]

        result = VersionResolver().filter_compatible_versions(
            versions,
            _criteria(channel=channel),
        )

        assert [version.version_number for version in result] == expected

    def test_shader_uses_shader_loader(self) -> None:
        versions = [
            _make_version("fabric", loaders=["fabric"]),
            _make_version("iris", loaders=["iris"]),
        ]

        result = VersionResolver().filter_compatible_versions(
            versions,
            _criteria(
                project_type=ProjectType.SHADER,
                shader_loader=Loader.IRIS,
            ),
        )

        assert [version.version_number for version in result] == ["iris"]

    def test_resourcepack_ignores_loader(self) -> None:
        versions = [
            _make_version("empty-loader", loaders=[]),
            _make_version("minecraft-loader", loaders=["minecraft"]),
            _make_version("forge-loader", loaders=["forge"]),
        ]

        result = VersionResolver().filter_compatible_versions(
            versions,
            _criteria(project_type=ProjectType.RESOURCEPACK),
        )

        assert [version.version_number for version in result] == [
            "empty-loader",
            "minecraft-loader",
            "forge-loader",
        ]


class TestVersionResolverResolvePinnedVersion:
    """Tests for pinned version resolution."""

    def test_returns_compatible_pinned_version(self) -> None:
        versions = [
            _make_version("1.0.0"),
            _make_version("1.1.0"),
        ]

        result = VersionResolver().resolve_pinned_version(
            versions,
            _criteria(pinned_version="1.1.0"),
        )

        assert result.version is not None
        assert result.version.version_number == "1.1.0"
        assert result.error is None

    def test_returns_error_when_pinned_version_is_missing(self) -> None:
        result = VersionResolver().resolve_pinned_version(
            [_make_version("1.0.0")],
            _criteria(pinned_version="2.0.0"),
        )

        assert result.version is None
        assert result.error == "Pinned version 2.0.0 not found"

    def test_returns_error_when_pinned_version_is_not_compatible(self) -> None:
        result = VersionResolver().resolve_pinned_version(
            [_make_version("1.0.0", game_versions=["1.20.1"])],
            _criteria(pinned_version="1.0.0"),
        )

        assert result.version is None
        assert result.error == "Pinned version 1.0.0 is not compatible"

    def test_requires_pinned_version(self) -> None:
        with pytest.raises(ValueError, match="requires pinned_version"):
            VersionResolver().resolve_pinned_version(
                [_make_version("1.0.0")],
                _criteria(),
            )
