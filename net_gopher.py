#!/usr/bin/env python3
'''
For Nix Systems Only.
'''
def getargs():
  pass


def parse_creds(credFile):
  pass


def format_ssh_commands(cmdStr, formatters):
  pass


def port_forward(local_port, gate_ip, gate_user, gate_pw, remote_ip, remote_port):
  pass


def ssh_session_loop(sshParams, credLst, gateCreds, ):
  pass


def ssh_session(user, ip, port, password, commands):
  pass


def scp_session_loop():
  pass


def log_session_data_raw(ip, data, logfile):
  pass


def log_session_data_json():
  pass
