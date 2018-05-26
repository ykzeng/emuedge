ip netns add n1
ip netns add n2
ip netns add n3

ip link add t1 type veth peer name t2
ip link add t3 type veth peer name t4
ip link add t5 type veth peer name t6

ovs-vsctl add-br br1
ovs-vsctl add-port br1 t2
ovs-vsctl add-port br1 t4
ovs-vsctl add-port br1 t6

ip link set t1 netns n1
ip link set t3 netns n2
ip link set t5 netns n3

ip netns exec n1 ifconfig t1 10.0.0.1/24 up
ip netns exec n2 ifconfig t3 10.0.0.2/24 up
ip netns exec n3 ifconfig t5 10.0.0.3/24 up
ip netns exec n1 ip link set lo up
ip netns exec n2 ip link set lo up
ip netns exec n3 ip link set lo up

ip link set t2 up
ip link set t4 up
ip link set t6 up
