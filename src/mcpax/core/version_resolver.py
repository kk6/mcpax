"""Version compatibility and pinning resolution."""

from pydantic import BaseModel

from mcpax.core.models import Loader, ProjectType, ProjectVersion, ReleaseChannel


class VersionCriteria(BaseModel):
    """Criteria used to select a compatible project version."""

    minecraft_version: str
    mod_loader: Loader
    shader_loader: Loader | None = None
    project_type: ProjectType | None = None
    channel: ReleaseChannel = ReleaseChannel.RELEASE
    pinned_version: str | None = None


class PinnedVersionResult(BaseModel):
    """Result of resolving a pinned version."""

    version: ProjectVersion | None
    error: str | None = None


class VersionResolver:
    """Resolve compatible Modrinth project versions."""

    _CHANNEL_ORDER = {
        ReleaseChannel.RELEASE: 0,
        ReleaseChannel.BETA: 1,
        ReleaseChannel.ALPHA: 2,
    }

    def filter_compatible_versions(
        self,
        versions: list[ProjectVersion],
        criteria: VersionCriteria,
    ) -> list[ProjectVersion]:
        """Filter versions compatible with the provided criteria."""
        min_channel_value = self._CHANNEL_ORDER[criteria.channel]

        compatible = []
        for version in versions:
            if criteria.minecraft_version not in version.game_versions:
                continue

            loader_to_check = self._loader_for(criteria)
            if loader_to_check is not None:
                loader_str = loader_to_check.value.lower()
                loaders_lower = [name.lower() for name in version.loaders]
                if (
                    version.loaders
                    and "minecraft" not in loaders_lower
                    and loader_str not in loaders_lower
                ):
                    continue

            version_channel_value = self._CHANNEL_ORDER[version.version_type]
            if version_channel_value > min_channel_value:
                continue

            compatible.append(version)

        compatible.sort(key=lambda v: v.date_published, reverse=True)
        return compatible

    def latest_compatible_version(
        self,
        versions: list[ProjectVersion],
        criteria: VersionCriteria,
    ) -> ProjectVersion | None:
        """Return the newest compatible version, if one exists."""
        compatible = self.filter_compatible_versions(versions, criteria)
        return compatible[0] if compatible else None

    def find_version_by_number(
        self,
        versions: list[ProjectVersion],
        version_number: str,
    ) -> ProjectVersion | None:
        """Find a version by exact version number match."""
        return next(
            (
                version
                for version in versions
                if version.version_number == version_number
            ),
            None,
        )

    def resolve_pinned_version(
        self,
        versions: list[ProjectVersion],
        criteria: VersionCriteria,
    ) -> PinnedVersionResult:
        """Find the pinned version and verify it is compatible."""
        if criteria.pinned_version is None:
            msg = "Pinned version criteria requires pinned_version"
            raise ValueError(msg)

        pinned_version = self.find_version_by_number(
            versions,
            criteria.pinned_version,
        )
        if pinned_version is None:
            return PinnedVersionResult(
                version=None,
                error=f"Pinned version {criteria.pinned_version} not found",
            )

        compatible_versions = self.filter_compatible_versions(
            [pinned_version],
            criteria,
        )
        if not compatible_versions:
            return PinnedVersionResult(
                version=None,
                error=f"Pinned version {criteria.pinned_version} is not compatible",
            )

        return PinnedVersionResult(version=pinned_version)

    def _loader_for(self, criteria: VersionCriteria) -> Loader | None:
        """Return the loader criterion relevant to the project type."""
        if criteria.project_type == ProjectType.SHADER:
            return criteria.shader_loader
        if criteria.project_type != ProjectType.RESOURCEPACK:
            return criteria.mod_loader
        return None
