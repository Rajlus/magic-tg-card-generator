"""Test cases for the CardToolbar widget."""

from unittest.mock import Mock

import pytest
from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QApplication

from src.ui.widgets.card_toolbar import CardToolbar


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def card_toolbar(qapp):  # noqa: ARG001
    """Create a CardToolbar instance for testing."""
    return CardToolbar()


class TestCardToolbar:
    """Test cases for CardToolbar widget."""

    def test_initialization(self, card_toolbar):
        """Test that the toolbar initializes correctly."""
        assert card_toolbar is not None
        assert hasattr(card_toolbar, "load_button")
        assert hasattr(card_toolbar, "reload_button")
        assert hasattr(card_toolbar, "csv_import_button")
        assert hasattr(card_toolbar, "csv_export_button")
        assert hasattr(card_toolbar, "generate_all_btn")
        assert hasattr(card_toolbar, "config_button")
        assert hasattr(card_toolbar, "auto_save_label")

    def test_signals_exist(self, card_toolbar):
        """Test that all required signals are defined."""
        # File operation signals
        assert hasattr(card_toolbar, "load_deck_requested")
        assert hasattr(card_toolbar, "reload_deck_requested")

        # Import/Export signals
        assert hasattr(card_toolbar, "import_csv_requested")
        assert hasattr(card_toolbar, "export_csv_requested")

        # Generation signals
        assert hasattr(card_toolbar, "generate_all_requested")

        # Configuration signals
        assert hasattr(card_toolbar, "toggle_config_requested")

    def test_auto_save_status_update(self, card_toolbar):
        """Test auto-save status indicator updates correctly."""
        # Test active state
        card_toolbar.set_auto_save_status(True)
        assert "Active" in card_toolbar.auto_save_label.text()

        # Test inactive state
        card_toolbar.set_auto_save_status(False)
        assert "Inactive" in card_toolbar.auto_save_label.text()

    def test_button_enable_disable(self, card_toolbar):
        """Test button enable/disable functionality."""
        # Test individual button controls
        card_toolbar.set_reload_enabled(False)
        assert not card_toolbar.reload_button.isEnabled()

        card_toolbar.set_generation_enabled(False)
        assert not card_toolbar.generate_all_btn.isEnabled()

        card_toolbar.set_export_enabled(False)
        assert not card_toolbar.csv_export_button.isEnabled()

        # Test enabling buttons
        card_toolbar.set_reload_enabled(True)
        assert card_toolbar.reload_button.isEnabled()

        card_toolbar.set_generation_enabled(True)
        assert card_toolbar.generate_all_btn.isEnabled()

        card_toolbar.set_export_enabled(True)
        assert card_toolbar.csv_export_button.isEnabled()

    def test_config_button_state(self, card_toolbar):
        """Test config button state updates."""
        # Test expanded state
        card_toolbar.update_config_button_state(True)
        assert "▼" in card_toolbar.config_button.text()

        # Test collapsed state
        card_toolbar.update_config_button_state(False)
        assert "▲" in card_toolbar.config_button.text()

    def test_all_buttons_enable_disable(self, card_toolbar):
        """Test enable/disable all buttons functionality."""
        # Disable all buttons
        card_toolbar.set_all_buttons_enabled(False)
        states = card_toolbar.get_button_states()

        assert not states["load_enabled"]
        assert not states["reload_enabled"]
        assert not states["import_enabled"]
        assert not states["export_enabled"]
        assert not states["generate_enabled"]
        assert not states["config_enabled"]

        # Enable all buttons
        card_toolbar.set_all_buttons_enabled(True)
        states = card_toolbar.get_button_states()

        assert states["load_enabled"]
        assert states["reload_enabled"]
        assert states["import_enabled"]
        assert states["export_enabled"]
        assert states["generate_enabled"]
        assert states["config_enabled"]

    def test_signal_emission(self, card_toolbar, qapp):
        """Test that signals are emitted when buttons are clicked."""
        # Create mock receivers
        load_mock = Mock()
        reload_mock = Mock()
        import_mock = Mock()
        export_mock = Mock()
        generate_mock = Mock()
        config_mock = Mock()

        # Connect signals to mocks
        card_toolbar.load_deck_requested.connect(load_mock)
        card_toolbar.reload_deck_requested.connect(reload_mock)
        card_toolbar.import_csv_requested.connect(import_mock)
        card_toolbar.export_csv_requested.connect(export_mock)
        card_toolbar.generate_all_requested.connect(generate_mock)
        card_toolbar.toggle_config_requested.connect(config_mock)

        # Simulate button clicks
        card_toolbar.load_button.click()
        load_mock.assert_called_once()

        card_toolbar.reload_button.click()
        reload_mock.assert_called_once()

        card_toolbar.csv_import_button.click()
        import_mock.assert_called_once()

        card_toolbar.csv_export_button.click()
        export_mock.assert_called_once()

        card_toolbar.generate_all_btn.click()
        generate_mock.assert_called_once()

        card_toolbar.config_button.click()
        config_mock.assert_called_once()
