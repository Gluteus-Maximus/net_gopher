#!/usr/bin/env python3
'''
For Nix Systems Only.
'''
import sys
import os
import argparse as ap
import re
import time
import pathlib
import csv
import subprocess as sp
import copy as _copy

#TODO: capture output from scripts

# Global Script Filepaths
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


def main():
  args = getargs()
  print(args)


def getargs():
  #TODO: how to allow multiple of a flag?
  #d = defaults.copy()
  #d.update(os.environ)
  #d.update(command_line_args)
  #ChainMap
  parser = ap.ArgumentParser()  #TODO: add desc
  parser.add_argument('-r', '--remoteCreds', action=readable_file, required=True)
  parser.add_argument('-b', '--bashScript', dest='bashScripts',
      action=readable_file_append, required=True)
  parser.add_argument('--test', type=int, required=True)
  #parser.add_argument('', required=True)
  #parser.add_argument('', required=True)
  #TODO: get gate password securely? file with permission restrictions?
  #TODO: support non-standard key formatters (-f nargs=2 key,value - append to formatters)
  #TODO: default values for standard key formatters
  try:
    return parser.parse_args()
  except ap.ArgumentTypeError as e:
    #TODO: print usage
    print(e, file=sys.stderr)
    exit(1)


class readable_dir(ap.Action):
  def __call__(self, parser, namespace, values, option_string=None):
    prospective_dir=values
    if not os.path.isdir(prospective_dir):
      raise ap.ArgumentError(self, "{0} is not a valid path".format(prospective_dir))
    if os.access(prospective_dir, os.R_OK):
      setattr(namespace,self.dest,prospective_dir)
    else:
      raise ap.ArgumentError(self, "{0} is not a readable dir".format(prospective_dir))


class readable_file(ap.Action):
  def __call__(self, parser, namespace, values, option_string=None):
    prospective_file=values
    if not os.path.isfile(prospective_file):
      raise ap.ArgumentError(self, "{0} is not a valid file".format(prospective_file))
    if os.access(prospective_file, os.R_OK):
      setattr(namespace,self.dest,prospective_file)
    else:
      raise ap.ArgumentError(self, "{0} is not a readable file".format(prospective_file))


class readable_file_append(ap.Action):
  def __call__(self, parser, namespace, values, option_string=None):
    prospective_file=values
    if not os.path.isfile(prospective_file):
      raise ap.ArgumentError(self, "{0} is not a valid file".format(prospective_file))
    if os.access(prospective_file, os.R_OK):
      items = _copy.copy(_ensure_value(namespace, self.dest, []))
      items.append(prospective_file)
      setattr(namespace, self.dest, items)
    else:
      raise ap.ArgumentError(self, "{0} is not a readable file".format(prospective_file))


def _ensure_value(namespace, name, value):
    if getattr(namespace, name, None) is None:
        setattr(namespace, name, value)
    return getattr(namespace, name)


def parse_csv(csvFile):
  #TODO: include expected csv format (incl. header) in docs
  csvLst = list()
  with open(csvFile) as fp:
    # skip commented (#) lines
    csvLines = [line for line in fp.readlines() if not line.startswith("#")]
    #TODO: read one line at a time?? how to
    reader = csv.reader(csvLines)
    next(reader)  # skip header
  return reader
  '''
    for values in reader:
      csvLst.append(values)
  return csvLst
  '''


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
  commands = re.sub("\s*;\s*", ";", commands)  # strip w/s around ';'
  commands = re.sub(";+", ";", commands).strip(";")  # fix repeated ';'
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


def tunneled_ssh_loop(localPort, credLst, gateCreds, commandStr,
      outputFilepath, errlogFilepath):  #TODO: add jsonFilepath
  '''
  @params:
    credLst: nested list of endpoint creds.
    gateCreds: Credentials object for ssh tunnel gateway.
  '''
  for remoteIP, remotePort, remoteUser, remotePassword in credLst:
    #TODO: store/delete forwarder socket
    #TODO: check if localport in use, kill process/block until open
    forwardRetval = port_forward(
        localPort,
        gateCreds.ip,
        gateCreds.user,
        gateCreds.password,
        remoteIP,
        remotePort
        )
    sshRetval = ssh_session(
        remoteUser,
        "localhost",
        localPort,
        remotePassword,
        commandStr
        )
    print(sshRetval.stdout.decode('utf-8'))  #TODO DBG
    sp.run("pkill ssh", shell=True, stdout=sp.PIPE, stderr=sp.PIPE)  #TODO DBG
    #TODO: log return data
  pass


def ssh_session(user, ip, port, password, commandStr):
  #print("DBG: {}".format(commands))
  retval = sp.run(
      "expect {} {} {} {} {} {}".format(
        sshScriptPath,
        user,
        ip,
        port,
        password,
        '"{}"'.format(commandStr)
        ),
      shell=True,
      stdout=sp.PIPE,
      stderr=sp.PIPE)
  #TODO: check retval.returncode, log failure
  return retval


def tunneled_scp_loop():
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


if __name__ == "__main__":
  main()
