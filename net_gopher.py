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
  parser.add_argument('-g', '--gateCreds', action=_readable_file, required=True)
  parser.add_argument('-r', '--remoteCreds', action=_readable_file, required=True)
  parser.add_argument('-o', '--outputDir', action=_readable_dir, required=True)
  parser.add_argument('-b', '--bashScript', dest='bashScripts', nargs='+',
      action=_readable_file_append, required=False)
  parser.add_argument('-f', '--scpFiles', action=_readable_file, required=False)
  # adds fromDate and minusDays formatters
  parser.add_argument('-d', '--fromDate', action='append',
      metavar='DATE', dest='formatters', required=False) #type=dateFormatter
  parser.add_argument('-F', '--formatter', nargs=2, action='append',
      metavar=('KEY', 'VALUE'), dest='formatters', required=False) #type=dict
  #TODO: get gate password securely? file with permission restrictions?
  #TODO: support non-standard key formatters (-f nargs=2 key,value - append to formatters)
  #TODO: default values for standard key formatters
  return parser.parse_args()


class _readable_dir(ap.Action):
  def __call__(self, parser, namespace, values, option_string=None):
    if not os.path.isdir(values):
      raise ap.ArgumentError(self, "{0} is not a valid path".format(values))
    if os.access(values, os.R_OK):
      setattr(namespace,self.dest,values)
    else:
      raise ap.ArgumentError(self, "{0} is not a readable dir".format(values))


class _readable_file(ap.Action):
  def __call__(self, parser, namespace, values, option_string=None):
    if not os.path.isfile(values):
      raise ap.ArgumentError(self, "{0} is not a valid file".format(values))
    if os.access(values, os.R_OK):
      setattr(namespace,self.dest,values)
    else:
      raise ap.ArgumentError(self, "{0} is not a readable file".format(values))


class _readable_file_append(ap.Action):
  def __call__(self, parser, namespace, values, option_string=None):
    def _check_append(self, parser, namespace, values, option_string=None):
      if not os.path.isfile(values):
        raise ap.ArgumentError(self, "{0} is not a valid file".format(values))
      if os.access(values, os.R_OK):
        items = _copy.copy(_ensure_value(namespace, self.dest, []))
        items.append(values)
        setattr(namespace, self.dest, items)
      else:
        raise ap.ArgumentError(self, "{0} is not a readable file".format(values))
    if isinstance(values, list):
      for item in values:
        _check_append(self, parser, namespace, item, option_string=None)
    else:
      _check_append(self, parser, namespace, values, option_string=None)


def _ensure_value(namespace, name, value):
    if getattr(namespace, name, None) is None:
        setattr(namespace, name, value)
    return getattr(namespace, name)


def load_csv(csvFile):
  #TODO: include expected csv format (incl. header) in docs
  ''' # Doesn't skip comment lines
  with open(csvFile) as fp:
    reader = csv.reader(fp)
    next(reader)  # skip header
  return reader
  '''
  csvLst = list()
  with open(csvFile) as fp:
    # skip commented (#) lines
    csvLines = [line for line in fp.readlines() if not line.startswith("#")]
    #TODO: read one line at a time?? how to
    reader = csv.reader(csvLines)
    next(reader)  # skip header
  return reader


def format_commands(commandStr, formatters):
  '''
  @params:
    commandsLst: command string to be formatted.
    formatters: dictionary of formatters to apply to commands string.
      * Keys must match between commandStr and formatters
  '''
  try:
    return commandStr.format(**formatters)
  except KeyError as e:
    raise e  #TODO: write error mssg


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
