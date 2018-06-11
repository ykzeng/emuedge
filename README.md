# EmuEdge (Previously HybridNet)

A scalable, Hi-Fi, highly-automated real-life network emulator based on Xen/Linux Netns/OvS, supporting edge computing prototyping and general network emulation with both container/vm/physical machines.

## Usages
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
