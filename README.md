# EmuEdge (Previously HybridNet)

EmuEdge is a scalable, Hi-Fi, highly-automated real-world network emulator based on Xen/Linux Netns/OvS, supporting edge computing prototyping and general network emulation with both container/vm and can be hybridly combined with existing physical infrastructures. Ultimately, EmuEdge is designed to emulate real-world experiments with high Degree of Realism (DoR) in lab settings instead of costly physical field deployments. An overview of EmuEdge architecture is shown below:
<p align="center">
<img src="https://github.com/ykzeng/emuedge/blob/master/docs/figures/arch.png" width="400" height="500">
</p>

## Cite this work

Zeng, Yukun, Mengyuan Chao, and Radu Stoleru. "EmuEdge: A hybrid emulator for reproducible and realistic edge computing experiments." 2019 IEEE International Conference on Fog Computing (ICFC). IEEE, 2019. ([Download](https://ieeexplore.ieee.org/document/8822062))

Biblatex entry:

```bibtex
@inproceedings{zeng2019emuedge,
  title={EmuEdge: A hybrid emulator for reproducible and realistic edge computing experiments},
  author={Zeng, Yukun and Chao, Mengyuan and Stoleru, Radu},
  booktitle={2019 IEEE International Conference on Fog Computing (ICFC)},
  pages={153--164},
  year={2019},
  organization={IEEE}
}
```

## Reproducing Experiments on EmuEdge
The following parameters can be configured to emulate/reproduce a realistic experiment:
* Network Topology: EmuEdge provides a JSON API based on adjacency list to define a network topology, with major network components virtualized in EmuEdge, we can easily replay a real-world topology as is on EmuEdge.
* Link Quality: Real-world networks are filled with noises and interferences, especially when wireless networks are gaining popularities nowadays. Comparing to previous work, EmuEdge provides more functionalities in emulating unrealiable networks. For each virtual link in EmuEdge, basic asymmetric/bidirectional network quality can be defined in multi perspectives of network (e.g., delay, packet loss). Moreover, with EmuEdge, we can define correlations in common network metrics to emulate network consistency and even reproduce a real-world network trace as is.
* Emulation Parameters (node configurations): Besides virtual routers and switches, currently EmuEdge supports two types of network nodes, container (linux netns) node for network-bounded emulation with high scalability and Xen VM node for computation-bounded experiments. The computing resources of EmuEdge server can be limited or dedicated to each node properly to achieve high DoR in computation with low costs.
* Mobility/Synthetic trace (in progress): EmuEdge aims to support synthetic traces (from traditional simulators) and mobility emulation in future work.
The figure below shows an example of extracting information from real experiment for repeated experiment replays on EmuEdge.
<p align="center">
<img src="https://github.com/ykzeng/emuedge/blob/master/docs/figures/reproduce.png" width="500" height="500">
</p>

## Usages
### Initing A Topology
The most intuitive way of interacting with EmuEdge is to define an edge topology through JSON adjacency list. Starting such a customized topology is simple:
```{r}
[root@xenserver ~]# cd /PATH/TO/hybridnet
[root@xenserver hybridnet]# python
Python 2.7.5 (default, Nov 20 2015, 02:00:19) 
[GCC 4.8.5 20150623 (Red Hat 4.8.5-4)] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> import xen
>>> xnet=xen.test_topo(topo='exps/twoway_simple.topo', start=True, nolog=False)
```
The `start` parameter controls if all devices will be booted automatically after setting up the topology, `nolog` parameter gives us the ability to select between fast no-log mode or debugging mode that shows useful logs. 

A `twoway_simple` topology configuration with DHCP and traffic shaping for network full-duplexity test can be found in the Appendix part, for more useful examples with probably routing, NAT and other advanced capabilities, pls. check out `topos/`.

### Interacting with the Topology

Through the script `ee` in our root directory, we can easily interact with containers in EmuEdge. Every container hosts can run real programs originally on your system as is like in MiniNet, an simple example as follows:
```{r}
[root@xenserver hybridnet]# ./ee h1 ip addr
1: lo: <LOOPBACK> mtu 65536 qdisc noop state DOWN qlen 1
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
389: h1-in0@if388: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc tbf state UP qlen 1000
    link/ether 0a:48:5b:51:35:dc brd ff:ff:ff:ff:ff:ff link-netnsid 0
    inet 10.0.0.2/24 scope global h1-in0
       valid_lft forever preferred_lft forever
    inet6 fe80::848:5bff:fe51:35dc/64 scope link 
       valid_lft forever preferred_lft forever
```

To interact with VM hosts, we can either do it with a Xen management console, or `ssh` to it through a container hosts that has connectivity with it. Currently, EmuEdge is limited in fully controlling VMs in terms of IP address, DHCP servers will assign random addresses which adds up the complexity of interacting with them. This can be probably resolved in the future with methods proposed in issue #13.

### Modify the Topology on-the-fly

After initing the topology, we can still modify the topology with EmuEdge Python APIs. For example, shutting down a VM with id `$node_id`:
```{r}
xnet.shutdown_node($node_id)
```
Creating a new Android VM with `Android` snapshot (if it is present in your XenServer), named `android-test`, overriding the default configuration with 2 cpus and 2048MB memory:
```{r}
xnet.create_new_dev("Android", "android-test", True, vcpu=2, mem=2048)
```
We left a more comprehensive API documents for interactive control over the topology as future work.

## Contents
### Directories
- bean/: EmuEdge core objects (e.g., vm, container, interface, etc) and functions

- utils/: helper/non-core utility functions

- trace/: network trace analysis module based on iproute2 and a sample real-world wifi trace

- bash/: some example scripts for manipulating virtual networks

- docs/: paper manuscript and referred figures go here
- topo/: testing topology sets covering all functions of EmuEdge, including paper experiments topologies

### Files:
- ee: container operation entry

- xen.py: main entry for EmuEdge

## Dependencies
### Necessary
* Xen and XenAPI
* Snapshots/Templates for the OSs to emulate in the target system
* Python 2
* Open vSwitch
* Linux iproute2

All our tests are conducted with Python 2.7.5 on XenServer 7.1.0, OvS version 2.3.2. If you are using also XenServer 7.1.0, all the other dependencies are by default installed.
### Optional
* Dnsmasq-2.79, for DHCP configurations, especially helpful in setting up VM connectivities.
* Linux tc, tbf, netem, iptables, for traffic shaping, rate limiting and routing support.

## Appendix
```{r}
[
  {
    "id":0,
    "name":"xswitch0",
    "type":0,
    "neighbors":[
      {
        "id":1
      },
      {
        "id":2,
        "link_control":{
          "rate":{
            "latency":"1ms",
            "burst":"47.5kb",
            "rate":"95Mbit"
          }
        }
      },
      {
        "id":3,
        "link_control":{
          "rate":{
            "latency":"1ms",
            "burst":"47.5kb",
            "rate":"95Mbit"
          }
        }
      },
      {
        "id":4,
        "link_control":{
          "rate":{
            "latency":"1ms",
            "burst":"47.5kb",
            "rate":"95Mbit"
          }
        }
      },
      {
        "id":5,
        "link_control":{
          "rate":{
            "latency":"1ms",
            "burst":"47.5kb",
            "rate":"95Mbit"
          }
        }
      }
    ] 
  },
  {
    "id":1,
    "name":"prouter0",
    "type":3,
    "nat":{
      "is_open":false
    },
    "dhcp":{
      "is_open":true,
      "if":0,
      "range_low":"10.0.0.50",
      "range_high":"10.0.0.254"
    },
    "ifs":[
      {
        "id":0,
        "ip":"10.0.0.1/24"
      }
    ],
    "neighbors":[
      {
        "if":0,
        "id":0
      }
    ]
  },
  {
    "id":2,
    "name":"centos1",
    "type":1,
    "image":"tcentos",
    "vcpus":2,
    "mem":2048,
    "override":false,
    "neighbors":[
      {
        "id":0,
        "link_control":{
          "rate":{
            "latency":"1ms",
            "burst":"47.5kb",
            "rate":"95Mbit"
          }
        }
      }
    ]
  },
  {
    "id":3,
    "name":"centos2",
    "type":1,
    "image":"tcentos",
    "vcpus":2,
    "mem":2048,
    "override":false,
    "neighbors":[
      {
        "id":0,
        "link_control":{
          "rate":{
            "latency":"1ms",
            "burst":"47.5kb",
            "rate":"95Mbit"
          }
        }
      }
    ]
  },
  {
    "id":4,
    "name":"h1",
    "type":3,
    "nat":{
      "is_open":false
    },
    "dhcp":{
      "is_open":false
    },
    "ifs":[
      {
        "id":0,
        "ip":"10.0.0.2/24"
      }
    ],
    "neighbors":[
      {
        "if":0,
        "id":0,
        "link_control":{
          "rate":{
            "latency":"1ms",
            "burst":"47.5kb",
            "rate":"95Mbit"
          }
        }
      }
    ]
  },
  {
    "id":5,
    "name":"h2",
    "type":3,
    "nat":{
      "is_open":false
    },
    "dhcp":{
      "is_open":false
    },
    "ifs":[
      {
        "id":0,
        "ip":"10.0.0.3/24"
      }
    ],
    "neighbors":[
      {
        "if":0,
        "id":0,
        "link_control":{
          "rate":{
            "latency":"1ms",
            "burst":"47.5kb",
            "rate":"95Mbit"
          }
        }
      }
    ]
  }
]
```
