"""Settings screen for editing config.toml."""

import logging
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, Footer, Input, Select, Static

from mcpax.core.config import (
    get_all_config_values,
    get_default_config_path,
    set_config_value,
)
from mcpax.core.models import Loader

# Section -> keys mapping for display order
SETTINGS_SECTIONS: dict[str, list[str]] = {
    "Minecraft": [
        "minecraft.version",
        "minecraft.mod_loader",
        "minecraft.shader_loader",
    ],
    "Paths": [
        "paths.minecraft_dir",
        "paths.mods_dir",
        "paths.shaders_dir",
        "paths.resourcepacks_dir",
    ],
    "Download": [
        "download.max_concurrent",
        "download.verify_hash",
    ],
}

# Key -> display label mapping
FIELD_LABELS: dict[str, str] = {
    "minecraft.version": "Minecraft Version",
    "minecraft.mod_loader": "Mod Loader",
    "minecraft.shader_loader": "Shader Loader",
    "paths.minecraft_dir": "Minecraft Directory",
    "paths.mods_dir": "Mods Directory",
    "paths.shaders_dir": "Shaders Directory",
    "paths.resourcepacks_dir": "Resource Packs Directory",
    "download.max_concurrent": "Max Concurrent Downloads",
    "download.verify_hash": "Verify Hash",
}

# Fields that should use Select widget with their choices
SELECT_FIELDS: dict[str, list[tuple[str, str]]] = {
    "minecraft.mod_loader": [
        (Loader.FABRIC.value, "Fabric"),
        (Loader.FORGE.value, "Forge"),
        (Loader.NEOFORGE.value, "NeoForge"),
        (Loader.QUILT.value, "Quilt"),
    ],
    "minecraft.shader_loader": [
        ("", "None"),
        (Loader.IRIS.value, "Iris"),
        (Loader.OPTIFINE.value, "OptiFine"),
    ],
}

# Fields that are boolean
BOOLEAN_FIELDS: set[str] = {
    "download.verify_hash",
}


class SettingsScreen(Screen[bool]):
    """Settings screen for editing config.toml.

    Returns:
        True if settings were changed, False otherwise
    """

    BINDINGS = [
        Binding("escape", "cancel", "Back"),
        Binding("enter", "edit_setting", "Edit"),
    ]

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize SettingsScreen.

        Args:
            config_path: Path to config.toml (defaults to standard config path)
        """
        super().__init__()
        self._config_path = config_path
        self._changed = False
        self._values: dict[str, str | int | bool | None] = {}
        self._ordered_keys: list[str] = []
        # Build reverse map: key -> section name for O(1) lookup
        self._key_to_section: dict[str, str] = {
            key: section
            for section, keys in SETTINGS_SECTIONS.items()
            for key in keys
        }

    def compose(self) -> ComposeResult:
        """Create child widgets.

        Yields:
            Header, DataTable, Footer
        """
        yield Static("Settings", id="settings-header")
        table = DataTable(id="settings-table", cursor_type="row")
        table.add_columns("Section", "Setting", "Value")
        yield table
        yield Footer()

    def on_mount(self) -> None:
        """Load settings when screen is mounted."""
        self._load_settings()
        # Focus the table so cursor is visible and keyboard works
        table = self.query_one("#settings-table", DataTable)
        table.focus()

    def _load_settings(self) -> None:
        """Load settings from config file and populate table."""
        # Get config path
        config_path = self._config_path or get_default_config_path()

        # Try to load all config values
        try:
            self._values = get_all_config_values(config_path)
        except FileNotFoundError:
            # If config file doesn't exist, initialize with None values
            from mcpax.core.config import CONFIG_KEY_MAP

            self._values = {key: None for key in CONFIG_KEY_MAP}

        # Build ordered list of keys from SETTINGS_SECTIONS
        self._ordered_keys = []
        for keys in SETTINGS_SECTIONS.values():
            self._ordered_keys.extend(keys)

        # Populate table
        table = self.query_one("#settings-table", DataTable)
        table.clear()

        current_section = ""
        for key in self._ordered_keys:
            # Get section name from reverse map (O(1) lookup)
            section_name = self._key_to_section.get(key, "")

            # Only show section name on first occurrence
            display_section = section_name if section_name != current_section else ""
            current_section = section_name

            # Get display label
            label = FIELD_LABELS[key]

            # Format value
            value = self._values.get(key)
            if value is None:
                display_value = "(not set)"
            elif isinstance(value, bool):
                display_value = str(value)
            else:
                display_value = str(value)

            # Add row
            table.add_row(display_section, label, display_value)

    def action_cancel(self) -> None:
        """Cancel and return to main screen."""
        self.dismiss(self._changed)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection (Enter key or click) in the data table.

        Args:
            event: Row selected event
        """
        self.action_edit_setting()

    def action_edit_setting(self) -> None:
        """Edit the selected setting."""
        table = self.query_one("#settings-table", DataTable)

        # Get cursor position
        if table.cursor_coordinate is None:
            return

        row_index = table.cursor_coordinate.row

        # Get the key for this row
        if row_index >= len(self._ordered_keys):
            return

        key = self._ordered_keys[row_index]
        label = FIELD_LABELS[key]

        # Get current value
        value = self._values.get(key)
        if value is None:
            current_value = ""
        elif isinstance(value, bool):
            current_value = str(value)
        else:
            current_value = str(value)

        # Push the edit modal
        self.app.push_screen(
            EditSettingModal(key=key, label=label, current_value=current_value),
            callback=self._on_edit_dismissed,
        )

    def _on_edit_dismissed(self, new_value: str | None) -> None:
        """Handle edit modal dismissal.

        Args:
            new_value: New value from modal, or None if cancelled
        """
        if new_value is None:
            # Cancelled
            return

        # Get current cursor position to determine which key was edited
        table = self.query_one("#settings-table", DataTable)
        if table.cursor_coordinate is None:
            return

        row_index = table.cursor_coordinate.row
        if row_index >= len(self._ordered_keys):
            return

        key = self._ordered_keys[row_index]

        # Save the value
        config_path = self._config_path or get_default_config_path()
        try:
            set_config_value(key, new_value, config_path)
            self._changed = True
            # Reload settings to reflect the change
            self._load_settings()
        except (ValueError, FileNotFoundError) as exc:
            logging.exception("Failed to save setting %s=%s", key, new_value)
            self.notify(f"Failed to save setting: {exc}", severity="error")


