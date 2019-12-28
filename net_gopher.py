#!/usr/bin/env python3
'''
For Nix Systems Only.
'''
import os
import pathlib
import re
import time
import csv
import subprocess as sp

#TODO: capture output from scripts

fileDir = os.path.dirname(os.path.realpath(__file__))
scriptsDir = os.path.join(fileDir, "scripts/")
forwarderScriptPath = os.path.join(scriptsDir, "port-forward.exp")
sshScriptPath = os.path.join(scriptsDir, "ssh-session.exp")
scpScriptPath = os.path.join(scriptsDir, "scp-session.exp")


class Credentials():
  def __init__(self, ip, user, password):
    self.ip = ip
    self.user = user
    self.password = password


def getargs():
  pass


def parse_creds(credFile):
  credLst = list()
  with open(credFile) as fp:
    csvLines = [line for line in fp.readlines() if not line.startswith("#")]
    reader = csv.reader(csvLines)
    for cred in reader:
      credLst.append(cred)
  return credLst


def format_commands(commandStr, formatters):
  '''
  @params:
    commandsLst: command string to be formatted.
    formatters: dictionary of formatters to apply to commands string.
      * Keys must match between commandStr and formatters
  '''
  return commandStr.format(**formatters)
  pass


def join_commands(commandsLst):
  commands = ";".join(commandsLst)
  commands = re.sub("\s*;\s*", ";", commands)
  commands = re.sub(";+", ";", commands).strip(";")
  return commands


def port_forward(local_port, gate_ip, gate_user, gate_pw,
        remote_ip, remote_port):
  retval = sp.run(
      "expect {} {} {} {} {} {} {}".format(
        forwarderScriptPath,
        local_port,
        gate_ip,
        gate_user,
        gate_pw,
        remote_ip,
        remote_port
        ),
      shell=True,
      stdout=sp.PIPE,
      stderr=sp.PIPE)
  #TODO: check retval.returncode, log failure
  return retval


def ssh_session_loop(sshParams, credLst, gateCreds, ):
  pass


def ssh_session(user, ip, port, password, commands):
  print("DBG: {}".format(commands))
  retval = sp.run(
      "expect {} {} {} {} {} {}".format(
        sshScriptPath,
        user,
        ip,
        port,
        password,
        '"{}"'.format(commands)
        ),
      shell=True,
      stdout=sp.PIPE,
      stderr=sp.PIPE)
  #TODO: check retval.returncode, log failure
  return retval


def scp_session_loop():
  pass


def scp_session():
  '''
  retval = sp.run(
      "expect {} {} {} {} {} {}".format(
        scpScriptPath,
        ,
        ,
        ,
        ,
        ,
        ),
      shell=True,
      stdout=sp.PIPE,
      stderr=sp.PIPE)
  #TODO: check retval.returncode, log failure
  '''
  pass


def log_session_data_raw(ip, data, logfile):
  pass


def log_session_data_json():
  pass
