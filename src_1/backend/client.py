'''
client side
'''
import os
import threading
import socket
import bitarray
import hashlib
import utilities
import time
import queue
import rdt_socket
import torrent
from piecemanager import pieceManager
from message import *
from state import *
import logging
import random


logging.basicConfig(
    # filename='../../log/client.{}.log'.format(__name__),
    format='[%(asctime)s - %(name)s - %(levelname)s] : \n%(message)s\n',
    # datefmt='%M:%S',
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.disabled = True

CLIENT_PORT = 5555
CLIENT_LISTEN_MAX = 8
FILE_HEADER_SIZE = 8

# 以下是优化策略相关的常数
UNCHOKE_NUM = 4
UNCHOKE_TIME = 30 #seconds
    #将UNCHOKE_TIME设置为0可以禁用UNCHOKING
RAREST_FIRST = True
    #启用RAREST_FIRST
OPTIMISTIC_UNCHOKING=True
    #启用乐观解除阻塞，需要先启用RAREST_FIRST

# 这些是常量，不会变动，不需要放到配置文件中
INIT_AM_INTERESTED = False
INIT_AM_CHOCKED = False
INIT_PEER_INTERESTED = False
INIT_PEER_CHOCKED = False
START_EVENT = 'started'
COMPLETED_EVENT = 'completed'

# 全局变量
left_pieces = queue.Queue(0)
queue_lock = threading.Lock()
queue_seted = threading.Event()

class PeerConnection(threading.Thread):
    '''
    not finished
    client
    '''
    # TODO: pieces_num 似乎没有用到？因为pieces_manager这个全局变量已经有了
    def __init__(self, sock, lock):
        threading.Thread.__init__(self)
        self.socket = rdt_socket.rdt_socket(sock)
        self.queue_lock = lock
        self.peer_bitfield = 0
        self.update_event = threading.Event()
        self.request_piece_index = 0
        self.request_piece_hash = 0

        self.data_sent = 0
        self.start_time = time.time()
        self.peer_choked = True
        self.is_interested = False
        logger.info('peer init connection %s', self.socket.s.getsockname())

    def run(self):
        """ 连接 线程主函数 """
        # TODO:这里是需要读全局的bitfield的，发送一个全局的bitfield(一方拥有的文件区块信息)
        # print(f"The bitfield: {pieces_manager.get_bitfield().tolist()}")
        self.send_message(Bitfield(pieces_manager.get_bitfield().tolist()))
        self.initial_flag = 1
        self.send_file_state = sendFileState('10')
        self.recv_file_state = recvFileState('10')

        logger.info('peer connection %s begin to listen', self.socket.s.getsockname())


        
        while True:
            recv_msg = self.recv_message()
            if type(recv_msg) == ServerClose:
                logger.warning(' ============== server close.============== ')
                return
            # 由于这个是阻塞接受消息，不需要读取不到就循环
            
            # 第一次连接必须交换bitfield
            if self.initial_flag == 1:
                if type(recv_msg) == Bitfield:
                    self.peer_bitfield = bitarray.bitarray(recv_msg.bitfield)
                    self.update_event.set()
                    if (self.get_available_piece_request()):
                        # 我已经从队列里取出了我需要并且对面有的块
                        # 对面还是choke，我变成了interested
                        self.send_message(Interested())
                        self.recv_file_state.to_11()
                    else :
                        # 对面已经没有我需要的块了（包含了队列为空的情况）
                        # 我收不了文件，对面choke，我not interested
                        self.send_message(UnInterested())
                        self.recv_file_state.to_10()
                    self.initial_flag = 0
                    continue
            
            # 不是第一次连接，开始检查发送文件部分的状态
            if self.send_file_state.is_10() and type(recv_msg) == Interested:
                # TODO:这里可以决定我到底是choking 还是 no_choke
                # 这里是直接设置我不choke，对方interested
                send_available = 1
                
                logger.debug('============== I know you are interested with me.==============  ')
                if send_available == 1:
                    self.send_file_state.to_01()
                    self.send_message(UnChoke())    
                # else : #  吸血鬼的话是需要 发Choke的，不过这里不考虑
                #     self.send_file_state.to_11()
                #     self.send_message(Choke())
            elif self.send_file_state.is_01() and type(recv_msg) == Request:
                # 当我Un choke并且对方 interested，能够响应Resquest，发送数据包
                cur_piece_index = recv_msg.piece_index
                cur_piece_binary_data = pieces_manager.get_piece(cur_piece_index)
                self.send_message(Piece(cur_piece_index, cur_piece_binary_data))
                self.data_sent += len(cur_piece_binary_data)
                self.peer_choked = False
            elif self.send_file_state.is_01() and type(recv_msg) == UnInterested:
                # 当我处于可以发送文件的状态，但是peer收完了，不感兴趣
                self.send_file_state.to_10()
            

            # 开始检查接受文件部分的状态
            if self.recv_file_state.is_11() and type(recv_msg) == UnChoke:
                # 如果对面choke，我interested（一般是交换bitfield之后的第一个状态）
                # 收到unchoke触发行为
                self.recv_file_state.to_01()
                # 已经是interested状态了，说明之前交换bitfield的时候已经拿到了可以请求的数据块索引
                # 所以可以直接发request请求
                self.send_message(Request(self.request_piece_index))
            elif self.recv_file_state.is_01() and type(recv_msg) == Piece:
                # 在peer没有choke我并且我interested对方的时候，响应对方的piece
                # 检查哈希并视情况更新piece_manager
                if (check_piece_hash_and_update(recv_msg.piece_index, recv_msg.raw_data)):
                    # TODO:可选最小输出
                    # print('receive piece : ',str(recv_msg.piece_index))
                    # 成功接收一个块并更新
                    if self.get_available_piece_request():
                        # 成功在队列中拿到一个可下载数据块，就发请求
                        self.send_message(Request(self.request_piece_index))
                    else:
                        # 如果拿不到呢，就修改状态
                        # 当做对方choke我，我也not interested对方
                        self.send_message(UnInterested())
                        self.recv_file_state.to_10()
                else :
                    # 说明刚刚那一块传输出现了差错，重发原来的请求
                    self.send_message(Request(self.request_piece_index))

            if type(recv_msg) == KeepAlive:
                pass

            logger.debug('(my choke, peer interested):{},(peer choke, my interested):{}'.format(self.send_file_state, self.recv_file_state))
            if self.recv_file_state.is_10() and self.send_file_state.is_10():
                # 检查连接是否应该断开
                logger.info('This connection is disconnected!')
                return
            # TODO:随机延时
            # time.sleep(random.random())
            # logger.info('stop 0.5 second')

    def send_message(self, msg):
        """ 传入message对象，并转成二进制发送 """
        self.socket.sendBytes(msg.to_bytes())
        logger.info('--------------------------------------------------')
        logger.info('[ send from {} to {}] : '.format(self.socket.s.getsockname(), self.socket.s.getpeername())+ msg.to_json_string())
        logger.info('--------------------------------------------------')

    def recv_message(self):
        """ 接受消息，并转成对应消息的对象 """
        logger.debug('begin recvive message')
        msg = bytes_to_message(self.socket.recvBytes())
        logger.debug('end receive message')
        logger.info('--------------------------------------------------')
        logger.info('[ recv ] from {} to {} : '.format(self.socket.s.getpeername(), self.socket.s.getsockname()) +  msg.to_json_string())
        logger.info('--------------------------------------------------')
        return msg
    
    def get_available_piece_request(self):
        """
        如果队列已空，返回0
        死循环：
            如果对面不再有我需要的块，返回0
            取出一个块
                对面的bitfield有，就修改成员变量（当前请求块）,并返回1
                否则就放回队列中，停5秒再拿
        """
        #等待需求队列初始化
        queue_seted.wait()
        if left_pieces.empty():
            logger.debug('The queue is empty.')
            return 0  
        # 如果队列不空，则在队列中取一个元素
        # TODO:拿出来与放回去之间应该要加锁，因为会出现这样的情况
        # 拿出来后，别的连接因为队列空了就断开连接，但实际上我取到的这个快只有那一个断开的连接对应的peer才能够下载到。
        while True:
            if pieces_manager.bitfield == self.peer_bitfield | pieces_manager.bitfield:
                # 过了5s后，我可能从其他客户端下载到了新块，对面可能不再有我需要的块，因此需要一直检查
                logger.debug("I don't need this peer:{}".format(self.socket.s.getpeername()))
                # 如果对面没有我需要的块，直接返回0

                return 0
            # self.queue_lock.acquire()
            piece_index, piece_hash = left_pieces.get()
            if self.peer_bitfield[piece_index] == 1:
                # 如果对面有这个数据块，就interest，否则就放回队列中
                self.request_piece_index, self.request_piece_hash = piece_index, piece_hash
                logger.debug("{}: this piece exists in peer:{}".format(piece_index,self.socket.s.getpeername()))
                # self.queue_lock.release()
                # print(list(left_pieces.queue))
                return 1
            else:
                # 对面没有这个块，将这个块放回到队列中
                left_pieces.put((piece_index, piece_hash))
                # self.queue_lock.release()
                logger.debug("{}: this piece doesn't exist in peer:{}".format(piece_index,self.socket.s.getpeername()))
                time.sleep(random.random())
                # print(list(left_pieces.queue))
                continue
    def get_upload_speed(self):
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 0:
            upload_speed = self.data_sent / elapsed_time
        else:
            upload_speed = 0
        return upload_speed
    
    def reset_upload_speed(self):
        self.data_sent = 0
        self.start_time = time.time()
    
    def wait_for_bitfield_update(self):
        self.update_event.wait()  # 等待 bitfield 更新
        


class Client(threading.Thread):
    '''
    client side
    '''
    def __init__(self, torrent_file_name, config_file_name, client_ip):
        """ 对客户端对象，初始化客户端ip，端口，并读取种子文件，将种子元数据存到客户端中 """
        threading.Thread.__init__(self)
        # 初始化种子文件元数据
        self.begin = time.time()
        self.metadata = torrent.read_torrent_file(torrent_file_name)
        logger.info(f"Tracker IP: {self.metadata['announce']}; port: {self.metadata['port']}")
        self.pieces_num = len(self.metadata['info']['piece_hash'])
        self.task_queue = queue.Queue()
        self.piece_rarity = {}
        self.rarest_pieces = {}
        self.peer_connections = []
        # TODO:bitfield需要思考如何处理，这个应该能够被各个连接访问
        self.bitfield = bitarray.bitarray([0 for _ in range(1, self.pieces_num+1)])
        # 得到本机ip并且作为客户端的成员变量存进来
        self.client_ip = client_ip
        self.client_port = 0
        # 从配置文件中读取数据,同时更新client_port
        self.load_config_file(config_file_name)
        # 初始化可用peer列表
        self.peers_list_response = []
        # 初始化监听线程
        self.client_monitor = ClientMonitor(self.client_ip, self.client_port)
        # TODO:没有什么特别好的解决方法
        global pieces_manager
        pieces_manager = pieceManager(torrent_file_name)
        


    def load_config_file(self, config_file_name):
        """ 从json配置文件中加载进来 """
        with open(config_file_name, 'r') as f:
            config = json.load(f)
        # 初始化几个全局常量TODO:讲道理全局常量不应该变，这么写好像不太好
        global CLIENT_LISTEN_MAX
        global FILE_HEADER_SIZE
        CLIENT_LISTEN_MAX = config['client_listen_max']
        FILE_HEADER_SIZE =  config['file_header_size']
        self.client_port = config['client_port']

    def run(self):
        logger.info('client side run...')
        logger.info('initing the queue ..... finished!')
        # 得到所有的peer列表。存在self.peerListResponse里。
        self.get_peers_list()
        logger.info('ok get list')
        # 向N个peer主动发起链接
        self.establish_link()
        #初始化piece稀有度
        self.init_piece_rarity()
        # 从bitfield中初始化队列，将任务放到队列中等待连接去执行
        self.from_bitfield_setup_queue()
        queue_seted.set()
        # 启动监听线程
        self.client_monitor.start()
        # 开始调度线程

        self.unchoke_manager = UnchokeManager(self)
        self.unchoke_manager.start()


        
        
        while True:
            """
            调度线程有两件事需要做：
            1. 【TODO:暂时不实现，为了先测试】 建立连接，如果连接数少于MAX，就尝试获取更多的可用peer，从中找到自己没有连的peer，然后连接他 
            2. 当文件传输完成，比对哈希值，并存好文件，输出相应信息，等待用户主动结束
            """
            # print(pieces_manager.is_completed())
            if pieces_manager.is_completed():
                if pieces_manager.file_exist:
                    pieces_manager.save_current_all_pieces()
                    break
                elif pieces_manager.merge_full_data_to_file():
                    self.end = time.time()
                    print(f"======= Download time is : {self.end - self.begin}s =======")
                    pieces_manager.save_current_all_pieces()
                    print('======= This file has been downloaded fully and correctly! ========')
                    break
                else:
                    print('======== This download file is damaged! =======')
                    break
            
        # TODO:不会停止线程
        while True:
            a = input('enter q to exit!\n')
            if a == 'q':
                print(f'The all threads: {threading.enumerate()}')
                print("Quit the client sueecssfully!")

                self.disconnect_to_server()
                ## use to exit the whole process
                ## all other threads are killed 
                os._exit(0)
                return
            elif a == 'l':
                print(left_pieces)

    def disconnect_to_server(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        logger.debug('=======DIS-connect to tracker : {}:{} ======='.format(self.metadata['announce'],str(self.metadata['port'])))
        sock.connect((self.metadata['announce'], self.metadata['port']))
        rdt_s = rdt_socket.rdt_socket(sock)
        rdt_s.sendBytes(utilities.objEncode(self.make_resquest(COMPLETED_EVENT)))
        data = rdt_s.recvBytes()
        logger.debug(utilities.binary_to_beautiful_json(data))
        sock.close()
        logger.debug('wave hand finished. program return.')

    def get_peers_list(self):
        """ 向tracker发起链接，请求peer list """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        logger.debug('connect to tracker : {}:{} '.format(self.metadata['announce'],str(self.metadata['port'])))
        sock.connect((self.metadata['announce'], self.metadata['port'])) #TODO
        rdt_s = rdt_socket.rdt_socket(sock)
        rdt_s.sendBytes(utilities.objEncode(self.make_resquest(START_EVENT)))
        data = rdt_s.recvBytes()
        logger.debug(utilities.binary_to_beautiful_json(data))
        sock.close()
        self.peers_list_response = utilities.objDecode(data)
        logger.debug('finish get peer list')

    def establish_link(self):
        """ 主动向peer建立链接 """
        for idx, peer_info in enumerate(self.peers_list_response['peers']):
            #if idx >= 4: return # TODO: add constant here
            peer_ip = peer_info['peer-ip']
            peer_port = peer_info['peer-port']
            print('======= trying to connect to peer {}:{} ======='.format(peer_ip, peer_port))
            logger.debug('========= trying to connect to peer {}:{} ======='.format(peer_ip, peer_port))
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((peer_ip, peer_port))
            # 拉起新的线程管理该tcp
            peer_connection = PeerConnection(sock,queue_lock)
            logger.info('connect to {}:{} finish. tcp start'.format(peer_ip, peer_port))
            print('======= connect to {}:{} finish. tcp start ======='.format(peer_ip, peer_port))
            self.peer_connections.append(peer_connection)
            logger.debug('connect to {}:{} finish. tcp start'.format(peer_ip, peer_port))
            peer_connection.start()
    
    def from_bitfield_setup_queue(self):
        """ 根据现有的bitfield，将没有的块的（索引，哈希值）二元组push进全局队列中 """
        if RAREST_FIRST == True:
            for piece in self.rarest_pieces:
                i=piece[0]
                if pieces_manager.bitfield[i] == 0:
                    logger.info('put the {}:{} into queue !'.format(i,self.metadata['info']['piece_hash'][i]))
                    left_pieces.put((i,self.metadata['info']['piece_hash'][i]))
        else:
            for i in range(0,self.pieces_num):
                if pieces_manager.bitfield[i] == 0:
                    logger.info('put the {}:{} into queue !'.format(i,self.metadata['info']['piece_hash'][i]))
                    left_pieces.put((i,self.metadata['info']['piece_hash'][i]))
    
    def get_id(self):
        """ 使用客户端自己的信息生成自己的id """
        return self.client_ip + ':' + str(self.client_port)

    def make_resquest(self, event):
        """ 制作特定事件的请求，返回对应请求的对象 """
        peer_list_request_obj = {
            'ip': self.client_ip,
            'port': self.client_port,
            'peer_id': self.get_id(),
            'event': event
        }
        return peer_list_request_obj
    
    def manage_unchoking(self):
        # 定期计算每个对等方的上传速度，并选择最快的几个进行unchoke
        peer_speeds = [(peer, peer.get_upload_speed()) for peer in self.peer_connections]
        peer_speeds.sort(key=lambda x: x[1], reverse=True)
        top_peers = peer_speeds[:UNCHOKE_NUM]  # 选择最快的几个对等方进行unchoke
        #每次尝试一个随机的对等方
        if OPTIMISTIC_UNCHOKING == True:
            if len(peer_speeds) > UNCHOKE_NUM:
                top_peers.append(peer_speeds[random.randint(UNCHOKE_NUM,len(peer_speeds)-1)])
        for peer, speed in peer_speeds:
            if (peer, speed) in top_peers:
                if peer.peer_choked:
                    peer.send_message(UnChoke())
                    peer.peer_choked = False
            else:
                if not peer.peer_choked:
                    peer.send_message(Choke())
                    peer.peer_choked = True
            
            peer.reset_upload_speed()
    def init_piece_rarity(self):
        # piece 稀有度统计
        self.piece_rarity.clear()
        for peer in self.peer_connections:
            peer.wait_for_bitfield_update()  # 等待 bitfield 更新完成
            peer_bitfield= peer.peer_bitfield
            for i in range(len(peer_bitfield)):
                if peer_bitfield[i] == 1:
                    if i in self.piece_rarity:
                        self.piece_rarity[i] += 1
                    else:
                        self.piece_rarity[i] = 1
        self.rarest_pieces = sorted(self.piece_rarity.items(), key=lambda item: item[1])
        


class ClientMonitor(threading.Thread):
    '''
    监听线程
    '''
    def __init__(self, client_ip, client_port):
        threading.Thread.__init__(self)
        self.client_ip = client_ip
        self.client_port = client_port

    def run(self):
        # 监听端口，等待其他peer建立其的链接
        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen_socket.bind((self.client_ip, self.client_port))
        listen_socket.listen(CLIENT_LISTEN_MAX)

        while True:
            # 阻塞型接受新链接
            (new_socket, addr) = listen_socket.accept()
            logger.info('get new socket from listener port, addr is {}'.format(addr))
            # 开启新线程建立链接
            peer_connection = PeerConnection(new_socket,queue_lock)
            peer_connection.start()


def check_piece_hash_and_update(recv_piece_index,recv_raw_data):
    """ 检查收到的元数据是否和对应数据块的哈希值一致,如果一致则更新并返回1，否则就返回0 """
    if str(hashlib.sha1(recv_raw_data).digest()) == pieces_manager.hash_table[recv_piece_index]:
        logger.info('======= Piece index: {} data received without error in hash check ======='.format(recv_piece_index))
        pieces_manager.update_data_field(recv_piece_index, recv_raw_data)
        return 1
    else :
        logger.info('====== Piece index: {} data received with error in hash check! ======='.format(recv_piece_index))
        return 0


def init_config_file(config_file_name='client_config.json'):
    """ 如果没有配置文件，先初始化一个 """
    config = {}
    config['client_listen_max'] = 8
    config['client_port'] = 5555
    config['file_header_size'] = 8
    with open(config_file_name, 'w') as config_f:
        json.dump(config, config_f, indent=4)

if __name__ == "__main__":
    init_config_file()
    logger.info('in file client.py')
    logger.debug('test case (NULL) running...')
    logger.debug('test case finish')
    
#评估传输速度并进行unchoking需要有间隔地进行，以避免过于频繁的切换choke状态，故使用独立进程完成防止阻塞其他工作
class UnchokeManager(threading.Thread):
    def __init__(self, client):
        threading.Thread.__init__(self)
        self.client = client

    def run(self):
        while True:
            if UNCHOKE_TIME == 0:
                break
            time.sleep(UNCHOKE_TIME)
            self.client.manage_unchoking()
