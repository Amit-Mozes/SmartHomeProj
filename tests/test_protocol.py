import socket
import unittest

from smart_home_project.common.protocol import Protocol, ProtocolError


class ProtocolTests(unittest.TestCase):
    def test_create_msg_prefixes_length(self):
        left, right = socket.socketpair()
        try:
            protocol = Protocol(left)
            self.assertEqual(protocol.create_msg("TURN_ON:LED_1"), b"0000000013TURN_ON:LED_1")
        finally:
            left.close()
            right.close()

    def test_get_msg_handles_partial_recv(self):
        left, right = socket.socketpair()
        try:
            Protocol(right).send_msg("hello")
            self.assertEqual(Protocol(left).get_msg(), b"hello")
        finally:
            left.close()
            right.close()

    def test_invalid_length_field_raises(self):
        left, right = socket.socketpair()
        try:
            right.sendall(b"abc0000000payload")
            with self.assertRaises(ProtocolError):
                Protocol(left).get_msg()
        finally:
            left.close()
            right.close()


if __name__ == "__main__":
    unittest.main()
