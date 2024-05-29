import sys
sys.path.append( '../../backend/')

from client import *
from torrent import *

file_name = '../test.mp4'
test_torrent_file = file_name+'.torrent'
test_config_file = './seed_config.json'
# seed_ip = '10.0.02'
seed_ip = '127.0.0.1'
client = Client(test_torrent_file,test_config_file, seed_ip)
client.start()
