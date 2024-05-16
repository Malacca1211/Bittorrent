import unittest
import bencodepy
import os
from create_torrent import create_torrent_file, get_file_info

class TestCreateTorrent(unittest.TestCase):
    def setUp(self):
        # 创建测试文件 test_file.txt，大小为 1024 字节
        self.filename = 'test_file.txt'
        self.torrent_filename = 'test.torrent'
        with open(self.filename, 'wb') as f:
            f.write(os.urandom(1024))  # 使用随机数据填充文件

    def test_file_info(self):
        # 测试文件信息获取是否正确
        self.filename = 'test_file.txt'
        info = get_file_info(self.filename, piece_length=524288)
        self.assertIsNotNone(info[b'pieces'])
        self.assertEqual(info[b'length'], 1024)  # 验证文件大小为 1024 字节

    def test_torrent_file_creation(self):
        # 测试.torrent文件的创建
        create_torrent_file(self.filename, 'http://127.0.0.1:6881/announce', self.torrent_filename)
        with open(self.torrent_filename, 'rb') as f:
            data = bencodepy.decode(f.read())
            self.assertEqual(data[b'announce'], b'http://127.0.0.1:6881/announce')
            self.assertTrue(b'info' in data)

    def tearDown(self):
        # 测试完成后删除创建的文件
        os.remove(self.filename)
        if(os.path.exists(self.torrent_filename)):
            os.remove(self.torrent_filename)

if __name__ == '__main__':
    unittest.main()
