import socket
import threading
import sys
import os
import bencodepy
import tools
import argparse
import socket

def main():
    parser = argparse.ArgumentParser(description='BitTorrent Client')
    parser.add_argument('torrent_file', help='The path to the torrent file')
    parser.add_argument('--port', type=int, default=6881, help='Port to use for incoming connections')
    args = parser.parse_args()

    # 使用 args.port 和 args.torrent_file 来启动客户端
    print(f"Running on port {args.port} with torrent file {args.torrent_file}")

def load_torrent_file(torrent_path):
    """从.torrent文件加载元数据"""
    with open(torrent_path, 'rb') as f:
        torrent_contents = f.read()
    torrent_data = bencodepy.decode(torrent_contents)
    announce_url = torrent_data[b'announce'].decode('utf-8')
    peer_list = tools.get_peers_from_tracker(torrent_data)
    # peer_list = [('127.0.0.1', 6881)]  # 这里应该是动态解析的，目前用静态数据代替
    return {'announce': announce_url, 'peers': peer_list}

def start_server(announce_url):
    """启动一个服务器来监听其他节点的连接请求"""
    server_port = tools.get_port_from_url(announce_url)  # 从announce URL获取端口
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind(('0.0.0.0', server_port))
        server.listen()
        print(f"Listening for connections on {announce_url}")
        while True:
            client_socket, addr = server.accept()
            print(f"Connected by {addr}")
            threading.Thread(target=handle_client, args=(client_socket,)).start()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def connect_to_peer(peer):
    """连接到一个指定的对等节点"""
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(peer)
        print(f"Connected to peer {peer}")
        # 发送一个简单的消息
        client.sendall("Hello, peer!".encode('utf-8'))
        response = client.recv(1024)
        print(f"Received: {response.decode('utf-8')}")
    except Exception as e:
        print(f"Failed to connect to peer {peer}: {e}")

def handle_client(client_socket):
    """处理从其他节点接收到的连接"""
    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            print(f"Received: {data.decode('utf-8')}")
            client_socket.sendall("Hi, thanks for the message!".encode('utf-8'))
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()

# 上面的功能测试完毕 下面是传输文件实现（集成后需要修改）

def create_file_chunks(file_path, chunk_size=1024*256):  # 默认块大小为256KB
    """将文件分块并返回块的列表"""
    chunks = []
    with open(file_path, 'rb') as file:
        chunk = file.read(chunk_size)
        while chunk:
            chunks.append(chunk)
            chunk = file.read(chunk_size)
    return chunks

def save_chunks_to_file(chunks, output_path):
    """将分块数据写回到文件中"""
    with open(output_path, 'wb') as output_file:
        for chunk in chunks:
            output_file.write(chunk)


if __name__ == '__main__':
    main()
    
