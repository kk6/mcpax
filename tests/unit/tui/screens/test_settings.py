"""Tests for SettingsScreen and EditSettingModal."""

from pathlib import Path

import pytest
from textual.app import App
from textual.coordinate import Coordinate

from mcpax.core.config import CONFIG_KEY_MAP


class TestSettingsConstants:
    """Test constants used in settings screen."""

    def test_settings_sections_covers_all_config_keys(self):
        """SETTINGS_SECTIONS should cover all CONFIG_KEY_MAP keys."""
        from mcpax.tui.screens.settings import SETTINGS_SECTIONS

        # Flatten all keys from SETTINGS_SECTIONS
        all_keys = []
        for keys in SETTINGS_SECTIONS.values():
            all_keys.extend(keys)

        # Check all CONFIG_KEY_MAP keys are present
        config_keys = set(CONFIG_KEY_MAP.keys())
        section_keys = set(all_keys)

        assert config_keys == section_keys, (
            f"Missing keys: {config_keys - section_keys}, "
            f"Extra keys: {section_keys - config_keys}"
        )

    def test_field_labels_covers_all_config_keys(self):
        """FIELD_LABELS should have labels for all CONFIG_KEY_MAP keys."""
        from mcpax.tui.screens.settings import FIELD_LABELS

        config_keys = set(CONFIG_KEY_MAP.keys())
        label_keys = set(FIELD_LABELS.keys())

        assert config_keys == label_keys, (
            f"Missing keys: {config_keys - label_keys}, "
            f"Extra keys: {label_keys - config_keys}"
        )

    def test_select_fields_has_mod_loader_and_shader_loader(self):
        """SELECT_FIELDS should include mod_loader and shader_loader."""
        from mcpax.tui.screens.settings import SELECT_FIELDS

        assert "minecraft.mod_loader" in SELECT_FIELDS
        assert "minecraft.shader_loader" in SELECT_FIELDS

        # Check that choices are available
        assert len(SELECT_FIELDS["minecraft.mod_loader"]) > 0
        assert len(SELECT_FIELDS["minecraft.shader_loader"]) > 0

    def test_boolean_fields_has_verify_hash(self):
        """BOOLEAN_FIELDS should include verify_hash."""
        from mcpax.tui.screens.settings import BOOLEAN_FIELDS

        assert "download.verify_hash" in BOOLEAN_FIELDS


class TestSettingsScreenStructure:
    """Test SettingsScreen basic structure."""

    @pytest.mark.asyncio
    async def test_settings_screen_initialization(self, tmp_path: Path) -> None:
        """Test SettingsScreen initialization."""
        from mcpax.tui.screens.settings import SettingsScreen

        config_path = tmp_path / "config.toml"
        screen = SettingsScreen(config_path=config_path)
        assert screen is not None
        assert screen._config_path == config_path

    @pytest.mark.asyncio
    async def test_settings_screen_initialization_default_path(self) -> None:
        """Test SettingsScreen initialization with default path."""
        from mcpax.tui.screens.settings import SettingsScreen

        screen = SettingsScreen()
        assert screen is not None
        assert screen._config_path is None

    @pytest.mark.asyncio
    async def test_settings_screen_compose(self, tmp_path: Path) -> None:
        """Test SettingsScreen has required widgets."""
        from mcpax.tui.screens.settings import SettingsScreen

        class TestApp(App[None]):
            def on_mount(self):
                config_path = tmp_path / "config.toml"
                self.push_screen(SettingsScreen(config_path=config_path))

        app = TestApp()
        async with app.run_test():
            screen = app.screen
            assert screen is not None

            # Check for DataTable
            table = screen.query_one("#settings-table")
            assert table is not None

            # Check for Footer
            from textual.widgets import Footer

            footer = screen.query_one(Footer)
            assert footer is not None

    @pytest.mark.asyncio
    async def test_settings_screen_bindings(self, tmp_path: Path) -> None:
        """Test SettingsScreen has required key bindings."""
        from mcpax.tui.screens.settings import SettingsScreen

        config_path = tmp_path / "config.toml"
        screen = SettingsScreen(config_path=config_path)

        # Check bindings
        binding_keys = [b.key for b in screen.BINDINGS]
        assert "escape" in binding_keys
        assert "enter" in binding_keys


