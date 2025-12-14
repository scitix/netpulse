import importlib
from types import SimpleNamespace

import pytest

from netpulse.models.common import CredentialRef, DriverConnectionArgs, DriverName
from netpulse.models.request import ExecutionRequest


def _load_device_module():
    return importlib.import_module("netpulse.routes.device")


def test_credential_disabled_rejects_request(runtime_loader):
    runtime_loader({"NETPULSE_CREDENTIAL__ENABLED": "false"})
    device_module = _load_device_module()

    req = ExecutionRequest(
        driver=DriverName.NETMIKO,
        connection_args=DriverConnectionArgs(),
        credential=CredentialRef(name="vault_kv", ref="netpulse/device-a", mount="kv"),
        command="show version",
    )

    with pytest.raises(ValueError, match="Credential support is disabled"):
        device_module._resolve_request_credentials(req)


def test_vault_path_not_allowed(runtime_loader, monkeypatch):
    runtime_loader(
        {
            "NETPULSE_CREDENTIAL__ENABLED": "true",
            "NETPULSE_CREDENTIAL__NAME": "vault_kv",
            "NETPULSE_CREDENTIAL__ADDR": "http://vault:8200",
            "NETPULSE_CREDENTIAL__TOKEN": "dev-root-token",
            "NETPULSE_CREDENTIAL__ALLOWED_PATHS": "kv/allowed",
            "NETPULSE_CREDENTIAL__CACHE_TTL": "0",
        }
    )

    device_module = _load_device_module()
    from netpulse.plugins.credentials import vault_kv

    # Ensure provider does not try to use a real hvac client
    monkeypatch.setattr(vault_kv, "hvac", SimpleNamespace(Client=lambda *_, **__: None))

    req = ExecutionRequest(
        driver=DriverName.NETMIKO,
        connection_args=DriverConnectionArgs(),
        credential=CredentialRef(name="vault_kv", ref="netpulse/device-a", mount="kv"),
        command="show version",
    )

    with pytest.raises(ValueError, match="not allowed by policy"):
        device_module._resolve_request_credentials(req)


def test_vault_provider_resolves_and_populates(runtime_loader, monkeypatch):
    runtime_loader(
        {
            "NETPULSE_CREDENTIAL__ENABLED": "true",
            "NETPULSE_CREDENTIAL__NAME": "vault_kv",
            "NETPULSE_CREDENTIAL__ADDR": "http://vault:8200",
            "NETPULSE_CREDENTIAL__TOKEN": "dev-root-token",
            "NETPULSE_CREDENTIAL__ALLOWED_PATHS": "kv/netpulse",
            "NETPULSE_CREDENTIAL__CACHE_TTL": "0",
        }
    )

    device_module = _load_device_module()
    from netpulse.plugins.credentials import vault_kv

    secret_store = {"kv/netpulse/device-a": {"username": "admin", "password": "s3cr3t"}}
    read_calls: list[tuple[str, str, int | None]] = []

    class FakeKVv2:
        def __init__(self, store):
            self._store = store

        def read_secret_version(self, mount_point, path, version=None):
            read_calls.append((mount_point, path, version))
            key = f"{mount_point}/{path}"
            if key not in self._store:
                raise ValueError("secret not found")
            return {"data": {"data": self._store[key]}}

    class FakeClient:
        def __init__(self, *, url, token, namespace=None, verify=True):
            self.url = url
            self.token = token
            self.namespace = namespace
            self.verify = verify
            self._store = secret_store
            self._authenticated = bool(token)
            self.auth = SimpleNamespace(approle=SimpleNamespace(login=self._login))
            self.secrets = SimpleNamespace(kv=SimpleNamespace(v2=FakeKVv2(self._store)))

        def _login(self, role_id, secret_id):
            self._authenticated = True

        def is_authenticated(self):
            return self._authenticated

    hvac_mock = SimpleNamespace(Client=FakeClient)
    monkeypatch.setattr(vault_kv, "hvac", hvac_mock)
    vault_kv.VaultKvCredentialProvider._cache = {}

    req = ExecutionRequest(
        driver=DriverName.NETMIKO,
        connection_args=DriverConnectionArgs(host="1.1.1.1"),
        credential=CredentialRef(name="vault_kv", ref="netpulse/device-a", mount="kv"),
        command="show version",
    )

    device_module._resolve_request_credentials(req)

    assert req.credential is None
    assert req.connection_args.username == "admin"
    assert req.connection_args.password == "s3cr3t"
    assert read_calls == [("kv", "netpulse/device-a", None)]


