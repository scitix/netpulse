import pytest

from netpulse.models import DriverName
from netpulse.plugins.drivers.paramiko.model import (
    ParamikoConnectionArgs,
    ParamikoExecutionRequest,
    ParamikoFileTransferOperation,
    ParamikoSendCommandArgs,
)
from netpulse.services import rpc
from tests.e2e.settings import get_linux_ssh_target, is_reachable

pytestmark = pytest.mark.e2e


def test_paramiko_exec_on_linux_ssh():
    """Execute a command on the Linux SSH host via Paramiko."""
    target = get_linux_ssh_target()

    if not is_reachable(target.host, target.port):
        msg = f"Linux device at {target.host}:{target.port} unreachable; ensure ContainerLab is up"
        pytest.skip(msg)

    req = ParamikoExecutionRequest(
        driver=DriverName.PARAMIKO,
        connection_args=ParamikoConnectionArgs(
            host=target.host,
            username=target.username,
            password=target.password,
            port=target.port,
            host_key_policy="auto_add",
            look_for_keys=False,
            allow_agent=False,
        ),  # type: ignore
        command=target.command,
    )

    result = rpc.execute(req)

    assert target.command in result
    payload = result[target.command]
    assert isinstance(payload, dict)
    assert payload["exit_status"] == 0
    assert "netpulse-e2e" in payload["output"]


def test_paramiko_config_on_linux_ssh(tmp_path):
    """Push a config command via Paramiko and verify it persisted on the host."""
    target = get_linux_ssh_target()

    if not is_reachable(target.host, target.port):
        pytest.skip(
            f"Linux device at {target.host}:{target.port} unreachable; ensure ContainerLab is up"
        )

    conn_args = ParamikoConnectionArgs(
        host=target.host,
        username=target.username,
        password=target.password,
        port=target.port,
        host_key_policy="auto_add",
        look_for_keys=False,
        allow_agent=False,
    )
    marker = "paramiko-config-e2e"
    cfg_cmd = f'sh -c "echo {marker} > /tmp/paramiko-config-e2e.txt"'

    cfg_req = ParamikoExecutionRequest(
        driver=DriverName.PARAMIKO,
        connection_args=conn_args,
        config=cfg_cmd,
    )
    cfg_result = rpc.execute(cfg_req)
    assert cfg_cmd in cfg_result
    assert cfg_result[cfg_cmd]["exit_status"] == 0

    verify_req = ParamikoExecutionRequest(
        driver=DriverName.PARAMIKO,
        connection_args=conn_args,
        command="cat /tmp/paramiko-config-e2e.txt",
    )
    verify_result = rpc.execute(verify_req)
    payload = verify_result["cat /tmp/paramiko-config-e2e.txt"]
    assert marker in payload["output"]


def test_paramiko_file_transfer_upload_and_download(tmp_path):
    """Exercise Paramiko file upload then download to confirm SFTP works."""
    target = get_linux_ssh_target()

    if not is_reachable(target.host, target.port):
        pytest.skip(
            f"Linux device at {target.host}:{target.port} unreachable; ensure ContainerLab is up"
        )

    conn_args = ParamikoConnectionArgs(
        host=target.host,
        username=target.username,
        password=target.password,
        port=target.port,
        host_key_policy="auto_add",
        look_for_keys=False,
        allow_agent=False,
    )

    upload_path = tmp_path / "paramiko-upload.txt"
    upload_payload = "paramiko-upload-e2e"
    upload_path.write_text(upload_payload)
    remote_path = "/tmp/paramiko-upload-e2e.txt"

    upload_req = ParamikoExecutionRequest(
        driver=DriverName.PARAMIKO,
        connection_args=conn_args,
        command="noop",
        driver_args=ParamikoSendCommandArgs(
            file_transfer=ParamikoFileTransferOperation(
                operation="upload",
                local_path=str(upload_path),
                remote_path=remote_path,
            )
        ),
    )
    upload_result = rpc.execute(upload_req)
    transfer_key = next(iter(upload_result.keys()))
    assert "file_transfer_upload" in transfer_key
    assert upload_result[transfer_key]["exit_status"] == 0

    download_path = tmp_path / "paramiko-download.txt"
    download_req = ParamikoExecutionRequest(
        driver=DriverName.PARAMIKO,
        connection_args=conn_args,
        command="noop",
        driver_args=ParamikoSendCommandArgs(
            file_transfer=ParamikoFileTransferOperation(
                operation="download",
                local_path=str(download_path),
                remote_path=remote_path,
            )
        ),
    )
    download_result = rpc.execute(download_req)
    transfer_key = next(iter(download_result.keys()))
    assert "file_transfer_download" in transfer_key
    assert download_result[transfer_key]["exit_status"] == 0
    assert download_path.read_text() == upload_payload