class TestSettingsScreenLoading:
    """Test settings loading functionality."""

    @pytest.mark.asyncio
    async def test_load_settings_displays_all_values(self, tmp_path: Path) -> None:
        """Test that _load_settings displays all config values."""
        from mcpax.tui.screens.settings import SettingsScreen

        # Create a test config file
        config_path = tmp_path / "config.toml"
        config_path.write_text("""
[minecraft]
version = "1.21.4"
mod_loader = "fabric"
shader_loader = "iris"

[paths]
minecraft_dir = "/tmp/.minecraft"

[download]
max_concurrent = 5
verify_hash = true
""")

        class TestApp(App[None]):
            def on_mount(self):
                self.push_screen(SettingsScreen(config_path=config_path))

        app = TestApp()
        async with app.run_test():
            screen = app.screen
            table = screen.query_one("#settings-table")

            # Check that all 9 config keys are displayed
            assert table.row_count == 9

            # Verify some specific values by checking cell contents
            # Get the first row (minecraft.version)
            row_key = list(table.rows)[0]
            first_row = table.get_row(row_key)
            # Check value column (index 2)
            assert "1.21.4" in str(first_row[2])

    @pytest.mark.asyncio
    async def test_load_settings_handles_missing_file(self, tmp_path: Path) -> None:
        """Test that _load_settings handles missing config file."""
        from mcpax.tui.screens.settings import SettingsScreen

        config_path = tmp_path / "nonexistent.toml"

        class TestApp(App[None]):
            def on_mount(self):
                self.push_screen(SettingsScreen(config_path=config_path))

        app = TestApp()
        async with app.run_test():
            screen = app.screen
            table = screen.query_one("#settings-table")

            # Table should still be populated with "(not set)" values
            assert table.row_count == 9

    @pytest.mark.asyncio
    async def test_load_settings_displays_not_set_for_missing_values(
        self, tmp_path: Path
    ) -> None:
        """Test that missing values are displayed as '(not set)'."""
        from mcpax.tui.screens.settings import SettingsScreen

        # Create minimal config
        config_path = tmp_path / "config.toml"
        config_path.write_text("""
[minecraft]
version = "1.21.4"
mod_loader = "fabric"

[paths]
minecraft_dir = "/tmp/.minecraft"
""")

        class TestApp(App[None]):
            def on_mount(self):
                self.push_screen(SettingsScreen(config_path=config_path))

        app = TestApp()
        async with app.run_test():
            screen = app.screen
            table = screen.query_one("#settings-table")

            # Check that shader_loader shows "(not set)"
            # Shader loader is the 3rd setting (index 2)
            row_keys = list(table.rows)
            shader_row = table.get_row(row_keys[2])
            # Check label column (index 1) is "Shader Loader"
            assert "Shader Loader" in str(shader_row[1])
            # Check value column (index 2) is "(not set)"
            assert "(not set)" in str(shader_row[2])


