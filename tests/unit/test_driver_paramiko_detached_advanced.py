from unittest.mock import MagicMock, patch

import pytest

from netpulse.models.common import FileTransferModel
from netpulse.models.driver import DriverExecutionResult
from netpulse.plugins.drivers.paramiko import ParamikoDriver
from netpulse.plugins.drivers.paramiko.model import (
    ParamikoConnectionArgs,
    ParamikoSendCommandArgs,
)


@pytest.fixture
def mock_session():
    session = MagicMock()

    # Mock default behavior for exec_command
    def default_exec(cmd, **kwargs):
        stdout = MagicMock()
        stdout.channel.recv_exit_status.return_value = 0
        stdout.read.return_value = b""
        if ".pid" in cmd and "cat" in cmd:
            stdout.read.return_value = b"1234\n"
        elif "ps -p" in cmd:
            # Match proc name
            stdout.read.return_value = b"np_test-task\n"

        stderr = MagicMock()
        stderr.read.return_value = b""
        return MagicMock(), stdout, stderr

    session.exec_command.side_effect = default_exec
    return session


def test_detached_launch_full_suite(mock_session):
    """
    Comprehensive test for detached launch covering:
    - User-isolated directory
    - Sudo wrapping
    - Environment variables
    - Working directory
    - Process name injection
    """
    args = ParamikoSendCommandArgs(
        sudo=True,
        sudo_password="secret_pass",
        environment={"APP_ENV": "prod"},
        working_directory="/opt/app",
    )
    driver = ParamikoDriver(
        args=args, conn_args=ParamikoConnectionArgs(host="h", username="admin", password="p")
    )

    # Act
    task_id = "test-task"
    driver.launch_detached(mock_session, "python worker.py", task_id)

    # Assert
    calls = [call[0][0] for call in mock_session.exec_command.call_args_list]

    # 1. Directory creation
    assert any("mkdir -p /tmp/np-detached-admin" in c for c in calls)

    # 2. Command wrapping check
    launch_call = next(c for c in calls if "nohup" in c)

    # Verify sudo
    assert launch_call.startswith("sudo -S bash -c")

    # Since quoting is deeply nested, we check for core components presence
    # (they will be escaped but visible)
    assert "APP_ENV" in launch_call
    assert "prod" in launch_call
    assert "cd /opt/app" in launch_call
    assert "python worker.py" in launch_call
    assert "setsid" in launch_call
    assert "np_test-task" in launch_call


@patch("netpulse.plugins.drivers.paramiko.ParamikoDriver._handle_file_transfer")
def test_detached_launch_with_binary_upload(mock_transfer, mock_session):
    """
    Test that binary upload correctly transitions to detached execution.
    """
    file_op = FileTransferModel(
        operation="upload",
        local_path="bin/tools",
        remote_path="/tmp/tools",
        execute_after_upload=True,
        execute_command="/tmp/tools --daemon",
    )
    driver = ParamikoDriver(
        args=ParamikoSendCommandArgs(),
        conn_args=ParamikoConnectionArgs(host="h", username="u", password="p"),
        file_transfer=file_op,
    )

    # Mock successful upload
    mock_transfer.return_value = {
        "file_transfer_upload": DriverExecutionResult(stdout="uploaded", exit_status=0)
    }

    # Act
    driver.launch_detached(mock_session, "", "task-binary")

    # Assert
    mock_transfer.assert_called_once()
    assert mock_transfer.call_args[1]["skip_exec"] is True

    launch_call = next(
        c[0][0] for c in mock_session.exec_command.call_args_list if "nohup" in c[0][0]
    )
    assert "/tmp/tools --daemon" in launch_call


def test_detached_script_execution_and_cleanup(mock_session):
    """
    Test that script_content is written, executed, and then cleaned up.
    """
    args = ParamikoSendCommandArgs(script_content="print('hello')", script_interpreter="python3")
    driver = ParamikoDriver(
        args=args, conn_args=ParamikoConnectionArgs(host="h", username="dev", password="p")
    )

    # 1. Launch
    driver.launch_detached(mock_session, "", "t-123")

    calls = [c[0][0] for c in mock_session.exec_command.call_args_list]
    assert any("printf %s" in c and "t-123.sh" in c for c in calls)

    launch_call = next(c for c in calls if "nohup" in c)
    assert "python3 /tmp/np-detached-dev/np_t-123.sh" in launch_call

    # 2. Kill / Cleanup
    mock_session.exec_command.reset_mock()
    driver.kill_task(mock_session, "t-123")

    cleanup_calls = [c[0][0] for c in mock_session.exec_command.call_args_list]
    assert any("rm -f" in c and "/tmp/np-detached-dev/np_t-123.sh" in c for c in cleanup_calls)
