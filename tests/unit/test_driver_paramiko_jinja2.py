import unittest
from unittest.mock import MagicMock, patch

from netpulse.models.common import DriverName
from netpulse.models.request import ExecutionRequest, TemplateRenderRequest
from netpulse.plugins.drivers.paramiko.model import (
    ParamikoConnectionArgs,
    ParamikoSendCommandArgs,
    ParamikoSendConfigArgs,
)
from netpulse.services import rpc


class TestParamikoJinja2(unittest.TestCase):
    def setUp(self):
        self.conn_args = ParamikoConnectionArgs(
            host="1.1.1.1",
            username="test",
            password="test"
        )

    @patch("netpulse.plugins.drivers.paramiko.ParamikoDriver.connect")
    @patch("netpulse.plugins.drivers.paramiko.ParamikoDriver.disconnect")
    @patch("paramiko.SSHClient")
    def test_rendering_in_send(self, mock_ssh, mock_disconnect, mock_connect):
        # Mock the session
        mock_session = mock_ssh.return_value
        mock_connect.return_value = mock_session

        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"bar\n"
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b""

        mock_session.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)

        req = ExecutionRequest(
            driver=DriverName.PARAMIKO,
            connection_args=self.conn_args,
            command="echo {{ foo }}",
            driver_args=ParamikoSendCommandArgs(),
            rendering=TemplateRenderRequest(
                name="jinja2",
                context={"foo": "bar"}
            )
        )

        # Test rendering through rpc.execute
        result = rpc.execute(req)

        # Verify exec_command was called with rendered string
        mock_session.exec_command.assert_called_with("echo bar", get_pty=False)
        self.assertIn("echo bar", result)
        self.assertEqual(result["echo bar"]["output"], "bar\n")

    @patch("netpulse.plugins.drivers.paramiko.ParamikoDriver.connect")
    @patch("netpulse.plugins.drivers.paramiko.ParamikoDriver.disconnect")
    @patch("paramiko.SSHClient")
    def test_rendering_in_config(self, mock_ssh, mock_disconnect, mock_connect):
        # Mock the session
        mock_session = mock_ssh.return_value
        mock_connect.return_value = mock_session

        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"success\n"
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b""
        mock_session.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)

        req = ExecutionRequest(
            driver=DriverName.PARAMIKO,
            connection_args=self.conn_args,
            config=["vlan {{ vlan_id }}"],
            driver_args=ParamikoSendConfigArgs(),
            rendering=TemplateRenderRequest(
                name="jinja2",
                context={"vlan_id": 100}
            )
        )

        # Test rendering through rpc.execute
        result = rpc.execute(req)

        # Verify rendering
        mock_session.exec_command.assert_called_with("vlan 100", get_pty=False)
        self.assertIn("vlan 100", result)

if __name__ == "__main__":
    unittest.main()
