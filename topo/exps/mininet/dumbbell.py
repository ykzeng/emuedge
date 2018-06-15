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
    topo = simpleMultiLinkTopo( n=2 )
    net = Mininet( topo=topo, link=TCLink )
    net.start()
    CLI( net )
    net.stop()

class simpleMultiLinkTopo( Topo ):
    "Simple topology with multiple links"

    def __init__( self, n, **kwargs ):
        Topo.__init__( self, **kwargs )
        hosts=[None]*(n*2)

        for i in range(0, n):
            hosts[i]=self.addHost('h'+str(i))

        for i in range(n, n*2):
            hosts[i]=self.addHost('h'+str(i))

        s1 = self.addSwitch( 's1' )
        for i in range(0, n):
            self.addLink(hosts[i], s1)

        s2 = self.addSwitch( 's2' )
        for i in range(n, n*2):
            self.addLink(hosts[i], s2)
        
        opts=dict(bw=95)
        self.addLink(s1, s2, **opts)

if __name__ == '__main__':
    setLogLevel( 'info' )
    runMultiLink()
