import socket
import time
import unittest

from smart_home_project.common.server_discovery import (
    create_discovery_request,
    create_discovery_response,
    discover_servers,
    parse_discovery_request,
    parse_discovery_response,
)
from smart_home_project.server.server_discovery import ServerDiscoveryService


class TestServerDiscovery(unittest.TestCase):
    def test_discovery_packet_helpers(self):
        self.assertTrue(parse_discovery_request(create_discovery_request()))
        server = parse_discovery_response(create_discovery_response(8820, "Test Pi"), "192.168.1.50")
        self.assertIsNotNone(server)
        self.assertEqual(server.host, "192.168.1.50")
        self.assertEqual(server.port, 8820)
        self.assertEqual(server.name, "Test Pi")

    def test_client_can_find_discovery_service(self):
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.bind(("127.0.0.1", 0))
        discovery_port = probe.getsockname()[1]
        probe.close()

        service = ServerDiscoveryService(tcp_port=8820, discovery_port=discovery_port, name="Unit Test Server")
        service.start()
        time.sleep(0.1)
        try:
            servers = discover_servers(discovery_port, timeout=1.0, broadcast_hosts=("127.0.0.1",))
        finally:
            service.stop()

        self.assertEqual(len(servers), 1)
        self.assertEqual(servers[0].host, "127.0.0.1")
        self.assertEqual(servers[0].port, 8820)
        self.assertEqual(servers[0].name, "Unit Test Server")


if __name__ == "__main__":
    unittest.main()
