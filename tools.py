import re
import requests
import bencodepy
import hashlib
import random

def get_port_from_url(url):
    match = re.search(r':(\d+)/', url)  # 查找冒号后面跟着数字，后面紧接着斜杠的模式
    if match:
        return int(match.group(1))  # 转换找到的数字为整数
    else:
        raise ValueError("Invalid URL, port not found.")


'''
# 示例用法
announce_url = 'http://127.0.0.1:6881/announce'
server_port = get_port_from_url(announce_url)
print(server_port)  # 应该输出 6881
'''

def generate_peer_id():
    """生成一个随机的 peer ID"""
    return '-PY0001-' + ''.join([str(random.randint(0, 9)) for _ in range(12)])

def get_peers_from_tracker(torrent_data):
    # with open(torrent_path, 'rb') as file:
    #     torrent_data = bencodepy.decode(file.read())
    announce_url = torrent_data[b'announce'].decode('utf-8')
    info_hash = hashlib.sha1(bencodepy.encode(torrent_data[b'info'])).digest()

    peer_id = generate_peer_id()
    params = {
        'info_hash': info_hash,
        'peer_id': peer_id,
        'port': 6881,
        'uploaded': 0,
        'downloaded': 0,
        'left': 1,
        'compact': 1,
        'event': 'started'
    }

    response = requests.get(announce_url, params=params)
    data = bencodepy.decode(response.content)
    peers = parse_peers(data[b'peers'])
    return peers

def parse_peers(peers_binary):
    peers = []
    for i in range(0, len(peers_binary), 6):
        ip = '.'.join(str(x) for x in peers_binary[i:i+4])
        port = int.from_bytes(peers_binary[i+4:i+6], 'big')
        peers.append((ip, port))
    return peers

'''# 使用示例
torrent_file = 'path_to_your_torrent_file.torrent'
peers = get_peers_from_tracker(torrent_file)
print(peers)
'''