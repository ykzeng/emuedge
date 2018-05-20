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
out_if=$2
in_if=$3
ip_addr=$4

if [ "$(ovs-vsctl list-br | grep $name)" == $name ]; 
then
	ip link add dev $out_if type veth peer name $in_if
	ip link set $out_if up
	ovs-vsctl add-port $name $out_if
	ip netns add $name
	ip link set $in_if netns $name
	ip netns exec $name ip addr add $ip_addr dev $in_if
	ip netns exec $name ip link set $in_if up
else
	echo "the bridge $name is not ready yet!"
	exit 2
fi

