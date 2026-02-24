from unittest.mock import MagicMock

from netpulse.plugins.drivers.paramiko import ParamikoDriver
from netpulse.plugins.drivers.paramiko.model import ParamikoConnectionArgs


def create_mock_driver():
    return ParamikoDriver(
        args=None,
        conn_args=ParamikoConnectionArgs(host="h", username="u", password="p"),
    )


def test_paramiko_launch_detached():
    """Test launching a command natively in the background."""
    driver = create_mock_driver()
    mock_session = MagicMock()
    detached_dir = "/tmp/np-detached-u"

    # Simulate reading the PID file in _read_remote_file
    def mock_exec_side_effect(cmd, **kwargs):
        ro = MagicMock()
        re = MagicMock()
        if f"cat {detached_dir}/np_test-123.pid" in cmd:
            ro.read.return_value = b"9999\n"
        elif "ps -p 9999 -o args=" in cmd:
            ro.read.return_value = b"np_test-123 bash -c ...\n"
        else:
            ro.read.return_value = b""
        ro.channel.recv_exit_status.return_value = 0
        re.read.return_value = b""
        return MagicMock(), ro, re

    mock_session.exec_command.side_effect = mock_exec_side_effect

    res = driver.launch_detached(mock_session, "sleep 100", "test-123")

    launch_res = next(x for x in res if x.command == "launch")
    assert launch_res.metadata["task_id"] == "test-123"
    assert launch_res.metadata["pid"] == 9999
    assert launch_res.metadata["log_file"] == f"{detached_dir}/np_test-123.log"
    assert "duration_seconds" in launch_res.metadata
    assert "session_reused" in launch_res.metadata
    assert launch_res.metadata["is_running"] is True


def test_paramiko_is_task_running():
    """Test verification of whether a detached task is still running."""
    driver = create_mock_driver()
    mock_session = MagicMock()
    detached_dir = "/tmp/np-detached-u"

    # 1. Test success case (PID match and comm match)
    def side_effect_running(cmd, **kwargs):
        ro = MagicMock()
        re = MagicMock()
        ro.channel.recv_exit_status.return_value = 0
        if f"cat {detached_dir}/np_t1.pid" in cmd:
            ro.read.return_value = b"5555\n"
        elif "ps -p 5555 -o args=" in cmd:
            ro.read.return_value = b"np_t1 bash -c 'sleep 100'\n"
        else:
            ro.read.return_value = b""
        re.read.return_value = b""
        return MagicMock(), ro, re

    mock_session.exec_command.side_effect = side_effect_running
    running, pid = driver._is_task_running(mock_session, "t1")
    assert running is True
    assert pid == 5555

    # 2. Test PID reuse/not running case (PID doesn't match background process)
    def side_effect_reused(cmd, **kwargs):
        ro = MagicMock()
        re = MagicMock()
        ro.channel.recv_exit_status.return_value = 0
        if f"cat {detached_dir}/np_t2.pid" in cmd:
            ro.read.return_value = b"6666\n"
        elif "ps -p 6666 -o args=" in cmd:
            ro.read.return_value = b"python script.py\n"  # no np_t2
        else:
            ro.read.return_value = b""
        re.read.return_value = b""
        return MagicMock(), ro, re

    mock_session.exec_command.side_effect = side_effect_reused
    running, pid = driver._is_task_running(mock_session, "t2")
    assert running is False
    assert pid == 6666


def test_paramiko_read_logs():
    """Test reading the log delta for a task."""
    driver = create_mock_driver()
    mock_session = MagicMock()
    detached_dir = "/tmp/np-detached-u"

    def side_effect_read(cmd, **kwargs):
        ro = MagicMock()
        re = MagicMock()
        ro.channel.recv_exit_status.return_value = 0
        # Mocking _is_task_running steps
        if f"cat {detached_dir}/np_t3.pid" in cmd:
            ro.read.return_value = b"7777\n"
        elif "ps -p 7777 -o args=" in cmd:
            ro.read.return_value = b"np_t3 bash -c ...\n"
        # Mocking tail/cat output
        elif "tail -c" in cmd or f"cat {detached_dir}/np_t3.log" in cmd:
            ro.read.return_value = b"hello\nworld\n"
        # Mocking file size query
        elif "stat -c%s" in cmd:
            ro.read.return_value = b"12\n"
        else:
            ro.read.return_value = b""
        re.read.return_value = b""
        return MagicMock(), ro, re

    mock_session.exec_command.side_effect = side_effect_read

    res = driver._read_logs(mock_session, "t3", offset=0)

    query_res = next(x for x in res if x.command == "query")
    assert query_res.stdout == "hello\nworld\n"
    assert query_res.metadata["next_offset"] == 12
    assert query_res.metadata["is_running"] is True
    assert query_res.metadata["completed"] is False


def test_paramiko_kill_task():
    """Test killing a task via the driver native detach."""
    driver = create_mock_driver()
    mock_session = MagicMock()
    detached_dir = "/tmp/np-detached-u"

    def side_effect_kill(cmd, **kwargs):
        ro = MagicMock()
        re = MagicMock()
        ro.channel.recv_exit_status.return_value = 0
        if f"cat {detached_dir}/np_t4.pid" in cmd:
            ro.read.return_value = b"8888\n"
        elif "ps -p 8888 -o args=" in cmd:
            ro.read.return_value = b"np_t4 bash -c ...\n"
        else:
            ro.read.return_value = b""
        re.read.return_value = b""
        return MagicMock(), ro, re

    mock_session.exec_command.side_effect = side_effect_kill

    # Run the kill
    res = driver.kill_task(mock_session, "t4")

    assert res[0].exit_status == 0
    assert res[0].command == "kill"

    # Assert kill and clean commands were run
    # exec_command is called by _execute_command which is called by
    # kill_task and _is_task_running
    calls = [
        call[1][0] if len(call[1]) > 0 else call[2].get("cmd")
        for call in mock_session.exec_command.mock_calls
    ]
    calls = [c for c in calls if c]

    assert any("kill -15 8888" in cmd and "kill -9 8888" in cmd for cmd in calls)
    assert any(f"rm -f {detached_dir}/np_t4.log" in cmd for cmd in calls)
