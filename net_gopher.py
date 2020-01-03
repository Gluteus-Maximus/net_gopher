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

# Global Filepaths
fileDir = os.path.dirname(os.path.realpath(__file__))
scriptsDir = os.path.join(fileDir, "expect/")
sshMasterScriptPath = os.path.join(scriptsDir, "ssh-open-master-socket.exp")
forwarderScriptPath = os.path.join(scriptsDir, "port-forward.exp")
sshScriptPath = os.path.join(scriptsDir, "ssh-session.exp")
scpScriptPath = os.path.join(scriptsDir, "scp-session.exp")
#TODO: error log filepath


#TODO
__all__ = [
    ]

#remoteCreds/gateCreds fields ['ip', 'ssh_port', 'username', 'password']


class Credentials():
  def __init__(self, ip, sshPort, user, password):
    self.ip = ip
    self.sshPort = sshPort
    self.user = user
    self.password = password


def main():
  args = get_args()
  #print(args) #TODO DBG
  #try:
  #print(next(load_csv(args.gateCreds)))  #TODO DBG
  #TODO: mkdir from dtg
  #TODO: store raw log
  #TODO: store json
  #TODO: mkdir for each ip (if scpFiles??)
  #TODO: store errors
  gateCreds = Credentials(*next(load_csv(args.gateCreds)))
  if args.bashScripts:
    commandStr = ingest_commands(args.bashScripts, args.formatters)
    remoteCreds = load_csv(args.remoteCreds)
    #print(commands)  #TODO DBG
    # ssh loop
    tunneled_ssh_loop(args.localport, remoteCreds, gateCreds, commandStr, args.outputDir,
        os.path.join(args.outputDir, "/error.log"))  #TODO: error log filepath
  if args.scpFiles:
    scpFiles = load_csv(args.scpFiles) #TODO: may cause issues with iter instead of list
    # scp loop
  #except Exception as e:
  #  print("ERROR: {}".format(e), file=sys.stderr)  #TODO DBG

def get_args():
  #TODO: how to allow multiple of a flag?
  #d = defaults.copy()
  #d.update(os.environ)
  #d.update(command_line_args)
  #ChainMap
  parser = ap.ArgumentParser()  #TODO: add desc
  parser.add_argument('-g', '--gateCreds', action=_readable_file, required=True)
  parser.add_argument('-r', '--remoteCreds', action=_readable_file, required=True)
  parser.add_argument('-o', '--outputDir', action=_readable_dir, required=True)
  #TODO: check if port in use through _valid_port, or use action _available_port
  parser.add_argument('-p', '--localport', type=_valid_port, required=False,
      default=22222)
  #parser.add_argument('-j', '--jsonFile', action=_readable_file, required=True)
  parser.add_argument('-b', '--bashScript', dest='bashScripts', nargs='+',
      action=_readable_file_append, required=False,
      help="###bashScript help -- comments must be on their own line")
  # comments must be on their own line or no following commands will be run
  parser.add_argument('-f', '--scpFiles', action=_readable_file, required=False)
  # adds fromDate and minusDays formatters
  parser.add_argument('-d', '--fromDate', action='append',
      metavar='DATE', dest='formatters', required=False, type=_date_formatter,
      help="###fromDate help, builtin formatter. converts, keys X/Y.")
  parser.add_argument('-F', '--formatter', nargs=2, required=False,
      metavar=('KEY', 'VALUE'), dest='formatters',
      type=str, action=_update_dict_nargs,
      help="###formatter help")
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


def _store_key_pairs_factory(separator):
  class _store_key_pairs(ap.Action):
    '''
    @func: Takes key value pairs (separated by 'separator') and updates dict 'dest'
    '''
    #TODO: raise ArgumentError if dest is not dict
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
      self._nargs = nargs
      super(_store_key_pairs, self).__init__(option_strings, dest, nargs=nargs, **kwargs)
    def __call__(self, parser, namespace, values, option_string=None):
      if isinstance(getattr(namespace, self.dest), dict):
        my_dict = getattr(namespace, self.dest)
      else:
        my_dict = {}
      for kv in values:
        k,v = kv.split(separator)
        my_dict[k] = v
      setattr(namespace, self.dest, my_dict)
  return _store_key_pairs


def _key_val_pair(keyValPair):
  '''
  @func: Takes key value pair (iterable) and returns dict
  @param:
    keyValPair: iterable of at least len 2, key and value(s).
    - If more than one value is provided (ie len greater than 2), these will
    - be stored as a list.
  '''
  print(keyValPair)
  if len(keyValPair) < 2:
    raise ap.ArgumentTypeError(
        "_key_val_pair: invalid input '{}': input must have at least two indices".format(keyValPair))
  elif len(keyValPair) == 2:
    key, value = keyValPair
  else:
    key, *value = keyValPair
  return dict([(key, value)])