class TestEditSettingModal:
    """Test EditSettingModal widget selection."""

    @pytest.mark.asyncio
    async def test_edit_modal_input_widget_for_string_fields(
        self, tmp_path: Path
    ) -> None:
        """Test that Input widget is used for string fields."""
        from mcpax.tui.screens.settings import EditSettingModal

        class TestApp(App[None]):
            def on_mount(self):
                self.push_screen(
                    EditSettingModal(
                        key="minecraft.version",
                        label="Minecraft Version",
                        current_value="1.21.4",
                    )
                )

        app = TestApp()
        async with app.run_test():
            screen = app.screen
            # Should have an Input widget
            from textual.widgets import Input

            input_widget = screen.query_one(Input)
            assert input_widget is not None
            assert input_widget.value == "1.21.4"

    @pytest.mark.asyncio
    async def test_edit_modal_select_widget_for_mod_loader(
        self, tmp_path: Path
    ) -> None:
        """Test that Select widget is used for mod_loader field."""
        from mcpax.tui.screens.settings import EditSettingModal

        class TestApp(App[None]):
            def on_mount(self):
                self.push_screen(
                    EditSettingModal(
                        key="minecraft.mod_loader",
                        label="Mod Loader",
                        current_value="fabric",
                    )
                )

        app = TestApp()
        async with app.run_test():
            screen = app.screen
            # Should have a Select widget
            from textual.widgets import Select

            select_widget = screen.query_one(Select)
            assert select_widget is not None

    @pytest.mark.asyncio
    async def test_edit_modal_select_widget_for_boolean(self, tmp_path: Path) -> None:
        """Test that Select widget is used for boolean fields."""
        from mcpax.tui.screens.settings import EditSettingModal

        class TestApp(App[None]):
            def on_mount(self):
                self.push_screen(
                    EditSettingModal(
                        key="download.verify_hash",
                        label="Verify Hash",
                        current_value="True",
                    )
                )

        app = TestApp()
        async with app.run_test():
            screen = app.screen
            # Should have a Select widget
            from textual.widgets import Select

            select_widget = screen.query_one(Select)
            assert select_widget is not None

    @pytest.mark.asyncio
    async def test_edit_modal_save_button_returns_new_value(
        self, tmp_path: Path
    ) -> None:
        """Test that Save button returns the new value."""
        from mcpax.tui.screens.settings import EditSettingModal

        result = None

        class TestApp(App[None]):
            def on_mount(self):
                self.push_screen(
                    EditSettingModal(
                        key="minecraft.version",
                        label="Minecraft Version",
                        current_value="1.21.4",
                    ),
                    callback=self.handle_result,
                )

            def handle_result(self, value: str | None):
                nonlocal result
                result = value

        app = TestApp()
        async with app.run_test() as pilot:
            screen = app.screen
            # Change the input value
            from textual.widgets import Input

            input_widget = screen.query_one(Input)
            input_widget.value = "1.22.0"

            # Click Save button
            save_button = screen.query_one("#save-button")
            await pilot.click(save_button)

            # Wait a bit for the callback
            await pilot.pause()

            assert result == "1.22.0"

    @pytest.mark.asyncio
    async def test_edit_modal_cancel_button_returns_none(self, tmp_path: Path) -> None:
        """Test that Cancel button returns None."""
        from mcpax.tui.screens.settings import EditSettingModal

        result = "UNSET"

        class TestApp(App[None]):
            def on_mount(self):
                self.push_screen(
                    EditSettingModal(
                        key="minecraft.version",
                        label="Minecraft Version",
                        current_value="1.21.4",
                    ),
                    callback=self.handle_result,
                )

            def handle_result(self, value: str | None):
                nonlocal result
                result = value

        app = TestApp()
        async with app.run_test() as pilot:
            screen = app.screen

            # Click Cancel button
            cancel_button = screen.query_one("#cancel-button")
            await pilot.click(cancel_button)

            # Wait a bit for the callback
            await pilot.pause()

            assert result is None

    @pytest.mark.asyncio
    async def test_edit_modal_escape_key_cancels(self, tmp_path: Path) -> None:
        """Test that Escape key cancels the modal."""
        from mcpax.tui.screens.settings import EditSettingModal

        result = "UNSET"

        class TestApp(App[None]):
            def on_mount(self):
                self.push_screen(
                    EditSettingModal(
                        key="minecraft.version",
                        label="Minecraft Version",
                        current_value="1.21.4",
                    ),
                    callback=self.handle_result,
                )

            def handle_result(self, value: str | None):
                nonlocal result
                result = value

        app = TestApp()
        async with app.run_test() as pilot:
            # Press Escape
            await pilot.press("escape")
            await pilot.pause()

            assert result is None

    @pytest.mark.asyncio
    async def test_edit_modal_select_returns_enum_value_not_label(
        self, tmp_path: Path
    ) -> None:
        """Test that Select widget returns enum value, not human label."""
        from mcpax.tui.screens.settings import EditSettingModal

        result = None

        class TestApp(App[None]):
            def on_mount(self):
                self.push_screen(
                    EditSettingModal(
                        key="minecraft.mod_loader",
                        label="Mod Loader",
                        current_value="fabric",
                    ),
                    callback=self.handle_result,
                )

            def handle_result(self, value: str | None):
                nonlocal result
                result = value

        app = TestApp()
        async with app.run_test() as pilot:
            screen = app.screen

            # Get the Select widget
            from textual.widgets import Select

            select_widget = screen.query_one(Select)

            # Change selection to "forge" (enum value)
            select_widget.value = "forge"

            # Click Save button
            save_button = screen.query_one("#save-button")
            await pilot.click(save_button)
            await pilot.pause()

            # Verify the result is the enum value "forge", not label "Forge"
            assert result == "forge"
            assert result != "Forge"


