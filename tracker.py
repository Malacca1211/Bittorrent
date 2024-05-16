import socket
import threading
import bencodepy
import logging

class Tracker:
    def __init__(self, host='0.0.0.0', port=6881):
        self.host = host
        self.port = port
        self.peers = {}
        logging.basicConfig(level=logging.INFO)

    def start(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.server.listen(5)
        logging.info(f"Tracker running on {self.host}:{self.port}")
        while True:
            conn, addr = self.server.accept()
            threading.Thread(target=self.handle_client, args=(conn,)).start()

    def handle_client(self, conn):
        try:
            data = conn.recv(1024)
            if data:
                try:
                    message = bencodepy.decode(data)
                    action = message.get(b'action', b'').decode('utf-8')
                    torrent_id = message.get(b'torrent_id', b'').decode('utf-8')
                    peer_info = message.get(b'peer_info', b'').decode('utf-8')

                    if not all([action, torrent_id, peer_info]):
                        raise ValueError("Missing required fields")

                    if action == 'update':
                        self.update_peers(torrent_id, peer_info)
                        logging.info(f"Updated peers: {self.peers}")
                    elif action == 'get_peers':
                        peers = self.get_peers(torrent_id)
                        conn.sendall(bencodepy.encode(peers))
                        logging.info(f"Sending peers: {peers}")

                except Exception as e:
                    logging.error(f"Error processing data: {e}")
                    conn.sendall(bencodepy.encode({"error": str(e)}))

        finally:
            conn.close()

    def update_peers(self, torrent_id, peer_info):
        self.peers.setdefault(torrent_id, []).append(peer_info)

    def get_peers(self, torrent_id):
        return self.peers.get(torrent_id, [])

if __name__ == '__main__':
    tracker = Tracker()
    tracker.start()
