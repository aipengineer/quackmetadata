import os
import tempfile
import inspect
from logging import Logger
from typing import Any, cast

from quackcore.fs.service import get_service
from quackcore.integrations.core.results import IntegrationResult
from quackcore.logging import get_logger
from quackcore.plugins.protocols import QuackPluginMetadata

from quackmetadata.plugins.metadata import MetadataPlugin
from quackmetadata.protocols import QuackToolPluginProtocol
from quackmetadata.version import __version__

# Use QuackCore FS for all file operations
fs = get_service()

# Registry to enforce a singleton plugin instance
_PLUGIN_REGISTRY: dict[str, QuackToolPluginProtocol] = {}
_LOGGER = get_logger(__name__)

# Determine the lock directory using QuackCore Paths if available
try:
    from quackcore.paths import service as paths
    project_context = paths.detect_project_context()
    base_temp = project_context.get_temp_dir() or tempfile.gettempdir()
except Exception:
    base_temp = tempfile.gettempdir()

# Join via FS, then extract a clean string path for the lock directory
_raw_lock_dir = fs.join_path(str(base_temp), "quackmetadata")
_LOCK_DIR = (
    str(_raw_lock_dir.path) if hasattr(_raw_lock_dir, "path") else str(_raw_lock_dir)
)
# Ensure the lock directory exists
fs.create_directory(_LOCK_DIR, exist_ok=True)

# Build the path for the lock file
_raw_lock_file = fs.join_path(_LOCK_DIR, "instance.lock")
_LOCK_FILE = (
    str(_raw_lock_file.path) if hasattr(_raw_lock_file, "path") else str(_raw_lock_file)
)

def _check_other_instances() -> tuple[bool, str]:
    """
    Prevent concurrent CLI sessions by using a lock file.
    Returns a tuple of (is_running, message).
    """
    try:
        info = fs.get_file_info(_LOCK_FILE)
        if info.success and info.exists:
            stats = getattr(info, "stats", None)
            if stats and hasattr(stats, "st_mtime"):
                import time
                if time.time() - stats.st_mtime < 600:
                    read = fs.read_text(_LOCK_FILE, encoding="utf-8")
                    if read.success:
                        pid = read.content.strip()
                        return True, f"Another instance is running (PID: {pid})"
                    return True, "Another instance is running"
        # Write our PID to lock file
        pid_str = str(os.getpid())
        write = fs.write_text(_LOCK_FILE, pid_str, encoding="utf-8", atomic=True)
        if not write.success:
            _LOGGER.warning(f"Could not write lock file: {write.error}")
        return False, "No other instances detected"
    except Exception as e:
        _LOGGER.warning(f"Lock check error: {e}")
        return False, f"Error checking lock: {e}"

class QuackMetadataPlugin(QuackToolPluginProtocol):
    """Singleton QuackMetadata plugin."""
    _instance: Any = None
    _logger: Logger = None
    _metadata_plugin: Any = None
    _project_name: str = "QuackMetadata"

    def __new__(cls) -> "QuackMetadataPlugin":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
            cls._logger = get_logger(__name__)
            try:
                from quackcore.config import load_config
                cfg = load_config()
                if hasattr(cfg, "general") and hasattr(cfg.general, "project_name"):
                    cls._project_name = cfg.general.project_name
            except Exception:
                cls._logger.debug("Could not load project name from config.")
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = False
        self._metadata_plugin = None

    @property
    def logger(self) -> Logger:
        return self.__class__._logger

    @property
    def name(self) -> str:
        return self.__class__._project_name

    @property
    def version(self) -> str:
        return __version__

    def get_metadata(self) -> QuackPluginMetadata:
        return QuackPluginMetadata(
            name=self.name,
            version=self.version,
            description=(
                "QuackMetadata plugin: download from Drive, extract metadata via LLM, validate, and upload back."
            ),
            author="AI Product Engineer Team",
            capabilities=[
                "download file",
                "LLM-based metadata extraction",
                "metadata validation",
                "upload file",
            ],
        )

    def initialize(self) -> IntegrationResult:
        try:
            running, msg = _check_other_instances()
            if running:
                return IntegrationResult.error_result(
                    f"Cannot initialize {self.name}: {msg}."
                )
            self._metadata_plugin = MetadataPlugin()
            init = self._metadata_plugin.initialize()
            if not init.success:
                return init
            self._initialized = True
            return IntegrationResult.success_result(
                message=f"{self.name} initialized successfully"
            )
        except Exception as e:
            self.logger.error(f"Initialization error: {e}")
            return IntegrationResult.error_result(f"Initialization error: {e}")

    def is_available(self) -> bool:
        return self._initialized

    def process_file(
        self,
        file_path: str,
        output_path: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> IntegrationResult:
        if not self._initialized:
            init = self.initialize()
            if not init.success:
                return init
        try:
            self.logger.info(f"Processing: {file_path}")
            return self._metadata_plugin.process_file(
                file_path=file_path,
                output_path=output_path,
                options=options,
            )
        except Exception as e:
            self.logger.error(f"Processing error: {e}")
            return IntegrationResult.error_result(f"Processing error: {e}")

    def __del__(self) -> None:
        try:
            info = fs.get_file_info(_LOCK_FILE)
            if info.success and info.exists:
                txt = fs.read_text(_LOCK_FILE, encoding="utf-8")
                if txt.success and txt.content.strip() == str(os.getpid()):
                    fs.delete(_LOCK_FILE)
        except Exception:
            pass

def create_plugin() -> QuackToolPluginProtocol:
    key = "quackmetadata_plugin"
    if key in _PLUGIN_REGISTRY:
        inst = cast(QuackMetadataPlugin, _PLUGIN_REGISTRY[key])
        inst._initialized = False
        return inst
    inst = QuackMetadataPlugin()
    inst._initialized = False
    _PLUGIN_REGISTRY[key] = inst
    _LOGGER.debug(f"Plugin registered under key: {key}")
    return inst
