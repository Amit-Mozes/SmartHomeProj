import socket
import threading
import time
import unittest

from smart_home_project.client.smart_home_client import SmartHomeClient
from smart_home_project.server.smart_home_server import SmartHomeServer


class ClientUpdateTests(unittest.TestCase):
    def test_abort_unblocks_pending_update_request(self):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()

        server = SmartHomeServer("127.0.0.1", port)
        threading.Thread(target=server.start, daemon=True).start()
        time.sleep(0.2)

        client = SmartHomeClient("127.0.0.1", port)
        client.connect()
        self.assertEqual(client.login("admin", "admin123")["status"], "ok")
        revision = client.get_updates(0, timeout=1)["data"]["revision"]

        result = {}

        def wait_for_update():
            try:
                client.get_updates(revision, timeout=10)
            except Exception as exc:
                result["error"] = exc

        worker = threading.Thread(target=wait_for_update, daemon=True)
        worker.start()
        time.sleep(0.2)
        client.abort()
        worker.join(2)
        server.stop()

        self.assertFalse(worker.is_alive())
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
