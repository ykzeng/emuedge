ip netns add n1
ip netns add n2

ip link add t1 type veth peer name t2
ip link add t3 type veth peer name t4

ovs-vsctl add-br br1
ovs-vsctl add-port br1 t2
ovs-vsctl add-port br1 t4

ip link set t1 netns n1
ip link set t3 netns n2

ip netns exec n1 ifconfig t1 10.0.0.1/24 up

ip link set t2 up
ip link set t4 up
