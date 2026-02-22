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
        session,  # type: ignore
        local_file,
        "/tmp/test.txt",
        sync_mode="hash",
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
        session,  # type: ignore
        local_dir,
        "/remote/path",
        recursive=True,
    )

    assert result["success"] is True
    assert result["recursive"] is True
    assert result["files_transferred"] == 2
    assert "/remote/path/sub" in fake_sftp.dirs

    shutil.rmtree(local_dir)


def test_paramiko_metadata():
    """Test that command execution returns metadata data."""
    from netpulse.plugins.drivers.paramiko.model import ParamikoSendCommandArgs

    class FakeSession:
        def exec_command(self, cmd, **kwargs):
            stdout = MagicMock()
            stdout.read.return_value = b"some output"
            stdout.channel.recv_exit_status.return_value = 0
            stderr = MagicMock()
            stderr.read.return_value = b""
            return MagicMock(), stdout, stderr

    driver = ParamikoDriver(
        args=None,
        conn_args=ParamikoConnectionArgs(host="h", username="u", password="p"),
    )

    result = driver._execute_command(FakeSession(), "echo test", ParamikoSendCommandArgs())
    metadata = result["echo test"].metadata
    assert metadata is not None
    assert "duration_seconds" in metadata
    assert isinstance(metadata["duration_seconds"], float)


def test_paramiko_interactive_expect():
    """Test that expect_map correctly handles automated responses."""

    mock_channel = MagicMock()
    # Mock behavior: return prompt on first call, then signal exit
    mock_channel.recv_ready.side_effect = [True, False, False]
    mock_channel.recv.return_value = b"Are you sure? [Y/n]: "
    mock_channel.exit_status_ready.side_effect = [False, True, True, True]
    mock_channel.recv_exit_status.return_value = 0
    mock_channel.recv_stderr_ready.return_value = False

    mock_stdout = MagicMock()
    mock_stdout.channel = mock_channel
    mock_stderr = MagicMock()
    mock_stderr.channel = mock_channel

    # Track what's written to stdin
    mock_stdin = MagicMock()

    mock_session = MagicMock()
    mock_session.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

    driver = ParamikoDriver(
        args=None,
        conn_args=ParamikoConnectionArgs(host="h", username="u", password="p"),
    )

    expect_map = {"[Y/n]": "y"}
    output, error, status = driver._execute_interactive(
        mock_session, "confirm_cmd", expect_map, timeout=1.0
    )

    assert "[Y/n]" in output
    # Verify that 'y\n' was written to stdin
    mock_stdin.write.assert_called_with("y\n")
    assert status == 0


def test_paramiko_list_active_detached_tasks():
    """Test that active detached tasks can be discovered on the remote host."""
    from netpulse.plugins.drivers.paramiko.model import ParamikoSendCommandArgs

    mock_session = MagicMock()
    # The expected directory for user 'u'
    detached_dir = "/tmp/np-detached-u"
    driver = ParamikoDriver(
        args=ParamikoSendCommandArgs(list_active_detached_tasks=True),
        conn_args=ParamikoConnectionArgs(host="h", username="u", password="p"),
    )

    def side_effect(cmd, **kwargs):
        ro, re = MagicMock(), MagicMock()
        if f"ls {detached_dir}/np_*.pid.meta" in cmd:
            ro.read.return_value = f"{detached_dir}/np_123.pid.meta\n".encode()
        elif f"cat {detached_dir}/np_123.pid.meta" in cmd:
            ro.read.return_value = b"task-xyz\n"
        elif f"cat {detached_dir}/np_123.pid" in cmd:
            ro.read.return_value = b"9999\n"
        elif "ps -p 9999" in cmd:
            ro.read.return_value = b"np_task-xyz\n"

        ro.channel.recv_exit_status.return_value = 0
        re.read.return_value = b""
        return MagicMock(), ro, re

    mock_session.exec_command.side_effect = side_effect

    # Execute via the public send() method
    results = driver.send(mock_session, [])

    assert "list_active_detached_tasks" in results
    tasks = results["list_active_detached_tasks"].metadata["active_tasks"]
    assert len(tasks) == 1
    assert tasks[0]["task_id"] == "task-xyz"
    assert tasks[0]["pid"] == 9999