class TestSettingsEditing:
    """Test settings editing flow."""

    @pytest.mark.asyncio
    async def test_on_edit_dismissed_saves_value(self, tmp_path: Path) -> None:
        """Test that _on_edit_dismissed saves the new value."""
        from unittest.mock import patch

        from mcpax.tui.screens.settings import SettingsScreen

        # Create a test config file
        config_path = tmp_path / "config.toml"
        config_path.write_text("""
[minecraft]
version = "1.21.4"
mod_loader = "fabric"

[paths]
minecraft_dir = "/tmp/.minecraft"

[download]
max_concurrent = 5
verify_hash = true
""")

        class TestApp(App[None]):
            def on_mount(self):
                self.push_screen(SettingsScreen(config_path=config_path))

        app = TestApp()
        async with app.run_test():
            screen = app.screen
            table = screen.query_one("#settings-table")

            # Set cursor to first row
            table.cursor_coordinate = (0, 0)

            # Mock set_config_value
            with patch("mcpax.tui.screens.settings.set_config_value") as mock_set:
                # Call _on_edit_dismissed directly with a new value
                screen._on_edit_dismissed("1.22.0")

                # Verify set_config_value was called
                mock_set.assert_called_once_with(
                    "minecraft.version", "1.22.0", config_path
                )

                # Verify _changed flag is True
                assert screen._changed is True

    @pytest.mark.asyncio
    async def test_on_edit_dismissed_handles_save_error(self, tmp_path: Path) -> None:
        """Test that save errors are handled gracefully."""
        from unittest.mock import patch

        from mcpax.tui.screens.settings import SettingsScreen

        # Create a test config file
        config_path = tmp_path / "config.toml"
        config_path.write_text("""
[minecraft]
version = "1.21.4"
mod_loader = "fabric"

[paths]
minecraft_dir = "/tmp/.minecraft"
""")

        class TestApp(App[None]):
            def on_mount(self):
                self.push_screen(SettingsScreen(config_path=config_path))

        app = TestApp()
        async with app.run_test():
            screen = app.screen
            table = screen.query_one("#settings-table")
            table.cursor_coordinate = (0, 0)

            # Mock set_config_value to raise an error
            with patch(
                "mcpax.tui.screens.settings.set_config_value",
                side_effect=ValueError("Invalid value"),
            ):
                # Call _on_edit_dismissed with invalid value
                screen._on_edit_dismissed("invalid")

                # Should handle error gracefully
                # _changed should still be False
                assert screen._changed is False

    @pytest.mark.asyncio
    async def test_on_edit_dismissed_cancel_does_not_change_flag(
        self, tmp_path: Path
    ) -> None:
        """Test that canceling edit doesn't set _changed flag."""
        from mcpax.tui.screens.settings import SettingsScreen

        config_path = tmp_path / "config.toml"
        config_path.write_text("""
[minecraft]
version = "1.21.4"
mod_loader = "fabric"

[paths]
minecraft_dir = "/tmp/.minecraft"
""")

        class TestApp(App[None]):
            def on_mount(self):
                self.push_screen(SettingsScreen(config_path=config_path))

        app = TestApp()
        async with app.run_test():
            screen = app.screen

            # Call _on_edit_dismissed with None (cancelled)
            screen._on_edit_dismissed(None)

            # _changed should still be False
            assert screen._changed is False

    @pytest.mark.asyncio
    async def test_on_edit_dismissed_saves_enum_value_not_label(
        self, tmp_path: Path
    ) -> None:
        """Test that enum value (not human label) is saved for Select fields."""
        from unittest.mock import patch

        from mcpax.tui.screens.settings import SettingsScreen

        config_path = tmp_path / "config.toml"
        config_path.write_text("""
[minecraft]
version = "1.21.4"
mod_loader = "fabric"

[paths]
minecraft_dir = "/tmp/.minecraft"
""")

        class TestApp(App[None]):
            def on_mount(self):
                self.push_screen(SettingsScreen(config_path=config_path))

        app = TestApp()
        async with app.run_test():
            screen = app.screen
            table = screen.query_one("#settings-table")

            # Set cursor to mod_loader row (index 1)
            table.cursor_coordinate = (1, 0)

            # Mock set_config_value to verify it receives enum value, not label
            with patch("mcpax.tui.screens.settings.set_config_value") as mock_set:
                # Simulate changing mod_loader to "forge" (enum value)
                # NOT "Forge" (human label)
                screen._on_edit_dismissed("forge")

                # Verify set_config_value was called with enum value
                mock_set.assert_called_once_with(
                    "minecraft.mod_loader", "forge", config_path
                )
                # Ensure it's NOT called with human label "Forge"
                assert mock_set.call_args[0][1] != "Forge"


