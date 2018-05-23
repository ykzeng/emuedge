#!/bin/bash
# Usage:
# ./xrouter.sh name, external, internal, ipaddr
# @name: name of the bridge created for xrouter
# @external: external interface of xrouter on the associated bridge
# @internal: internal interface of xrouter in the namespace
# @ipaddr: the ip address we want to assign the xrouter
# err code:
# 1. unspecified
# 2. no such bridge is present
name=$1
lan_ip=$2
wan_ip=$3
lan_if=$4
wan_if=$5

ip netns exec $name sysctl -w net.ipv4.ip_forward=1
ip netns exec $name iptables -t nat -A POSTROUTING -s $lan_ip -o $wan_if -j SNAT --to $wan_ip
#ip netns exec $netns iptables -t nat -A POSTROUTING -s $wan_ip -o $wan_if -j SNAT --to-source $lan_ip
ip netns exec $name iptables -A INPUT -i $lan_if -j ACCEPT
ip netns exec $name iptables -A INPUT -i $wan_if -m state --state ESTABLISHED,RELATED -j ACCEPT
ip netns exec $name iptables -A OUTPUT -j ACCEPT