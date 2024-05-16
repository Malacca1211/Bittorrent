import hashlib
import bencodepy
import argparse
from os import path

def get_file_info(filename, piece_length=524288):
    file_size = path.getsize(filename)
    pieces = []
    with open(filename, 'rb') as file:
        piece = file.read(piece_length)
        while piece:
            pieces.append(hashlib.sha1(piece).digest())
            piece = file.read(piece_length)
    return {
        b'name': filename.encode(),
        b'length': file_size,
        b'piece length': piece_length,
        b'pieces': b''.join(pieces)
    }

def create_torrent_file(filename, tracker_url, torrent_filename):
    torrent_info = {
        b'announce': tracker_url.encode(),
        b'info': get_file_info(filename)
    }
    with open(torrent_filename, 'wb') as torrent_file:
        torrent_file.write(bencodepy.encode(torrent_info))
    print(f"Torrent file '{torrent_filename}' created successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a .torrent file.")
    parser.add_argument('filename', help="The filename of the file to be shared.")
    parser.add_argument('tracker_url', help="The announce URL of the tracker.")
    parser.add_argument('torrent_filename', help="The name of the output .torrent file.")
    args = parser.parse_args()

    create_torrent_file(args.filename, args.tracker_url, args.torrent_filename)