class EditSettingModal(ModalScreen[str | None]):
    """Modal screen for editing a single setting.

    Returns:
        New value as string, or None if cancelled
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, key: str, label: str, current_value: str) -> None:
        """Initialize EditSettingModal.

        Args:
            key: Config key (e.g., "minecraft.version")
            label: Display label for the setting
            current_value: Current value as string
        """
        super().__init__()
        self._key = key
        self._label = label
        self._current_value = current_value

    def compose(self) -> ComposeResult:
        """Create child widgets.

        Yields:
            Container with input field and buttons
        """
        with Container(id="edit-setting-container"):
            yield Static(f"Edit {self._label}", id="edit-setting-header")

            # Determine which widget to use
            if self._key in SELECT_FIELDS:
                # Use Select widget
                choices = SELECT_FIELDS[self._key]
                # Convert (value, label) to (prompt/label, value) for Select widget
                # Textual Select expects (prompt, value) tuples
                select_options = [(label, value) for value, label in choices]
                # Use current value (enum value, not label)
                initial = self._current_value
                yield Select(
                    select_options, value=initial, id="setting-input", allow_blank=False
                )
            elif self._key in BOOLEAN_FIELDS:
                # Use Select widget for boolean
                select_options = [("True", "True"), ("False", "False")]
                yield Select(
                    select_options,
                    value=self._current_value,
                    id="setting-input",
                    allow_blank=False,
                )
            else:
                # Use Input widget
                yield Input(value=self._current_value, id="setting-input")

            # Buttons
            with Horizontal(id="button-row"):
                yield Button("Save", variant="primary", id="save-button")
                yield Button("Cancel", id="cancel-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press.

        Args:
            event: Button press event
        """
        if event.button.id == "save-button":
            self._save()
        elif event.button.id == "cancel-button":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in Input widget.

        Args:
            event: Input submitted event
        """
        self._save()

    def _save(self) -> None:
        """Save the new value and dismiss."""
        # Get the new value from the input widget
        widget = self.query_one("#setting-input")
        if isinstance(widget, Select):
            new_value = str(widget.value)
        else:
            assert isinstance(widget, Input)
            new_value = widget.value

        self.dismiss(new_value)

    def action_cancel(self) -> None:
        """Cancel and dismiss."""
        self.dismiss(None)