def test_vault_provider_respects_cache(runtime_loader, monkeypatch):
    runtime_loader(
        {
            "NETPULSE_CREDENTIAL__ENABLED": "true",
            "NETPULSE_CREDENTIAL__NAME": "vault_kv",
            "NETPULSE_CREDENTIAL__ADDR": "http://vault:8200",
            "NETPULSE_CREDENTIAL__TOKEN": "dev-root-token",
            "NETPULSE_CREDENTIAL__ALLOWED_PATHS": "kv/netpulse",
            "NETPULSE_CREDENTIAL__CACHE_TTL": "60",
        }
    )

    device_module = _load_device_module()
    from netpulse.plugins.credentials import vault_kv

    secret_store = {"kv/netpulse/device-a": {"username": "cached", "password": "once"}}
    read_calls: list[tuple[str, str, int | None]] = []

    class FakeKVv2:
        def __init__(self, store):
            self._store = store

        def read_secret_version(self, mount_point, path, version=None):
            read_calls.append((mount_point, path, version))
            key = f"{mount_point}/{path}"
            return {"data": {"data": self._store[key]}}

    class FakeClient:
        def __init__(self, *, url, token, namespace=None, verify=True):
            self._store = secret_store
            self._authenticated = True
            self.auth = SimpleNamespace(approle=SimpleNamespace(login=lambda *_: None))
            self.secrets = SimpleNamespace(kv=SimpleNamespace(v2=FakeKVv2(self._store)))

        def is_authenticated(self):
            return self._authenticated

    vault_kv.VaultKvCredentialProvider._cache = {}
    monkeypatch.setattr(vault_kv, "hvac", SimpleNamespace(Client=FakeClient))

    for _ in range(2):
        req = ExecutionRequest(
            driver=DriverName.NETMIKO,
            connection_args=DriverConnectionArgs(host="1.1.1.1"),
            credential=CredentialRef(name="vault_kv", ref="netpulse/device-a", mount="kv"),
            command="show version",
        )
        device_module._resolve_request_credentials(req)
        assert req.connection_args.username == "cached"
        assert req.connection_args.password == "once"

    # Second call should hit cache (only one backend read)
    assert read_calls == [("kv", "netpulse/device-a", None)]


def test_vault_provider_reads_version_and_mapping(runtime_loader, monkeypatch):
    runtime_loader(
        {
            "NETPULSE_CREDENTIAL__ENABLED": "true",
            "NETPULSE_CREDENTIAL__NAME": "vault_kv",
            "NETPULSE_CREDENTIAL__ADDR": "http://vault:8200",
            "NETPULSE_CREDENTIAL__TOKEN": "dev-root-token",
            "NETPULSE_CREDENTIAL__ALLOWED_PATHS": "kv/netpulse",
        }
    )

    device_module = _load_device_module()
    from netpulse.plugins.credentials import vault_kv

    secret_store = {"kv/netpulse/device-a": {"user_field": "u1", "pwd_field": "p1"}}
    read_calls: list[tuple[str, str, int | None]] = []

    class FakeKVv2:
        def __init__(self, store):
            self._store = store

        def read_secret_version(self, mount_point, path, version=None):
            read_calls.append((mount_point, path, version))
            key = f"{mount_point}/{path}"
            return {"data": {"data": self._store[key]}}

    class FakeClient:
        def __init__(self, *, url, token, namespace=None, verify=True):
            self._store = secret_store
            self._authenticated = True
            self.auth = SimpleNamespace(approle=SimpleNamespace(login=lambda *_: None))
            self.secrets = SimpleNamespace(kv=SimpleNamespace(v2=FakeKVv2(self._store)))

        def is_authenticated(self):
            return self._authenticated

    vault_kv.VaultKvCredentialProvider._cache = {}
    monkeypatch.setattr(vault_kv, "hvac", SimpleNamespace(Client=FakeClient))

    req = ExecutionRequest(
        driver=DriverName.NETMIKO,
        connection_args=DriverConnectionArgs(host="1.1.1.1"),
        credential=CredentialRef(
            name="vault_kv",
            ref="netpulse/device-a",
            mount="kv",
            version=2,
            field_mapping={"username": "user_field", "password": "pwd_field"},
        ),
        command="show version",
    )

    device_module._resolve_request_credentials(req)

    assert req.connection_args.username == "u1"
    assert req.connection_args.password == "p1"
    assert read_calls == [("kv", "netpulse/device-a", 2)]


