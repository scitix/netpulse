import importlib
import logging
from pathlib import Path
from typing import Any, Callable, Dict, Generic, Type, TypeVar

from ..utils import g_config
from .credentials import BaseCredentialProvider
from .drivers import BaseDriver
from .schedulers import BaseScheduler
from .templates import BaseTemplateParser, BaseTemplateRenderer
from .webhooks import BaseWebHookCaller

T = TypeVar("T")
log = logging.getLogger(__name__)


class PluginLoader(Generic[T]):
    """
    Dynamic loader for plugins.
    """

    def __init__(
        self,
        plugin_dir: str,
        plugin_base_cls: Type[T],
        plugin_type: str = "plugin",
        plugin_name_attr: str = "plugin_name",
    ):
        """
        Args:
            plugin_dir: plugin directory
            plugin_base_cls: base class for plugins
            plugin_type: type of plugin
            plugin_name_attr: name attribute for plugin
        """
        self.base_class = plugin_base_cls
        self.type = plugin_type
        self.name_attr = plugin_name_attr
        self.load_dir = Path(plugin_dir)

    def load(self) -> Dict[str, Type[T]]:
        """Load plugin from directory"""
        plugin_dict = {}

        if not self.load_dir.is_dir():
            log.error(f"{self.type.title()} directory not found: {self.load_dir}")
            return plugin_dict

        for pkg_path in self.load_dir.iterdir():
            if self._is_valid_package(pkg_path):
                self._load_package(pkg_path, plugin_dict)

        return plugin_dict

    def _is_valid_package(self, path: Path) -> bool:
        return path.is_dir() and (path / "__init__.py").exists()

    def _is_valid_class(self, cls: Any) -> bool:
        """Check if class is a valid plugin class"""
        return isinstance(cls, type) and issubclass(cls, self.base_class) and cls != self.base_class

    def _load_package(self, pkg_path: Path, plugin_dict: Dict[str, Type[T]]) -> None:
        """Load a single plugin package"""
        package_name = self._generate_package_name(pkg_path)
        try:
            module = importlib.import_module(package_name)
            self._process_module(module, plugin_dict)
        except Exception as e:
            log.error(f"Failed to load {self.type} package {pkg_path.name}: {e}")

    def _generate_package_name(self, pkg_path: Path) -> str:
        """Dynamically generate package name"""
        base_pkg = self.load_dir.as_posix().replace("/", ".").rstrip(".")
        return f"{base_pkg}.{pkg_path.name}" if base_pkg else pkg_path.name

    def _process_module(self, module: Any, plugin_dict: Dict[str, Type[T]]) -> None:
        """Process a single plugin module"""
        for name in getattr(module, "__all__", []):
            cls = getattr(module, name, None)
            if self._is_valid_class(cls):
                plugin_name = getattr(cls, self.name_attr, None)
                if plugin_name:
                    plugin_dict[plugin_name] = cls
                    log.info(f"Loaded {self.type}: {plugin_name}")


class LazyDictProxy(Generic[T]):
    """
    Lazy loading proxy for dictionary-like objects.

    NOTE: This is NOT thread-safe.
    """

    def __init__(self, loader: Callable[[], Dict[str, T]]):
        self._loader = loader
        self._data: Dict[str, T] | None = None

    def _ensure_loaded(self):
        if self._data is None:
            self._data = self._loader()

    def __getitem__(self, key: str) -> T:
        self._ensure_loaded()
        return self._data[key]  # type: ignore

    def __contains__(self, key: str) -> bool:
        self._ensure_loaded()
        return key in self._data  # type: ignore

    def get(self, key: str, default=None) -> T | None:
        self._ensure_loaded()
        return self._data.get(key, default)  # type: ignore

    def keys(self):
        self._ensure_loaded()
        return self._data.keys()  # type: ignore

    def values(self):
        self._ensure_loaded()
        return self._data.values()  # type: ignore

    def items(self):
        self._ensure_loaded()
        return self._data.items()  # type: ignore

    def __iter__(self):
        self._ensure_loaded()
        return iter(self._data)  # type: ignore

    def __len__(self) -> int:
        self._ensure_loaded()
        return len(self._data)  # type: ignore


def load_drivers() -> dict[str, Type[BaseDriver]]:
    """Load driver plugins"""
    return PluginLoader(
        plugin_dir=g_config.plugin.driver,
        plugin_base_cls=BaseDriver,
        plugin_type="driver",
        plugin_name_attr="driver_name",
    ).load()


def load_webhooks() -> dict[str, Type[BaseWebHookCaller]]:
    """Load webhook plugins"""
    return PluginLoader(
        plugin_dir=g_config.plugin.webhook,
        plugin_base_cls=BaseWebHookCaller,
        plugin_type="webhook",
        plugin_name_attr="webhook_name",
    ).load()


def load_template_renderers() -> dict[str, Type[BaseTemplateRenderer]]:
    """Load template renderer plugins"""
    return PluginLoader(
        plugin_dir=g_config.plugin.template,
        plugin_base_cls=BaseTemplateRenderer,
        plugin_type="template",
        plugin_name_attr="template_name",
    ).load()


def load_template_parsers() -> dict[str, Type[BaseTemplateParser]]:
    """Load template parser plugins"""
    return PluginLoader(
        plugin_dir=g_config.plugin.template,
        plugin_base_cls=BaseTemplateParser,
        plugin_type="template",
        plugin_name_attr="template_name",
    ).load()


def load_scheduler() -> dict[str, Type[BaseScheduler]]:
    """Load scheduler plugins"""
    return PluginLoader(
        plugin_dir=g_config.plugin.scheduler,
        plugin_base_cls=BaseScheduler,
        plugin_type="scheduler",
        plugin_name_attr="scheduler_name",
    ).load()


def load_credential_providers() -> dict[str, Type[BaseCredentialProvider]]:
    """Load credential provider plugins"""
    return PluginLoader(
        plugin_dir=g_config.plugin.credential,
        plugin_base_cls=BaseCredentialProvider,
        plugin_type="credential",
        plugin_name_attr="credential_name",
    ).load()


# NOTE: Type hints added just for Ruff. Pylance could infer the type w/o hints.
drivers: Dict[str, Type[BaseDriver]] = LazyDictProxy(load_drivers)
webhooks: Dict[str, Type[BaseWebHookCaller]] = LazyDictProxy(load_webhooks)
renderers: Dict[str, Type[BaseTemplateRenderer]] = LazyDictProxy(load_template_renderers)
parsers: Dict[str, Type[BaseTemplateParser]] = LazyDictProxy(load_template_parsers)
schedulers: Dict[str, Type[BaseScheduler]] = LazyDictProxy(load_scheduler)
credentials: Dict[str, Type[BaseCredentialProvider]] = LazyDictProxy(load_credential_providers)

__all__ = ["credentials", "drivers", "parsers", "renderers", "schedulers", "webhooks"]