# Phase 3: Settings Action Tests


class TestSettingsActions:
    """Test settings screen actions."""

    @pytest.mark.asyncio
    async def test_settings_screen_cancel_without_changes(
        self, settings_config_path: Path
    ) -> None:
        """Test that cancel without changes returns False."""
        from mcpax.tui.screens.settings import SettingsScreen

        result = None

        class TestApp(App[None]):
            def on_mount(self):
                self.push_screen(
                    SettingsScreen(config_path=settings_config_path),
                    callback=self.handle_result,
                )

            def handle_result(self, changed: bool | None):
                nonlocal result
                result = changed

        app = TestApp()
        async with app.run_test() as pilot:
            # Press ESC without making changes
            await pilot.press("escape")
            await pilot.pause()

            # Result should be False (no changes)
            assert result is False

    @pytest.mark.asyncio
    async def test_settings_screen_cancel_with_changes(
        self, settings_config_path: Path
    ) -> None:
        """Test that cancel with changes returns True."""

        from mcpax.tui.screens.settings import SettingsScreen

        result = None

        class TestApp(App[None]):
            def on_mount(self):
                self.push_screen(
                    SettingsScreen(config_path=settings_config_path),
                    callback=self.handle_result,
                )

            def handle_result(self, changed: bool | None):
                nonlocal result
                result = changed

        app = TestApp()
        async with app.run_test() as pilot:
            screen = app.screen
            assert isinstance(screen, SettingsScreen)

            # Simulate a change by setting _changed flag
            screen._changed = True

            # Press ESC
            await pilot.press("escape")
            await pilot.pause()

            # Result should be True (changes were made)
            assert result is True

    @pytest.mark.asyncio
    async def test_settings_screen_action_edit_setting_pushes_edit_modal(
        self, settings_config_path: Path
    ) -> None:
        """Test that action_edit_setting pushes EditSettingModal with correct params."""
        from unittest.mock import MagicMock

        from mcpax.tui.screens.settings import EditSettingModal, SettingsScreen

        config_path = settings_config_path
        config_path.write_text("""
[minecraft]
version = "1.21.4"
mod_loader = "fabric"

[paths]
minecraft_dir = "/tmp/.minecraft"
""")

        class TestApp(App[None]):
            def on_mount(self):
                self.push_screen(SettingsScreen(config_path=config_path))

        app = TestApp()
        async with app.run_test():
            screen = app.screen
            table = screen.query_one("#settings-table")

            # Set cursor to first row (minecraft.version)
            table.cursor_coordinate = Coordinate(0, 0)

            # Mock push_screen
            app.push_screen = MagicMock()  # type: ignore

            # Call action_edit_setting
            screen.action_edit_setting()

            # Verify push_screen was called with EditSettingModal
            app.push_screen.assert_called_once()
            args, kwargs = app.push_screen.call_args
            assert isinstance(args[0], EditSettingModal)
            # Check parameters
            modal = args[0]
            assert modal._key == "minecraft.version"
            assert modal._label == "Minecraft Version"
            assert modal._current_value == "1.21.4"

    @pytest.mark.asyncio
    async def test_settings_screen_action_edit_setting_none_value_passes_empty_string(
        self, settings_config_path: Path
    ) -> None:
        """Test that None values are passed as empty string to EditSettingModal."""
        from unittest.mock import MagicMock

        from mcpax.tui.screens.settings import SettingsScreen

        class TestApp(App[None]):
            def on_mount(self):
                self.push_screen(SettingsScreen(config_path=settings_config_path))

        app = TestApp()
        async with app.run_test():
            screen = app.screen
            table = screen.query_one("#settings-table")

            # Set cursor to shader_loader row (index 2) which should be None
            table.cursor_coordinate = Coordinate(2, 0)

            # Mock push_screen
            app.push_screen = MagicMock()  # type: ignore

            # Call action_edit_setting
            screen.action_edit_setting()

            # Verify current_value is empty string
            args, _ = app.push_screen.call_args
            modal = args[0]
            assert modal._current_value == ""

    @pytest.mark.asyncio
    async def test_settings_screen_action_edit_setting_bool_value_passes_string(
        self, settings_config_path: Path
    ) -> None:
        """Test that boolean values are passed as string to EditSettingModal."""
        from unittest.mock import MagicMock

        from mcpax.tui.screens.settings import SettingsScreen

        # Override config with download section
        settings_config_path.write_text("""
[minecraft]
version = "1.21.4"
mod_loader = "fabric"

[paths]
minecraft_dir = "/tmp/.minecraft"

[download]
max_concurrent = 5
verify_hash = true
""")

        class TestApp(App[None]):
            def on_mount(self):
                self.push_screen(SettingsScreen(config_path=settings_config_path))

        app = TestApp()
        async with app.run_test():
            screen = app.screen
            table = screen.query_one("#settings-table")

            # Set cursor to verify_hash row (index 8)
            table.cursor_coordinate = Coordinate(8, 0)

            # Mock push_screen
            app.push_screen = MagicMock()  # type: ignore

            # Call action_edit_setting
            screen.action_edit_setting()

            # Verify current_value is "True" (string)
            args, _ = app.push_screen.call_args
            modal = args[0]
            assert modal._current_value == "True"

    @pytest.mark.asyncio
    async def test_settings_screen_row_selected_delegates_to_edit_setting(
        self, settings_config_path: Path
    ) -> None:
        """Test that DataTable.RowSelected delegates to action_edit_setting."""
        from unittest.mock import MagicMock

        from mcpax.tui.screens.settings import SettingsScreen

        class TestApp(App[None]):
            def on_mount(self):
                self.push_screen(SettingsScreen(config_path=settings_config_path))

        app = TestApp()
        async with app.run_test():
            screen = app.screen

            # Mock action_edit_setting
            screen.action_edit_setting = MagicMock()

            # Simulate pressing Enter (will trigger RowSelected event)
            await app.workers.wait_for_complete()
            table = screen.query_one("#settings-table")

            table.cursor_coordinate = Coordinate(0, 0)

            # Create a mock event object
            class MockEvent:
                pass

            event = MockEvent()
            screen.on_data_table_row_selected(event)

            # Verify action_edit_setting was called
            screen.action_edit_setting.assert_called_once()

    @pytest.mark.asyncio
    async def test_edit_modal_enter_key_saves_value(self, tmp_path: Path) -> None:
        """Test that Enter key saves the value in EditSettingModal."""
        from mcpax.tui.screens.settings import EditSettingModal

        result = None

        class TestApp(App[None]):
            def on_mount(self):
                self.push_screen(
                    EditSettingModal(
                        key="minecraft.version",
                        label="Minecraft Version",
                        current_value="1.21.4",
                    ),
                    callback=self.handle_result,
                )

            def handle_result(self, value: str | None):
                nonlocal result
                result = value

        app = TestApp()
        async with app.run_test() as pilot:
            screen = app.screen
            # Change the input value
            from textual.widgets import Input

            input_widget = screen.query_one(Input)
            input_widget.value = "1.22.0"

            # Press Enter
            await pilot.press("enter")
            await pilot.pause()

            # Result should be the new value
            assert result == "1.22.0"
