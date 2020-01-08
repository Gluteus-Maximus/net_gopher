#!/bin/bash
# Called by tunnel-ssh.exp

# Parameters
user=$1
ip=$2
port=$3
cmd=$4

ssh -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $user@$ip -p $port "$cmd"
