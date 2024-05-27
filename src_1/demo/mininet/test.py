from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel, info

def create_bittorrent_network():
    net = Mininet()

    info('*** Adding hosts\n')
    tracker = net.addHost('tracker')
    seed = net.addHost('seed')
    c2 = net.addHost('c2')

    info('*** Adding switches\n')
    s1 = net.addSwitch('s1')

    info('*** Creating links\n')
    net.addLink(tracker, s1)
    net.addLink(seed, s1)
    net.addLink(c2, s1)

    # net.addLink(tracker, seed)
    # net.addLink(tracker, c2)
    # net.addLink(seed, c2)

    info('*** Starting network\n')
    net.start()

    info('*** Running CLI\n')
    CLI(net)

    info('*** Stopping network\n')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    create_bittorrent_network()

