import sys
sys.path.append( '../../backend/')

from client import *
from torrent import *

file_name = '../test.mp4'
test_torrent_file = file_name+'.torrent'
test_config_file = './seed_config.json'
# client1_ip = '10.0.0.2'
client1_ip = '10.180.57.167'
client = Client(test_torrent_file,test_config_file, client_ip = client1_ip)
client.start()
