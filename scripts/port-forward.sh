#!/bin/bash
# Called by port-forward.exp

# Parameters
local_port=$1
gate_ip=$2
gate_user=$3
remote_ip=$4
remote_port=$5

#ssh -f -N -S port-forward-socket -L localhost:$local_port:$remote_ip:$remote_port $gate_user@$gate_ip
ssh -q -o StrictHostKeyChecking=no -f -N -L localhost:$local_port:$remote_ip:$remote_port $gate_user@$gate_ip
