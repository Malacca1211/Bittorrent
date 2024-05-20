from mininet.net import Mininet
from mininet.node import Controller, OVSKernelSwitch, Host
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
import os

def setup_environment():
    """设置测试环境，创建必要的文件和.torrent文件在指定的目录下。"""
    # base_dir = os.getcwd()  # 获取当前工作目录
    base_dir = os.path.join(os.getcwd(), 'test')
    seed_dir = os.path.join(base_dir, 'seed')
    os.makedirs(seed_dir, exist_ok=True)

    test_file = os.path.join(seed_dir, 'testfile')
    torrent_file_name = test_file + '.torrent'
    
    # 创建一个大文件用于测试
    os.system(f'dd if=/dev/urandom of={test_file} bs=1M count=10')
    
    # 创建.torrent文件，注意更改跟踪器URL
    tracker_url = "http://10.0.0.99:8000/announce"  # 示例tracker URL
    os.system(f'python create_torrent.py {test_file} {tracker_url} {torrent_file_name}')
    
    return test_file, torrent_file_name

def start_tracker(net):
    """启动跟踪器服务器"""
    tracker = net.addHost('tracker', ip='10.0.0.99')
    net.addLink(tracker, net.switches[0])
    tracker.cmd('python tracker.py --host 10.0.0.99 --port 8000 &')
    # tracker.cmd('python tracker.py &')
    return tracker

def test_mininet():
    net = Mininet(controller=Controller, switch=OVSKernelSwitch, link=TCLink)
    c0 = net.addController('c0')
    switch = net.addSwitch('s1')
    net.start()

    # 设置环境和启动跟踪器
    test_file, torrent_file = setup_environment()
    tracker = start_tracker(net)

    # 添加和启动BitTorrent客户端
    seed = net.addHost('seed', ip='10.0.0.1')
    peer1 = net.addHost('peer1', ip='10.0.0.2')
    peer2 = net.addHost('peer2', ip='10.0.0.3')

    net.addLink(seed, switch)
    net.addLink(peer1, switch)
    net.addLink(peer2, switch)

    seed.cmd(f'python bittorrent.py --torrent_file {torrent_file} --mode seed &')
    peer1.cmd(f'mkdir -p {os.path.join(os.getcwd(), "test/peer1")} && python bittorrent.py --torrent_file {torrent_file} --mode peer &')
    peer2.cmd(f'mkdir -p {os.path.join(os.getcwd(), "test/peer2")} && python bittorrent.py --torrent_file {torrent_file} --mode peer &')

    info('*** Running CLI\n')
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    test_mininet()
