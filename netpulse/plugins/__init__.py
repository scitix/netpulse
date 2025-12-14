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
        load_dir: Path,
        base_cls: Type[T],
        ptype: str = "plugin",
        name_attr: str = "plugin_name",
    ):
        """
        Args:
            load_dir: plugin directory
            base_cls: base class for plugins
            ptype: type of plugin
            name_attr: name attribute for plugin
        """
        self.base_class = base_cls
        self.type = ptype
        self.name_attr = name_attr
        self.load_dir = load_dir

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
            cls: Type[T] | None = getattr(module, name, None)
            if self._is_valid_class(cls):
                plugin_name: str | None = getattr(cls, self.name_attr, None)
                if plugin_name:
                    plugin_dict[plugin_name] = cls  # type: ignore
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
        load_dir=g_config.plugin.driver,
        base_cls=BaseDriver,
        ptype="driver",
        name_attr="driver_name",
    ).load()


def load_webhooks() -> dict[str, Type[BaseWebHookCaller]]:
    """Load webhook plugins"""
    return PluginLoader(
        load_dir=g_config.plugin.webhook,
        base_cls=BaseWebHookCaller,
        ptype="webhook",
        name_attr="webhook_name",
    ).load()


def load_template_renderers() -> dict[str, Type[BaseTemplateRenderer]]:
    """Load template renderer plugins"""
    return PluginLoader(
        load_dir=g_config.plugin.template,
        base_cls=BaseTemplateRenderer,
        ptype="template",
        name_attr="template_name",
    ).load()


def load_template_parsers() -> dict[str, Type[BaseTemplateParser]]:
    """Load template parser plugins"""
    return PluginLoader(
        load_dir=g_config.plugin.template,
        base_cls=BaseTemplateParser,
        ptype="template",
        name_attr="template_name",
    ).load()


def load_scheduler() -> dict[str, Type[BaseScheduler]]:
    """Load scheduler plugins"""
    return PluginLoader(
        load_dir=g_config.plugin.scheduler,
        base_cls=BaseScheduler,
        ptype="scheduler",
        name_attr="scheduler_name",
    ).load()


def load_credentials() -> dict[str, Type[BaseCredentialProvider]]:
    """Load credential plugins"""
    return PluginLoader(
        load_dir=g_config.plugin.credential,
        base_cls=BaseCredentialProvider,
        ptype="credential",
        name_attr="credential_name",
    ).load()


drivers: Dict[str, Type[BaseDriver]] = LazyDictProxy(load_drivers)  # type: ignore
webhooks: Dict[str, Type[BaseWebHookCaller]] = LazyDictProxy(load_webhooks)  # type: ignore
renderers: Dict[str, Type[BaseTemplateRenderer]] = LazyDictProxy(load_template_renderers)  # type: ignore
parsers: Dict[str, Type[BaseTemplateParser]] = LazyDictProxy(load_template_parsers)  # type: ignore
schedulers: Dict[str, Type[BaseScheduler]] = LazyDictProxy(load_scheduler)  # type: ignore
credentials: Dict[str, Type[BaseCredentialProvider]] = LazyDictProxy(load_credentials)  # type: ignore

__all__ = ["credentials", "drivers", "parsers", "renderers", "schedulers", "webhooks"]
