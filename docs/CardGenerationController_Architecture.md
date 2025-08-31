# CardGenerationController Architecture Design

## Overview

The `CardGenerationController` is designed following the established manager patterns in the MTG Card Generator codebase. It encapsulates all card generation workflows while maintaining clean separation of concerns and testability through dependency injection.

## Architecture Patterns

### 1. QObject-Based Manager Pattern
```python
class CardGenerationController(QObject):
    # Signal-based communication
    generation_started = pyqtSignal(int, str)
    generation_progress = pyqtSignal(int, int, str)
    generation_completed = pyqtSignal(list, object)
    card_status_changed = pyqtSignal(object, str)
    error_occurred = pyqtSignal(str, str)
```

**Follows**: `CardTableManager` pattern with PyQt signals for UI communication.

### 2. Dependency Injection Pattern
```python
def __init__(
    self,
    parent_widget: QWidget,
    logger: Optional[Logger] = None,
    progress_reporter: Optional[ProgressReporter] = None,
    status_updater: Optional[StatusUpdater] = None,
    generation_worker: Optional[GenerationWorker] = None,
    config: Optional[GenerationConfig] = None,
):
```

**Follows**: `CardFileOperations` pattern with protocol-based injection for testability.

### 3. Protocol-Based Interfaces
```python
class Logger(Protocol):
    def log_message(self, level: str, message: str) -> None: ...

class ProgressReporter(Protocol):
    def update_progress(self, current: int, total: int, message: str = "") -> None: ...

class StatusUpdater(Protocol):
    def update_card_status(self, card: MTGCard, status: str) -> None: ...
```

**Follows**: `CardFileOperations` protocol pattern for loose coupling and testability.

### 4. Context Manager Support
```python
def __enter__(self):
    """Enter context manager for batch generation operations."""
    return self

def __exit__(self, exc_type, exc_val, exc_tb):
    """Exit context manager and cleanup resources."""
    if self._is_generation_active:
        self.stop_generation()
```

**Follows**: Both existing managers support context manager pattern for resource management.

## Integration with CardManagementTab

### Initialization Pattern
```python
class CardManagementTab(QWidget):
    def __init__(self):
        super().__init__()

        # Initialize generation controller with dependency injection
        self.generation_controller = CardGenerationController(
            parent_widget=self,
            logger=self._create_logger(),
            progress_reporter=self._create_progress_reporter(),
            status_updater=self._create_status_updater(),
            generation_worker=self.generator_worker,  # Existing worker
            config=self._create_generation_config()
        )

        # Connect signals
        self.generation_controller.generation_started.connect(self._on_generation_started)
        self.generation_controller.generation_progress.connect(self._on_generation_progress)
        self.generation_controller.generation_completed.connect(self._on_generation_completed)
        self.generation_controller.card_status_changed.connect(self._on_card_status_changed)
```

### Signal Integration
The controller integrates with existing UI patterns through signals:

1. **Generation Progress**: Updates existing progress bars and status indicators
2. **Card Status Changes**: Triggers table refresh through `CardTableManager`
3. **Completion Events**: Updates statistics and UI state
4. **Error Handling**: Shows user-friendly error messages

## Core Features

### 1. Generation Modes
```python
class GenerationMode(str, Enum):
    CARDS_ONLY = "cards_only"
    ARTWORK_ONLY = "artwork_only"
    COMPLETE = "complete"
    ART_DESCRIPTIONS = "art_descriptions"
    MISSING_ONLY = "missing_only"
    REGENERATE = "regenerate"
```

### 2. Configuration Management
```python
class GenerationConfig:
    def __init__(
        self,
        output_directory: Optional[Path] = None,
        concurrent_workers: int = 1,
        retry_attempts: int = 3,
        timeout_seconds: int = 300,
        generate_images: bool = True,
        generate_artwork: bool = True,
        use_existing_artwork: bool = True,
        ai_art_descriptions: bool = False,
        batch_size: int = 10,
    ):
```

### 3. Statistics Tracking
```python
class GenerationStatistics:
    def __init__(self):
        self.total_cards = 0
        self.pending_cards = 0
        self.generating_cards = 0
        self.completed_cards = 0
        self.failed_cards = 0
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.errors: list[str] = []
```

### 4. Validation System
```python
def validate_cards_for_generation(self, cards: list[MTGCard]) -> list[str]:
    """Validate cards meet generation requirements."""

def validate_generation_environment(self) -> list[str]:
    """Validate system configuration for generation."""
```

## API Design

### Public Methods

#### Generation Control
- `start_generation(cards, mode, **kwargs) -> bool`
- `stop_generation() -> bool`
- `pause_generation() -> bool`
- `resume_generation() -> bool`
- `is_generation_active() -> bool`

