import unittest
from unittest.mock import MagicMock, patch

from netpulse.plugins.drivers.paramiko import ParamikoDriver
from netpulse.plugins.drivers.paramiko.model import (
    ParamikoConnectionArgs,
    ParamikoSendCommandArgs,
    ParamikoSendConfigArgs,
)


class TestParamikoJinja2(unittest.TestCase):
    def setUp(self):
        self.conn_args = ParamikoConnectionArgs(
            host="1.1.1.1",
            username="test",
            password="test"
        )

    @patch("paramiko.SSHClient")
    def test_rendering_in_send(self, mock_ssh):
        # Mock the session
        mock_session = mock_ssh.return_value
        # Mock exec_command to return stdout, stderr, stdin
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"bar\n"
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b""
        mock_session.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)

        args = ParamikoSendCommandArgs(
            context={"foo": "bar"}
        )
        driver = ParamikoDriver(args=args, conn_args=self.conn_args)

        # Test rendering of a single command
        result = driver.send(mock_session, ["echo {{ foo }}"])

        # Verify exec_command was called with rendered string
        # Match the exact call: exec_command('echo bar', get_pty=False)
        mock_session.exec_command.assert_called_with("echo bar", get_pty=False)
        self.assertIn("echo bar", result)
        self.assertEqual(result["echo bar"]["output"], "bar\n")

    @patch("paramiko.SSHClient")
    def test_rendering_in_config(self, mock_ssh):
        # Mock the session
        mock_session = mock_ssh.return_value
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"success\n"
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b""
        mock_session.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)

        args = ParamikoSendConfigArgs(
            context={"vlan_id": 100}
        )
        driver = ParamikoDriver(args=args, conn_args=self.conn_args)

        # Test rendering of a config line
        result = driver.config(mock_session, ["vlan {{ vlan_id }}"])

        # Verify rendering. In config(), exec_kwargs includes get_pty
        mock_session.exec_command.assert_called_with("vlan 100", get_pty=False)
        self.assertIn("vlan 100", result)

    @patch("paramiko.SSHClient")
    def test_rendering_in_script_content(self, mock_ssh):
        # Mock the session
        mock_session = mock_ssh.return_value
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"script output\n"
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b""
        mock_session.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        script_tpl = "echo User is {{ user }}"
        args = ParamikoSendCommandArgs(
            script_content=script_tpl,
            context={"user": "admin"}
        )
        driver = ParamikoDriver(args=args, conn_args=self.conn_args)

        # Trigger script execution through send()
        result = driver.send(mock_session, [])

        # Verify rendered content was written to stdin
        mock_stdin.write.assert_called_with("echo User is admin")
        self.assertIn("script_execution_bash", result)

if __name__ == "__main__":
    unittest.main()
