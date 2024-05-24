from torrent import *

torrent = read_torrent_file('../demo/test.mp4.torrent')

print(type(torrent['info']['piece_hash']))