#### Batch Operations
- `generate_missing_cards(cards) -> bool`
- `generate_failed_cards(cards) -> bool`
- `regenerate_selected_cards(cards) -> bool`
- `generate_art_descriptions(cards) -> bool`

#### Statistics & Analysis
- `get_generation_statistics(cards) -> dict`
- `get_cards_by_status(cards, status) -> list[MTGCard]`
- `get_pending_cards(cards) -> list[MTGCard]`
- `get_completed_cards(cards) -> list[MTGCard]`
- `get_failed_cards(cards) -> list[MTGCard]`

#### Validation
- `validate_cards_for_generation(cards) -> list[str]`
- `validate_generation_environment() -> list[str]`

## Error Handling Patterns

### 1. Graceful Degradation
```python
def _show_error(self, title: str, message: str) -> None:
    try:
        QMessageBox.critical(self.parent_widget, title, message)
    except (TypeError, AttributeError):
        # Fallback for testing or when parent_widget is mock/None
        self._log("ERROR", f"{title}: {message}")
    finally:
        self.error_occurred.emit(title, message)
```

### 2. Comprehensive Validation
- Card field validation before generation
- Environment validation (scripts, directories)
- Configuration validation
- Runtime state validation

### 3. Recovery Mechanisms
- Automatic retry for failed generations
- Status synchronization after errors
- Resource cleanup on failures

## Thread Safety

### Worker Integration
The controller integrates with existing `CardGeneratorWorker` pattern:
```python
# Connect worker signals if available
if hasattr(self.generation_worker, "progress"):
    self.generation_worker.progress.connect(self._on_worker_progress)
if hasattr(self.generation_worker, "completed"):
    self.generation_worker.completed.connect(self._on_worker_completed)
if hasattr(self.generation_worker, "error"):
    self.generation_worker.error.connect(self._on_worker_error)
```

### Batch Processing Fallback
When no worker is available, provides timer-based batch processing:
```python
def _process_batch(self):
    """Process a batch of cards from the queue."""
    batch_size = min(self.config.batch_size, len(self._generation_queue))
    current_batch = self._generation_queue[:batch_size]
    # Process batch...
```

## Testing Strategy

### Protocol-Based Testing
All dependencies are protocol-based, enabling easy mocking:
```python
class MockLogger:
    def log_message(self, level: str, message: str) -> None:
        self.logged_messages.append((level, message))

class MockProgressReporter:
    def update_progress(self, current: int, total: int, message: str = "") -> None:
        self.progress_updates.append((current, total, message))
```

### Unit Test Coverage
- Generation workflow validation
- Status transitions
- Error handling scenarios
- Configuration management
- Statistics calculation

### Integration Test Coverage
- CardManagementTab integration
- Signal propagation
- UI state synchronization
- File system operations

## Performance Considerations

### 1. Batch Processing
- Configurable batch size for memory management
- Timer-based processing to avoid UI blocking
- Queue management for large card sets

### 2. Memory Management
- Context manager support for resource cleanup
- Proper signal disconnection
- Queue size limits and monitoring

### 3. Progress Reporting
- Efficient progress calculation
- Configurable update frequency
- Indeterminate mode for unknown durations

## Future Extensions

### 1. Plugin Architecture
The protocol-based design allows for easy extension:
```python
class CustomGenerationWorker:
    def start_generation(self, cards, mode, **kwargs):
        # Custom generation logic
```

### 2. Advanced Statistics
- Generation time analytics
- Success/failure pattern analysis
- Performance metrics per generation mode

### 3. Configuration Persistence
- Save/load generation configurations
- User-specific settings
- Project-specific settings

## Usage Examples

### Basic Generation
```python
# Initialize controller
controller = CardGenerationController(parent_widget, logger=logger)

# Start generation
success = controller.start_generation(cards, GenerationMode.COMPLETE)
```

### Batch Operations
```python
# Generate only missing cards
controller.generate_missing_cards(all_cards)

# Retry failed cards
controller.generate_failed_cards(all_cards)

# Regenerate specific cards
selected_cards = get_selected_cards()
controller.regenerate_selected_cards(selected_cards)
```

### Configuration Management
```python
# Custom configuration
config = GenerationConfig(
    concurrent_workers=4,
    batch_size=20,
    generate_artwork=True,
    ai_art_descriptions=True
)
controller.update_config(config)
```

### Statistics and Monitoring
```python
# Get current statistics
stats = controller.get_generation_statistics(cards)
print(f"Completion rate: {stats['completion_rate']:.1f}%")

# Filter cards by status
pending = controller.get_pending_cards(cards)
failed = controller.get_failed_cards(cards)
```

This architecture provides a robust, extensible, and maintainable foundation for card generation workflows while maintaining consistency with the existing codebase patterns.
