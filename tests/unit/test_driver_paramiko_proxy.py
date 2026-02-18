import unittest
from unittest.mock import MagicMock, patch

from netpulse.plugins.drivers.paramiko import ParamikoDriver
from netpulse.plugins.drivers.paramiko.model import (
    ParamikoConnectionArgs,
    ParamikoSendCommandArgs,
)


class TestParamikoProxy(unittest.TestCase):
    def setUp(self):
        self.conn_args = ParamikoConnectionArgs(
            host="target.example.com",
            username="target_user",
            password="target_password",
            proxy_host="jump.example.com",
            proxy_username="jump_user",
            proxy_password="jump_password"
        )

    @patch("paramiko.SSHClient")
    def test_connect_via_proxy(self, mock_ssh_cls):
        # We need two SSHClient instances: one for proxy, one for target
        proxy_client = MagicMock()
        target_client = MagicMock()

        # side_effect to return proxy_client first, then target_client
        mock_ssh_cls.side_effect = [proxy_client, target_client]

        # Mock transport and channel for proxy
        mock_transport = MagicMock()
        proxy_client.get_transport.return_value = mock_transport
        mock_channel = MagicMock()
        mock_transport.open_channel.return_value = mock_channel

        args = ParamikoSendCommandArgs()
        driver = ParamikoDriver(args=args, conn_args=self.conn_args)

        session = driver.connect()

        # Verify proxy connection
        proxy_client.connect.assert_called_with(
            hostname="jump.example.com",
            port=22,
            timeout=30.0,
            password="jump_password",
            username="jump_user"
        )

        # Verify channel opening
        mock_transport.open_channel.assert_called_with(
            "direct-tcpip",
            ("target.example.com", 22),
            ("jump.example.com", 22)
        )

        # Verify target connection via channel
        target_client.connect.assert_called_with(
            hostname="target.example.com",
            port=22,
            username="target_user",
            sock=mock_channel,
            timeout=30.0,
            look_for_keys=True,  # Now correctly respects conn_args
            allow_agent=False,   # Now correctly respects conn_args
            password="target_password"
        )

        self.assertEqual(session, target_client)
        self.assertEqual(target_client._proxy_client, proxy_client)

if __name__ == "__main__":
    unittest.main()