def _date_formatter(dateStr):
  #call _key_val_pair
  pass


class _update_dict_nargs(ap.Action):
  #TODO: raise ArgumentError if dest or value are not dict
  def __init__(self, option_strings, dest, nargs=None, **kwargs):
    self._nargs = nargs
    super(_update_dict_nargs, self).__init__(option_strings, dest, nargs=nargs, **kwargs)
  def __call__(self, parser, namespace, values, option_string=None):
    '''
    @func: Takes dict 'values' and updates dict 'namespace.dest'
    '''
    # if dest is not a dictionary, held data will be lost
    if isinstance(getattr(namespace, self.dest), dict):
      my_dict = getattr(namespace, self.dest)
    else:
      my_dict = {}
    my_dict.update(_key_val_pair(values))
    setattr(namespace, self.dest, my_dict)


def _valid_port(port):
  #TODO: validate
  return int(port)


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


def ingest_commands(bashScripts, formatters):
  commands = list()
  for filepath in bashScripts:
    with open(filepath) as fp:
      commands.extend(fp.readlines())
  #commands = format_commands(join_commands(commands), formatters)
  commands = join_commands(commands)
  #try:
  if formatters is None:
    return commands
  else:
    return commands.format(**formatters)
  #except KeyError as e:

"""
def format_commands(commandStr, formatters):
  '''
  @params:
    commandsLst: command string to be formatted.
    formatters: dictionary of formatters to apply to commands string.
      * Keys must match between commandStr and formatters
  '''
  if formatters is None:
    return commandStr
  try:
    return commandStr.format(**formatters)
  except KeyError as e:
    raise e  #TODO: write error mssg
"""

def join_commands(commandsLst):
  # comments must be on their own line or no following commands will be run
  #TODO: commands have trailing newline
  commands = [cmd for cmd in commandsLst if not cmd.startswith("#")]
  commands = ";".join(commands)
  commands = re.sub("\s*;\s*", ";", commands)  # strip w/s around ';'
  commands = re.sub(";+", ";", commands).strip(";").strip()  # fix repeated ';'
  return commands


def port_forward(local_port, gate_ip, gate_ssh_port, gate_user, gate_pw,
        remote_ip, remote_ssh_port):
  retval = sp.run(
      "expect {} {} {} {} {} {} {} {}".format(
        forwarderScriptPath,
        local_port,
        gate_ip,
        gate_ssh_port,
        gate_user,
        gate_pw,
        remote_ip,
        remote_ssh_port
        ),
      shell=True,
      stdout=sp.PIPE,
      stderr=sp.PIPE)
  #TODO: check retval.returncode, log failure
  return retval


def ssh_socket_open_master(socketPath, gateIP, gateSshPort, gateUser, gatePW):
  pass


def ssh_socket_close_master(socketPath):
  pass


def ssh_socket_open_forward(socketPath, localPort, remoteIP, remotePort):
  pass


def ssh_socket_close_forward(socketPath, localPort, remoteIP, remotePort):
  pass


def tunneled_ssh_loop(localPort, remoteCreds, gateCreds, commandStr,
      outputDir, errlogFilepath):  #TODO: add jsonFilepath
  '''
  @params:
    remoteCreds: nested list of endpoint creds.
    gateCreds: Credentials object for ssh tunnel gateway.
  '''
  for remoteIP, remotePort, remoteUser, remotePassword in remoteCreds:
    #TODO: store/delete forwarder socket
    #TODO: check if localport in use, kill process/block until open
    forwardRetval = port_forward(
        localPort,
        gateCreds.ip,
        gateCreds.sshPort,
        gateCreds.user,
        gateCreds.password,
        remoteIP,
        remotePort
        )
    #print("\nForwarder STDOUT:\n", forwardRetval.stdout.decode('utf-8'), sep="")  #TODO DBG
    print("\nnForwarder STDERR:\n", forwardRetval.stderr.decode('utf-8'))  #TODO DBG
    #TODO: check stderr for spawn id * not open, attempt again, log (keep counter, quit after X)
    sshRetval = ssh_session(
        remoteUser,
        "localhost",
        localPort,
        remotePassword,
        commandStr
        )
    print("\nSession STDOUT:\n", "{}@{}\n".format(remoteUser, remoteIP),
        sshRetval.stdout.decode('utf-8'), sep="")  #TODO DBG
    print("\nSession STDERR:\n", sshRetval.stderr.decode('utf-8'))  #TODO DBG
    sp.run("pkill ssh", shell=True, stdout=sp.PIPE, stderr=sp.PIPE)  #TODO: better tunnel closer
    #TODO: check stderr for spawn id * not open, attempt again, log (keep counter, quit after X)
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
