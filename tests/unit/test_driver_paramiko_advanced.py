import hashlib
import os
import shutil
import tempfile
from unittest.mock import MagicMock

from netpulse.plugins.drivers.paramiko import ParamikoDriver
from netpulse.plugins.drivers.paramiko.model import (
    ParamikoConnectionArgs,
)


class FakeSFTPFile:
    def __init__(self):
        self.data = b""

    def write(self, chunk):
        self.data += chunk

    def read(self, size=-1):
        return b""

    def seek(self, offset):
        pass

    def close(self):
        pass


class FakeSFTP:
    def __init__(self):
        self.dirs = set()
        self.files = {}

    def mkdir(self, path):
        self.dirs.add(path)

    def stat(self, path):
        if path in self.files:
            return MagicMock(st_size=len(self.files[path]), st_mode=0o644)
        if path in self.dirs:
            return MagicMock(st_size=4096, st_mode=0o40755)
        raise FileNotFoundError()

    def file(self, path, mode="wb"):
        f = FakeSFTPFile()
        self.files[path] = f
        return f

    def close(self):
        pass


def test_paramiko_upload_hash_sync(monkeypatch):
    """Test hash-based sync skips transfer when MD5 matches."""
    local_dir = tempfile.mkdtemp()
    local_file = os.path.join(local_dir, "test.txt")
    content = b"hello world"
    with open(local_file, "wb") as f:
        f.write(content)

    local_hash = hashlib.md5(content).hexdigest()

    class FakeSession:
        def exec_command(self, cmd):
            if "md5sum" in cmd:
                # Mock md5sum output
                stdout = MagicMock()
                stdout.read.return_value = f"{local_hash}  /tmp/test.txt".encode()
                return None, stdout, None
            return None, MagicMock(), None

        def open_sftp(self):
            sftp = MagicMock()
            sftp.stat.return_value = MagicMock(st_size=len(content))
            return sftp

    driver = ParamikoDriver(
        args=None,
        conn_args=ParamikoConnectionArgs(host="h", username="u", password="p"),
    )

    session = FakeSession()

    # Run upload with hash sync
    result = driver._upload_file(
        session, # type: ignore
        local_file,
        "/tmp/test.txt",
        sync_mode="hash"
    )

    assert result["success"] is True
    assert result.get("skipped") is True
    assert result["bytes_transferred"] == 0

    shutil.rmtree(local_dir)


def test_paramiko_upload_recursive(monkeypatch):
    """Test recursive upload creates directories and transfers files."""
    local_dir = tempfile.mkdtemp()
    sub_dir = os.path.join(local_dir, "sub")
    os.makedirs(sub_dir)

    with open(os.path.join(local_dir, "f1.txt"), "w") as f:
        f.write("f1")
    with open(os.path.join(sub_dir, "f2.txt"), "w") as f:
        f.write("f2")

    fake_sftp = FakeSFTP()

    class FakeSession:
        def open_sftp(self):
            return fake_sftp
        def exec_command(self, cmd):
            return None, MagicMock(), None

    driver = ParamikoDriver(
        args=None,
        conn_args=ParamikoConnectionArgs(host="h", username="u", password="p"),
    )

    session = FakeSession()

    result = driver._upload_file(
        session, # type: ignore
        local_dir,
        "/remote/path",
        recursive=True
    )

    assert result["success"] is True
    assert result["recursive"] is True
    assert result["files_transferred"] == 2
    assert "/remote/path/sub" in fake_sftp.dirs

    shutil.rmtree(local_dir)
