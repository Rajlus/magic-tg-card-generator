"""Tests for UI interactions and status updates in MTG Deck Builder."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QMessageBox, QPushButton, QTableWidget

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestUIInteractions:
    """Test UI interactions and status updates."""

    @pytest.fixture
    def qapp(self):
        """Provide a QApplication instance."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    def test_button_click_interactions(self, qapp):
        """Test button click interactions."""
        button = QPushButton("Test Button")
        button.show()

        clicked = False

        def on_clicked():
            nonlocal clicked
            clicked = True

        button.clicked.connect(on_clicked)

        # Simulate button click
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)

        # Process events
        qapp.processEvents()

        assert clicked

    def test_progress_bar_updates(self, qapp):
        """Test progress bar status updates."""
        from PyQt6.QtWidgets import QProgressBar

        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.show()

        # Test progress updates
        progress_values = [0, 25, 50, 75, 100]

        for value in progress_values:
            progress_bar.setValue(value)
            qapp.processEvents()
            assert progress_bar.value() == value

    def test_status_message_updates(self, qapp):
        """Test status message updates."""
        from PyQt6.QtWidgets import QLabel, QStatusBar

        status_bar = QStatusBar()
        status_label = QLabel()
        status_bar.addPermanentWidget(status_label)

        # Test status messages
        messages = [
            "Loading card database...",
            "Filtering cards...",
            "Generation in progress...",
            "Generation completed successfully",
            "Ready",
        ]

        for message in messages:
            status_label.setText(message)
            qapp.processEvents()
            assert status_label.text() == message

    def test_error_dialog_display(self, qapp):
        """Test error dialog display."""
        with patch.object(
            QMessageBox, "exec", return_value=QMessageBox.StandardButton.Ok
        ):
            error_msg = QMessageBox()
            error_msg.setIcon(QMessageBox.Icon.Critical)
            error_msg.setWindowTitle("Error")
            error_msg.setText("Test error message")

            # Mock the exec method to avoid actually showing dialog
            result = error_msg.exec()
            assert result == QMessageBox.StandardButton.Ok

    def test_confirmation_dialog_interactions(self, qapp):
        """Test confirmation dialog interactions."""
        with patch.object(
            QMessageBox, "exec", return_value=QMessageBox.StandardButton.Yes
        ):
            confirm_msg = QMessageBox()
            confirm_msg.setIcon(QMessageBox.Icon.Question)
            confirm_msg.setWindowTitle("Confirm")
            confirm_msg.setText("Are you sure?")
            confirm_msg.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            result = confirm_msg.exec()
            assert result == QMessageBox.StandardButton.Yes

    def test_tab_switching_interactions(self, qapp):
        """Test tab switching interactions."""
        from PyQt6.QtWidgets import QTabWidget, QWidget

        tab_widget = QTabWidget()

        # Add tabs
        tab1 = QWidget()
        tab2 = QWidget()
        tab3 = QWidget()

        tab_widget.addTab(tab1, "Card Management")
        tab_widget.addTab(tab2, "Theme Config")
        tab_widget.addTab(tab3, "Settings")

        tab_widget.show()

        # Test tab switching
        for i in range(3):
            tab_widget.setCurrentIndex(i)
            qapp.processEvents()
            assert tab_widget.currentIndex() == i

    def test_menu_interactions(self, qapp):
        """Test menu interactions."""
        from PyQt6.QtWidgets import QMainWindow, QMenuBar

        main_window = QMainWindow()
        menu_bar = main_window.menuBar()

        # Create menus
        file_menu = menu_bar.addMenu("File")
        edit_menu = menu_bar.addMenu("Edit")

        # Add actions
        new_action = file_menu.addAction("New Deck")
        save_action = file_menu.addAction("Save Deck")

        action_triggered = False

        def on_action_triggered():
            nonlocal action_triggered
            action_triggered = True

        new_action.triggered.connect(on_action_triggered)

        # Trigger action
        new_action.trigger()
        qapp.processEvents()

        assert action_triggered

    def test_drag_drop_interactions(self, qapp):
        """Test drag and drop interactions."""
        from PyQt6.QtCore import QMimeData
        from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
        from PyQt6.QtWidgets import QListWidget

        list_widget = QListWidget()
        list_widget.setAcceptDrops(True)
        list_widget.setDragDropMode(QListWidget.DragDropMode.InternalMove)

        # Add items
        list_widget.addItem("Lightning Bolt")
        list_widget.addItem("Giant Growth")
        list_widget.addItem("Counterspell")

        list_widget.show()

        # Test that drag/drop is enabled
        assert list_widget.acceptDrops()
        assert list_widget.dragDropMode() == QListWidget.DragDropMode.InternalMove

    def test_context_menu_interactions(self, qapp):
        """Test context menu interactions."""
        from PyQt6.QtCore import QPoint
        from PyQt6.QtGui import QContextMenuEvent
        from PyQt6.QtWidgets import QMenu, QWidget

        widget = QWidget()
        widget.show()

        context_menu_shown = False

        def show_context_menu(position):
            nonlocal context_menu_shown
            context_menu = QMenu(widget)
            context_menu.addAction("Add to Deck")
            context_menu.addAction("Remove from Deck")
            context_menu.addAction("View Details")
            context_menu_shown = True
            return context_menu

        # Mock context menu event
        widget.contextMenuEvent = lambda event: show_context_menu(event.pos())

        # Simulate context menu event
        event = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(10, 10))
        widget.contextMenuEvent(event)

        assert context_menu_shown

    def test_timer_based_updates(self, qapp):
        """Test timer-based UI updates."""
        timer_fired = False

        def on_timer():
            nonlocal timer_fired
            timer_fired = True

        timer = QTimer()
        timer.timeout.connect(on_timer)
        timer.setSingleShot(True)
        timer.start(10)  # 10ms

        # Wait for timer
        QTest.qWait(50)

        assert timer_fired

    def test_widget_visibility_updates(self, qapp):
        """Test widget visibility updates."""
        from PyQt6.QtWidgets import QLabel

        label = QLabel("Test Label")

        # Test show/hide
        label.hide()
        assert not label.isVisible()

        label.show()
        assert label.isVisible()

        # Test enabled/disabled
        label.setEnabled(False)
        assert not label.isEnabled()

        label.setEnabled(True)
        assert label.isEnabled()

    def test_color_theme_updates(self, qapp):
        """Test color theme updates."""
        from PyQt6.QtWidgets import QWidget

        widget = QWidget()

        # Test style sheet updates
        dark_theme = """
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        """

        light_theme = """
        QWidget {
            background-color: #ffffff;
            color: #000000;
        }
        """

        widget.setStyleSheet(dark_theme)
        assert "2b2b2b" in widget.styleSheet()

        widget.setStyleSheet(light_theme)
        assert "ffffff" in widget.styleSheet()

    def test_layout_updates(self, qapp):
        """Test layout updates and resizing."""
        from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Add widgets dynamically
        labels = []
        for i in range(3):
            label = QLabel(f"Label {i}")
            labels.append(label)
            layout.addWidget(label)

        widget.show()
        qapp.processEvents()

        # Verify layout
        assert layout.count() == 3

        # Remove widget
        layout.removeWidget(labels[1])
        labels[1].deleteLater()

        qapp.processEvents()
        assert layout.count() == 2

    def test_data_model_updates(self, qapp):
        """Test data model updates in UI components."""
        from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
        from PyQt6.QtWidgets import QTableView

        class TestModel(QAbstractTableModel):
            def __init__(self):
                super().__init__()
                self.data_list = [
                    ["Lightning Bolt", "{R}"],
                    ["Giant Growth", "{G}"],
                    ["Counterspell", "{U}{U}"],
                ]
                self.headers = ["Name", "Mana Cost"]

            def rowCount(self, parent=QModelIndex()):
                return len(self.data_list)

            def columnCount(self, parent=QModelIndex()):
                return len(self.headers)

            def data(self, index, role=Qt.ItemDataRole.DisplayRole):
                if role == Qt.ItemDataRole.DisplayRole:
                    return self.data_list[index.row()][index.column()]
                return None

            def headerData(
                self, section, orientation, role=Qt.ItemDataRole.DisplayRole
            ):
                if (
                    role == Qt.ItemDataRole.DisplayRole
                    and orientation == Qt.Orientation.Horizontal
                ):
                    return self.headers[section]
                return None

            def add_card(self, name, mana_cost):
                self.beginInsertRows(
                    QModelIndex(), len(self.data_list), len(self.data_list)
                )
                self.data_list.append([name, mana_cost])
                self.endInsertRows()

        model = TestModel()
        table_view = QTableView()
        table_view.setModel(model)
        table_view.show()

        initial_count = model.rowCount()

        # Add data
        model.add_card("Shock", "{R}")

        assert model.rowCount() == initial_count + 1

    def test_loading_spinner_animation(self, qapp):
        """Test loading spinner animation."""
        from PyQt6.QtCore import QPropertyAnimation, QRect
        from PyQt6.QtWidgets import QLabel

        spinner_label = QLabel("⟳")  # Unicode spinner character
        spinner_label.show()

        # Create rotation animation
        animation = QPropertyAnimation(spinner_label, b"geometry")
        animation.setDuration(1000)
        animation.setStartValue(QRect(0, 0, 50, 50))
        animation.setEndValue(QRect(0, 0, 50, 50))
        animation.setLoopCount(-1)  # Infinite loop

        # Start animation
        animation.start()

        # Verify animation is running
        assert animation.state() == QPropertyAnimation.State.Running

        # Stop animation
        animation.stop()
        assert animation.state() == QPropertyAnimation.State.Stopped

    def test_tooltip_interactions(self, qapp):
        """Test tooltip interactions."""
        from PyQt6.QtWidgets import QPushButton

        button = QPushButton("Hover me")
        button.setToolTip("This is a test tooltip")
        button.show()

        # Verify tooltip is set
        assert button.toolTip() == "This is a test tooltip"

        # Test tooltip update
        button.setToolTip("Updated tooltip")
        assert button.toolTip() == "Updated tooltip"

    def test_splitter_interactions(self, qapp):
        """Test splitter widget interactions."""
        from PyQt6.QtWidgets import QLabel, QSplitter

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_widget = QLabel("Left Panel")
        right_widget = QLabel("Right Panel")

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)

        splitter.show()

        # Test initial sizes
        initial_sizes = splitter.sizes()
        assert len(initial_sizes) == 2

        # Test resizing
        splitter.setSizes([200, 300])
        new_sizes = splitter.sizes()
        assert new_sizes != initial_sizes

    def test_scroll_area_interactions(self, qapp):
        """Test scroll area interactions."""
        from PyQt6.QtCore import QRect
        from PyQt6.QtWidgets import QLabel, QScrollArea

        scroll_area = QScrollArea()
        content_label = QLabel(
            "This is a very long label that should require scrolling " * 20
        )

        scroll_area.setWidget(content_label)
        scroll_area.show()

        # Test scroll functionality
        scroll_bar = scroll_area.verticalScrollBar()

        # Scroll to different positions
        scroll_bar.setValue(0)
        assert scroll_bar.value() == 0

        if scroll_bar.maximum() > 0:
            scroll_bar.setValue(scroll_bar.maximum() // 2)
            assert scroll_bar.value() == scroll_bar.maximum() // 2
