import unittest
from unittest.mock import MagicMock
from tracker import Tracker
import socket
import threading
import unittest
import bencodepy
from tracker import Tracker
import time

class TestTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = Tracker()

    def test_update_peers(self):
        # 测试更新对等节点信息
        self.tracker.update_peers('torrent1', 'peer1:6881')
        self.assertIn('peer1:6881', self.tracker.peers['torrent1'])

    def test_get_peers(self):
        # 测试获取对等节点列表
        self.tracker.update_peers('torrent1', 'peer1:6881')
        peers = self.tracker.get_peers('torrent1')
        self.assertEqual(peers, ['peer1:6881'])

def start_tracker():
    # 在另一个线程中运行跟踪器
    tracker = Tracker(host='127.0.0.1', port=6882)
    threading.Thread(target=tracker.start, daemon=True).start()

class TestTrackerIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 启动跟踪器
        start_tracker()

    def test_tracker_communication(self):
        # 测试跟踪器网络通信
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('127.0.0.1', 6882))
                request_update = bencodepy.encode({
                    b'action': b'update',
                    b'torrent_id': b'torrent1',
                    b'peer_info': b'peer1:6881'
                })
                s.sendall(request_update)
                # 等待服务器响应
                # time.sleep(1)
                request_get_peers = bencodepy.encode({
                    b'action': b'get_peers',
                    b'torrent_id': b'torrent1'
                })
                s.sendall(request_get_peers)
                data = s.recv(1024)
                if data:
                    peers = bencodepy.decode(data)
                    self.assertIn(b'peer1:6881', peers)
        except ConnectionAbortedError as e:
            self.fail(f"Connection was aborted unexpectedly: {e}")

if __name__ == '__main__':
    unittest.main()
