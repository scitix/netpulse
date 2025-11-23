
from netpulse.plugins import PluginLoader
from netpulse.plugins.drivers import BaseDriver


class DummyDriver(BaseDriver):
    driver_name = "dummy"

    @classmethod
    def from_execution_request(cls, req):
        return cls()

    @classmethod
    def validate(cls, req):
        return None

    def __init__(self, **kwargs):
        pass

    def connect(self):
        raise NotImplementedError

    def send(self, session, command: list[str]):
        raise NotImplementedError

    def config(self, session, config: list[str]):
        raise NotImplementedError

    def disconnect(self, session):
        raise NotImplementedError

    @classmethod
    def test(cls, connection_args):
        raise NotImplementedError


def test_plugin_loader_loads_valid_package(tmp_path, monkeypatch):
    base_pkg = tmp_path / "tmp_plugins"
    base_pkg.mkdir()
    (base_pkg / "__init__.py").write_text("")

    pkg_dir = base_pkg / "dummy_pkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text(
        "from netpulse.plugins.drivers import BaseDriver\n"
        "__all__ = ['DummyDriver']\n"
        "class DummyDriver(BaseDriver):\n"
        "    driver_name='dummy'\n"
        "    @classmethod\n"
        "    def from_execution_request(cls, req):\n"
        "        return cls()\n"
        "    @classmethod\n"
        "    def validate(cls, req):\n"
        "        return None\n"
        "    def __init__(self, **kwargs):\n"
        "        pass\n"
        "    def connect(self):\n"
        "        pass\n"
        "    def send(self, session, command: list[str]):\n"
        "        pass\n"
        "    def config(self, session, config: list[str]):\n"
        "        pass\n"
        "    def disconnect(self, session):\n"
        "        pass\n"
        "    @classmethod\n"
        "    def test(cls, connection_args):\n"
        "        pass\n"
    )

    monkeypatch.syspath_prepend(str(tmp_path))
    loader = PluginLoader(
        load_dir=base_pkg, base_cls=BaseDriver, ptype="driver", name_attr="driver_name"
    )

    # Force predictable package name regardless of absolute path
    monkeypatch.setattr(
        loader, "_generate_package_name", lambda pkg_path: f"tmp_plugins.{pkg_path.name}"
    )

    loaded = loader.load()
    assert "dummy" in loaded
    assert issubclass(loaded["dummy"], BaseDriver)


def test_plugin_loader_ignores_invalid_package(tmp_path, monkeypatch):
    plugin_root = tmp_path / "invalid_plugins"
    bad_pkg = plugin_root / "bad"
    bad_pkg.mkdir(parents=True)
    (bad_pkg / "__init__.py").write_text("raise RuntimeError('boom')")

    monkeypatch.syspath_prepend(str(tmp_path))
    loader = PluginLoader(
        load_dir=plugin_root, base_cls=BaseDriver, ptype="driver", name_attr="driver_name"
    )

    loaded = loader.load()
    assert loaded == {}
