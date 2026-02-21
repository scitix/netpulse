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
    assert stream_res.telemetry["output_bytes"] == 1024
    assert stream_res.telemetry["next_offset"] == 1024


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


def test_paramiko_pid_reuse_detection():
    """Test that background task check detects PID reuse via comm verification."""
    from netpulse.plugins.drivers.paramiko.model import BackgroundTaskQuery

    mock_session = MagicMock()
    mock_stdout = MagicMock()
    mock_stderr = MagicMock()
    mock_session.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)

    driver = ParamikoDriver(
        args=None,
        conn_args=ParamikoConnectionArgs(host="h", username="u", password="p"),
    )

    # 1. Setup: Case where comm matches (Identity Verified)
    # Commands: ps -p ... and cat ...pid.meta
    task_id = "task123"
    pid = 12345

    def side_effect(cmd, **kwargs):
        ro = MagicMock()
        re = MagicMock()
        if "ps -p" in cmd:
            ro.read.return_value = f"{pid} 00:01 {task_id}".encode()
        elif ".meta" in cmd:
            ro.read.return_value = f"{task_id}\n".encode()
        else:
            ro.read.return_value = b""

        re.read.return_value = b""
        ro.channel.recv_exit_status.return_value = 0
        return MagicMock(), ro, re

    mock_session.exec_command.side_effect = side_effect

    query = BackgroundTaskQuery(pid=pid, output_file="/tmp/test.log")
    result = driver._check_background_task(mock_session, query)["task_query"]

    assert result.telemetry["running"] is True
    assert result.telemetry["identity_verified"] is True

    # 2. Setup: Case where comm mismatch (PID Reuse)
    def side_effect_reuse(cmd, **kwargs):
        ro = MagicMock()
        re = MagicMock()
        if "ps -p" in cmd:
            ro.read.return_value = f"{pid} 10:00:00 nginx".encode() # Reuse by nginx
        elif ".meta" in cmd:
            ro.read.return_value = f"{task_id}\n".encode()
        else:
            ro.read.return_value = b""

        re.read.return_value = b""
        ro.channel.recv_exit_status.return_value = 0
        return MagicMock(), ro, re

    mock_session.exec_command.side_effect = side_effect_reuse
    result_reuse = driver._check_background_task(mock_session, query)["task_query"]

    assert result_reuse.telemetry["running"] is False
    assert result_reuse.telemetry["identity_verified"] is False


def test_paramiko_stream_identity_verification():
    """Test that stream query detects PID reuse and handles results correctly."""
    from netpulse.plugins.drivers.paramiko.model import StreamQuery

    mock_session = MagicMock()
    driver = ParamikoDriver(
        args=None,
        conn_args=ParamikoConnectionArgs(host="h", username="u", password="p"),
    )

    sid = "stream123"
    pid = "5555"

    def side_effect(cmd, **kwargs):
        ro, re = MagicMock(), MagicMock()
        if f"cat /tmp/netpulse_stream_{sid}.pid" in cmd:
            ro.read.return_value = f"{pid}\n".encode()
        elif "ps -p" in cmd:
            # Case 1: Identity match
            ro.read.return_value = f"{pid} 00:05 {sid}".encode()
        elif "stat -c%s" in cmd:
            ro.read.return_value = b"500\n"
        else:
            ro.read.return_value = b"some output"
        ro.channel.recv_exit_status.return_value = 0
        re.read.return_value = b""
        return MagicMock(), ro, re

    mock_session.exec_command.side_effect = side_effect
    query = StreamQuery(session_id=sid, offset=0, lines=10)

    # 1. Test Success Case
    res = driver._query_stream(mock_session, query)["stream_result"]
    assert res.telemetry["identity_verified"] is True
    assert res.telemetry["completed"] is False
    assert res.telemetry["output_bytes"] == 500

    # 2. Test PID Reuse Case
    def side_effect_reuse(cmd, **kwargs):
        ro, re = MagicMock(), MagicMock()
        if f"cat /tmp/netpulse_stream_{sid}.pid" in cmd:
            ro.read.return_value = f"{pid}\n".encode()
        elif "ps -p" in cmd:
            # Identity mismatch (reused by python)
            ro.read.return_value = f"{pid} 01:00 python".encode()
        elif "stat -c%s" in cmd:
            ro.read.return_value = b"500\n"
        else:
            ro.read.return_value = b""
        ro.channel.recv_exit_status.return_value = 0
        re.read.return_value = b""
        return MagicMock(), ro, re

    mock_session.exec_command.side_effect = side_effect_reuse
    res_reuse = driver._query_stream(mock_session, query)["stream_result"]
    assert res_reuse.telemetry["identity_verified"] is False
    assert res_reuse.telemetry["completed"] is True


def test_paramiko_list_active_tasks():
    """Test that active tasks can be discovered on the remote host."""
    from netpulse.plugins.drivers.paramiko.model import ParamikoSendCommandArgs

    mock_session = MagicMock()
    driver = ParamikoDriver(
        args=ParamikoSendCommandArgs(list_active_tasks=True),
        conn_args=ParamikoConnectionArgs(host="h", username="u", password="p"),
    )

    def side_effect(cmd, **kwargs):
        ro, re = MagicMock(), MagicMock()
        if "ls /tmp/netpulse_*.pid.meta" in cmd:
            ro.read.return_value = b"/tmp/netpulse_bg_123.pid.meta\n"
        elif "cat /tmp/netpulse_bg_123.pid.meta" in cmd:
            ro.read.return_value = b"task-xyz\n"
        elif "cat /tmp/netpulse_bg_123.pid" in cmd:
            ro.read.return_value = b"9999\n"
        elif "ps -p 9999" in cmd:
            ro.read.return_value = b"task-xyz\n"

        ro.channel.recv_exit_status.return_value = 0
        re.read.return_value = b""
        return MagicMock(), ro, re

    mock_session.exec_command.side_effect = side_effect

    # Execute via the public send() method
    results = driver.send(mock_session, [])

    assert "task_list" in results
    tasks = results["task_list"].telemetry["active_tasks"]
    assert len(tasks) == 1
    assert tasks[0]["task_id"] == "task-xyz"
    assert tasks[0]["pid"] == 9999
