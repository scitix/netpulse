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


def test_paramiko_telemetry():
    """Test that command execution returns telemetry data."""
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
    telemetry = result["echo test"].telemetry
    assert telemetry is not None
    assert "duration_seconds" in telemetry
    assert isinstance(telemetry["duration_seconds"], float)


def test_paramiko_stream_cursor():
    """Test that stream query returns next_offset."""
    from netpulse.plugins.drivers.paramiko.model import StreamQuery

    class FakeSession:
        def exec_command(self, cmd, **kwargs):
            stdout = MagicMock()
            # If it's a 'stat -c%s' command, return a mock file size
            if "stat -c%s" in cmd:
                stdout.read.return_value = b"1024\n"
            else:
                stdout.read.return_value = b"log content"
            stdout.channel.recv_exit_status.return_value = 0
            stderr = MagicMock()
            stderr.read.return_value = b""
            return MagicMock(), stdout, stderr

    driver = ParamikoDriver(
        args=None,
        conn_args=ParamikoConnectionArgs(host="h", username="u", password="p"),
    )

    query = StreamQuery(session_id="test-session", offset=0, lines=10)
    result = driver._query_stream(FakeSession(), query)

    stream_res = result["stream_result"]
    assert stream_res.telemetry["stream_result"]["output_bytes"] == 1024
    assert stream_res.telemetry["stream_result"]["next_offset"] == 1024


def test_paramiko_interactive_expect():
    """Test that expect_map correctly handles automated responses."""

    mock_channel = MagicMock()
    # Mock behavior: return prompt on first call, then signal exit
    mock_channel.recv_ready.side_effect = [True, False, False]
    mock_channel.recv.return_value = b"Are you sure? [Y/n]: "
    mock_channel.exit_status_ready.side_effect = [False, True]
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


def test_paramiko_ttl_metadata():
    """Test that background tasks include TTL metadata in commands."""
    from netpulse.plugins.drivers.paramiko.model import ParamikoSendCommandArgs

    mock_session = MagicMock()
    # Mock successful execution
    mock_stdout = MagicMock()
    mock_stdout.read.return_value = b"1234\n"  # PID
    mock_stdout.channel.recv_exit_status.return_value = 0
    mock_stderr = MagicMock()
    mock_stderr.read.return_value = b""
    mock_session.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)

    driver = ParamikoDriver(
        args=None,
        conn_args=ParamikoConnectionArgs(host="h", username="u", password="p"),
    )

    args = ParamikoSendCommandArgs(run_in_background=True, ttl_seconds=1800)

    # We need to mock _cleanup_expired_tasks to avoid side effects during test
    driver._cleanup_expired_tasks = MagicMock()

    driver._execute_background_command(mock_session, "sleep 100", args)

    # Check the actual bg_cmd sent
    # It should look for something containing '.ttl' and the creation timestamp
    calls = mock_session.exec_command.mock_calls
    found_ttl_logic = False
    for call in calls:
        cmd_sent = call[1][0]
        if ".ttl" in cmd_sent and "echo" in cmd_sent:
            found_ttl_logic = True
            break

    assert found_ttl_logic is True
    # Verify cleanup was called
    driver._cleanup_expired_tasks.assert_called_with(mock_session, 1800)