def test_vault_provider_missing_required_field(runtime_loader, monkeypatch):
    runtime_loader(
        {
            "NETPULSE_CREDENTIAL__ENABLED": "true",
            "NETPULSE_CREDENTIAL__NAME": "vault_kv",
            "NETPULSE_CREDENTIAL__ADDR": "http://vault:8200",
            "NETPULSE_CREDENTIAL__TOKEN": "dev-root-token",
            "NETPULSE_CREDENTIAL__ALLOWED_PATHS": "kv/netpulse",
        }
    )

    device_module = _load_device_module()
    from netpulse.plugins.credentials import vault_kv

    secret_store = {"kv/netpulse/device-a": {"user_field": "u1"}}

    class FakeClient:
        def __init__(self, *, url, token, namespace=None, verify=True):
            self._authenticated = True
            self.auth = SimpleNamespace(approle=SimpleNamespace(login=lambda *_: None))
            kvv2 = SimpleNamespace(
                read_secret_version=lambda **kwargs: {
                    "data": {"data": secret_store[f"{kwargs['mount_point']}/{kwargs['path']}"]}
                }
            )
            self.secrets = SimpleNamespace(kv=SimpleNamespace(v2=kvv2))

        def is_authenticated(self):
            return self._authenticated

    vault_kv.VaultKvCredentialProvider._cache = {}
    monkeypatch.setattr(vault_kv, "hvac", SimpleNamespace(Client=FakeClient))

    req = ExecutionRequest(
        driver=DriverName.NETMIKO,
        connection_args=DriverConnectionArgs(host="1.1.1.1"),
        credential=CredentialRef(
            name="vault_kv",
            ref="netpulse/device-a",
            mount="kv",
            field_mapping={"username": "user_field", "password": "missing_pwd"},
        ),
        command="show version",
    )

    with pytest.raises(ValueError, match="Missing required secret fields: missing_pwd"):
        device_module._resolve_request_credentials(req)


def test_vault_provider_rejects_invalid_field_mapping(runtime_loader, monkeypatch):
    runtime_loader(
        {
            "NETPULSE_CREDENTIAL__ENABLED": "true",
            "NETPULSE_CREDENTIAL__NAME": "vault_kv",
            "NETPULSE_CREDENTIAL__ADDR": "http://vault:8200",
            "NETPULSE_CREDENTIAL__TOKEN": "dev-root-token",
            "NETPULSE_CREDENTIAL__ALLOWED_PATHS": "kv/netpulse",
        }
    )

    device_module = _load_device_module()
    from netpulse.plugins.credentials import vault_kv

    # Ensure provider does not try to use a real hvac client
    monkeypatch.setattr(vault_kv, "hvac", SimpleNamespace(Client=lambda *_, **__: None))

    req = ExecutionRequest(
        driver=DriverName.NETMIKO,
        connection_args=DriverConnectionArgs(host="1.1.1.1"),
        credential=CredentialRef(
            name="vault_kv",
            ref="netpulse/device-a",
            mount="kv",
            field_mapping={"": "user_field"},
        ),
        command="show version",
    )

    with pytest.raises(ValueError, match="field_mapping keys must be non-empty strings"):
        device_module._resolve_request_credentials(req)
