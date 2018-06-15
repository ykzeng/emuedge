#!/usr/bin/python

"""
This is a simple example that demonstrates multiple links
between nodes.
"""

from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.topo import Topo
from mininet.link import TCLink

def runMultiLink():
    "Create and run multiple link network"
    topo = simpleMultiLinkTopo( n=4 )
    net = Mininet( topo=topo, link=TCLink )
    net.start()
    CLI( net )
    net.stop()

class simpleMultiLinkTopo( Topo ):
    "Simple topology with multiple links"

    def __init__( self, n, **kwargs ):
        Topo.__init__( self, **kwargs )
        hosts=[None]*n
        for i in range(0, n):
            hosts[i]=self.addHost('h'+str(i))

        s1 = self.addSwitch( 's1' )
        opts=dict(bw=95)
        for i in range(0, n):
            self.addLink(hosts[i], s1, **opts)
            self.addLink(s1, hosts[i], **opts)

if __name__ == '__main__':
    setLogLevel( 'info' )
    runMultiLink()
