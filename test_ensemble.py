import subprocess
import os
import unittest
import hashlib
import time
import bittorrent

class TestBitTorrentSystem(unittest.TestCase):
    def setUp(self):
        self.test_file = 'test_data.txt'
        self.torrent_file = 'test_data.torrent'
        self.test_file_size = 1024 * 1024  # 1 MB
        with open(self.test_file, 'wb') as f:
            f.write(os.urandom(self.test_file_size))
        
        # 启动跟踪器
        self.tracker_process = subprocess.Popen(['python', 'tracker.py'])
        time.sleep(1)

        # 创建.torrent文件
        subprocess.run(['python', 'create_torrent.py', self.test_file, 'http://127.0.0.1:6881/announce', self.torrent_file])
        time.sleep(1)

        # 启动种子客户端在端口 6881
        self.seeder_process = subprocess.Popen(['python', 'bittorrent.py', self.torrent_file, '--port', '6881'])

        # 留时间给种子上传文件
        time.sleep(2)

    def test_file_download(self):
        # 启动下载客户端在端口 6882
        downloader_process = subprocess.Popen(['python', 'bittorrent.py', self.torrent_file, '--port', '6882'])
        
        self.output_path = 'downloaded_' + self.test_file #设置一下输出文件

        chunks = bittorrent.create_file_chunks(self.test_file, chunk_size=1024*256) # 默认块大小为256KB
        bittorrent.save_chunks_to_file(chunks, self.output_path)

        downloader_process.wait(timeout=60)

        # 校验文件是否正确下载
        self.assertTrue(os.path.exists('downloaded_' + self.test_file))
        self.assertEqual(self.hash_file('downloaded_' + self.test_file), self.hash_file(self.test_file))


    def hash_file(self, filename):
        hasher = hashlib.sha1()
        with open(filename, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def tearDown(self):
        for process in [self.tracker_process, self.seeder_process]:
            process.terminate()
            stdout, stderr = process.communicate()
            if stderr:
                print(f"Error from {process.args}: {stderr.decode()}")
        for file in [self.test_file, self.torrent_file, 'downloaded_' + self.test_file]:
            try:
                os.remove(file)
            except OSError as e:
                print(f"Failed to remove {file}: {e}")

if __name__ == '__main__':
    unittest.main()
