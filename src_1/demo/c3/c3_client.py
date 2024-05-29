import sys
sys.path.insert(0, '../../backend/')

from client import *
from torrent import *

# make_torrent_file('vid.mp4')
file_name = 'test.mp4'
test_torrent_file = '../{}.torrent'.format(file_name)
test_config_file = './c3_config.json'
c3_ip = '10.0.0.4'
# c3_ip = '127.0.0.1'
client = Client(test_torrent_file, test_config_file, client_ip = c3_ip)
client.start()
