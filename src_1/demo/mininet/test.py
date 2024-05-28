from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from traceback import print_tb
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel
from mininet.node import OVSController

class TestTopo(Topo):
    # "Single switch connected to n hosts."
    def build(self):
        info('*** Adding hosts\n')
        tracker = self.addHost('tracker', ip = '10.0.0.1')
        seed = self.addHost('seed', ip = '10.0.0.2')
        c2 = self.addHost('c2', ip = '10.0.0.3')

        info('*** Adding switches\n')
        s1 = self.addSwitch('s1')

        info('*** Creating links\n')
        self.addLink(tracker, s1)
        self.addLink(seed, s1)
        self.addLink(c2, s1)





def create_bittorrent_network():
    testTopo = TestTopo()
    net = Mininet(topo= testTopo, controller=OVSController)
    # info('*** Adding hosts\n')
    # tracker = net.addHost('tracker')
    # seed = net.addHost('seed')
    # c2 = net.addHost('c2')

    # info('*** Adding switches\n')
    # s1 = net.addSwitch('s1')

    # info('*** Creating links\n')
    # net.addLink(tracker, s1)
    # net.addLink(seed, s1)
    # net.addLink(c2, s1)
    info('*** Starting network\n')
    net.start()

    info('*** Running CLI\n')
    CLI(net)

    info('*** Stopping network\n')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    create_bittorrent_network()

