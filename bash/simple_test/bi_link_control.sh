# set_link_prop.sh [1] [2]
# 1. if_name: of the interface to controll
# 2. ifb_name: the intermediate interface we push the ingress traffic to for control

if_name=$1
ifb_name=$2

# enable ifb module in linux
#modprobe ifb numifbs=1

# up ifb interfaces
ip link set $ifb_name up
# redirect ingress traffic on $if_name (the external if in root netns)
tc qdisc add dev $if_name handle ffff: ingress
tc filter add dev $if_name parent ffff: protocol ip u32 match u32 0 0 action mirred egress redirect dev $ifb_name
tc qdisc add dev $ifb_name root handle 1: tbf rate 256kbit buffer 1600 limit 3000
tc qdisc add dev $ifb_name parent 1: handle 2: netem delay 100ms 20ms distribution normal
