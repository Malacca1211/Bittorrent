import unittest
from unittest.mock import patch, MagicMock
import bittorrent
import os


class TestBitTorrentClient(unittest.TestCase):
    @patch('socket.socket')
    def test_connect_to_peer(self, mock_socket):
        """测试连接到对等节点功能"""
        # 设置 mock socket 实例
        mock_socket_instance = mock_socket.return_value
        mock_socket_instance.recv.return_value = b"Received: Hello, peer!"

        # 测试连接到一个对等节点
        bittorrent.connect_to_peer(('127.0.0.1', 6881))

        # 确保 socket.connect 被调用
        mock_socket_instance.connect.assert_called_with(('127.0.0.1', 6881))
        # 确保消息被正确发送
        mock_socket_instance.sendall.assert_called_with(b"Hello, peer!")
        # 检查是否接收到响应
        mock_socket_instance.recv.assert_called_once()

    @patch('socket.socket')
    def test_handle_client(self, mock_socket):
        """测试处理客户端连接和数据接收"""
        # 设置 mock socket 实例
        client_socket = mock_socket.return_value
        client_socket.recv.side_effect = [b"Hello from peer!", b'']

        # 使用 MagicMock 模拟客户端 socket
        client = MagicMock()
        bittorrent.handle_client(client_socket)

        # 检查接收数据和发送响应
        self.assertEqual(client_socket.sendall.call_count, 1)
        client_socket.sendall.assert_called_with(b"Hi, thanks for the message!")
        self.assertEqual(client_socket.recv.call_count, 2)

    @patch('bittorrent.start_server')
    @patch('bittorrent.connect_to_peer')
    def test_main(self, mock_connect_to_peer, mock_start_server):
        """测试 main 函数"""
        bittorrent.peers = [('127.0.0.1', 6881)]
        bittorrent.main()

        # 检查是否启动了服务器
        mock_start_server.assert_called_once()
        # 检查是否尝试连接到对等节点
        mock_connect_to_peer.assert_called_with(('127.0.0.1', 6881))




class TestFileChunking(unittest.TestCase):
    def setUp(self):
        """在每个测试前运行，准备测试文件"""
        self.file_path = 'test_file.txt'
        self.output_path = 'test_output_file.txt'
        self.chunk_size = 1024 * 256  # 256KB
        # 创建测试文件
        with open(self.file_path, 'wb') as f:
            f.write(os.urandom(1024 * 1024))  # 写入1MB随机数据

    def test_file_chunking_and_assembly(self):
        """测试文件是否可以被正确分块并重组"""
        chunks = bittorrent.create_file_chunks(self.file_path, self.chunk_size)
        bittorrent.save_chunks_to_file(chunks, self.output_path)

        # 确保重组后的文件与原文件相同
        with open(self.file_path, 'rb') as original, open(self.output_path, 'rb') as output:
            self.assertEqual(original.read(), output.read(), "The reassembled file does not match the original")

    def tearDown(self):
        """清理测试产生的文件"""
        os.remove(self.file_path)
        os.remove(self.output_path)

if __name__ == '__main__':
    unittest.main()
