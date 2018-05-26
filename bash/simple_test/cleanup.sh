ip netns del n1
ip netns del n2
ip netns del n3

ovs-vsctl del-br br1
ip link set ifb0 down
