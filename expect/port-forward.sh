#!/bin/bash
# Called by port-forward.exp

# Parameters
local_port=$1
gate_ip=$2
gate_ssh_port=$3
gate_user=$4
remote_ip=$5
remote_ssh_port=$6

#ssh -f -N -S port-forward-socket -L localhost:$local_port:$remote_ip:$remote_port $gate_user@$gate_ip
ssh -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -f -N -L localhost:$local_port:$remote_ip:$remote_ssh_port $gate_user@$gate_ip -p $gate_ssh_port
