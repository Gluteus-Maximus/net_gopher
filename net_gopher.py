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
#TODO: initialize template files (creds)

__DBG = True  #TODO DBG

# Global Filepaths
fileDir = os.path.dirname(os.path.realpath(__file__))
scriptsDir = os.path.join(fileDir, "expect/")
sshMasterScriptPath = os.path.join(scriptsDir, "ssh-socket-open-master.exp")
forwarderScriptPath = os.path.join(scriptsDir, "port-forward.exp")
sshScriptPath = os.path.join(scriptsDir, "ssh-session.exp")
scpScriptPath = os.path.join(scriptsDir, "scp-session.exp")
#TODO: error log filepath


#TODO
__all__ = [
    ]

#remoteCreds/gateCreds fields ['ip', 'ssh_port', 'username', 'password']


def main():
  args = get_args()
  if __DBG: print(args) #TODO DBG
  #TODO: mkdir from dtg
  #TODO: store raw log
  #TODO: store json
  #TODO: mkdir for each ip (if scpFiles??)
  #TODO: store errors
  # unpack gateCreds from file
  gateIP, gatePort, gateUser, gatePW = next(load_csv(args.gateCreds))
  socketPath = os.path.join(fileDir, ".gopher_socket_{}".format(time.strftime("%Y%m%d%H%M%S")))

  try:
    # open master
    retval = ssh_socket_open_master(socketPath, gateIP, gatePort, gateUser, gatePW)
    if __DBG:  #TODO DBG
      print("\nSocket STDOUT:\n",
          retval.stdout.decode('utf-8'), sep="")  #TODO DBG
      print("\nSocket STDERR:\n", retval.stderr.decode('utf-8'))  #TODO DBG
    # loop scripts
    if args.bashScripts:
      commandStr = ingest_commands(args.bashScripts, args.formatters)
      remoteCreds = load_csv(args.remoteCreds)
      tunneled_ssh_loop(socketPath, args.localport, remoteCreds, commandStr,
          args.outputDir, os.path.join(args.outputDir, "/error.log"))  #TODO: error log filepath
    # loop scp
    if args.scpFiles:
      scpFiles = load_csv(args.scpFiles) #TODO: may cause issues with iter instead of list
  except Exception as e:  #TODO: specify
    raise e #TODO DBG
    pass  #TODO: react
  finally:
    # close master
    #TODO: try/exc warn socket (name) not closed, give cli command to close, log
    retval = ssh_socket_close_master(socketPath)
    if __DBG:  #TODO DBG
      print("\nSocket STDOUT:\n",
          retval.stdout.decode('utf-8'), sep="")  #TODO DBG
      print("\nSocket STDERR:\n", retval.stderr.decode('utf-8'))  #TODO DBG


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


def _DBG_readable_file(filepath):  #TODO DBG - remove
  if not os.path.isfile(filepath):
    print("DBG Readable File: '{}': file is invalid".format(filepath))
  if os.access(filepath, os.R_OK):
    print("DBG Readable File: '{}': file is valid".format(filepath))
  else:
    print("DBG Readable File: '{}': file isn't readable".format(filepath))


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
  #TODO: call _key_val_pair with keys and modified values. DON'T overwrite existing values.
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
  #TODO: validate in range
  return int(port)


def load_csv(csvFile):
  #TODO: include expected csv format (incl. header) in docs
  ''' # Doesn't skip comment lines (subclass reader?)
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


def join_commands(commandsLst):
  # comments must be on their own line or no following commands will be run
  #TODO: commands have trailing newline
  commands = [cmd for cmd in commandsLst if not cmd.startswith("#")]
  commands = ";".join(commands)
  commands = re.sub("\s*;\s*", ";", commands)  # strip w/s around ';'
  commands = re.sub(";+", ";", commands).strip(";").strip()  # fix repeated ';'
  return commands


def ssh_socket_open_master(socketPath, gateIP, gatePort, gateUser, gatePW):
  #print( "expect {} {} {} {} {} {}".format(sshMasterScriptPath, gateIP, gatePort, gateUser, gatePW, socketPath))
  #TODO: check retval, raise exc
  #TODO: while counter && not file.exists
  retval = sp.run(
      # parameter after 'exit' is irrelevant, but something must be put in this slot
      "expect {} {} {} {} {} {}".format(
        sshMasterScriptPath,
        gateIP,
        gatePort,
        gateUser,
        gatePW,
        socketPath
        ),
      shell=True,
      stdout=sp.PIPE,
      stderr=sp.PIPE
      )
  #TODO: prevent "ControlSocket ssh_socket already exists, disabling multiplexing" from creating session
  time.sleep(1)
  #TODO: raise exc if socketPath fails to create (attempt N times?)
  return retval


def ssh_socket_close_master(socketPath):
  #TODO: check retval, raise exc
  retval = sp.run(
      # parameter after 'exit' is irrelevant, but something must be put in this slot
      "ssh -S {} -O exit towel@42".format(socketPath),
      shell=True,
      stdout=sp.PIPE,
      stderr=sp.PIPE
      )
  return retval


_sshOptions = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
# parameter after forwarder settings is irrelevant, but something must be put in this spot
_sshSocketForwardFormatStr = "ssh -S {} -O {} {} -L localhost:{}:{}:{} towel@42 -fN"


def ssh_socket_forward(action, socketPath, localPort, remoteIP, remotePort):
  assert action in ["forward", "cancel"], \
      "ERROR: ssh_socket_forward: action parameter must be in [\"forward\", \"cancel\"]"
  retval = sp.run(
      _sshSocketForwardFormatStr.format(
        socketPath,
        action,
        _sshOptions,
        localPort,
        remoteIP,
        remotePort
        ),
      shell=True,
      stdout=sp.PIPE,
      stderr=sp.PIPE
      )
  return retval


def tunneled_ssh_loop(socketPath, localPort, remoteCreds, commandStr, outputDir, errlogPath):
  #TODO: add jsonPath
  for remoteIP, remotePort, remoteUser, remotePW in remoteCreds:
    #TODO: check stderr for spawn id * not open, attempt again, log (keep counter, quit after X)
    #c = 0
    #while c <= 2:
    try:
      retval = ssh_socket_forward("forward", socketPath, localPort, remoteIP, remotePort)
      if __DBG:  #TODO DBG
        print("\nForwarder STDERR:\n", retval.stderr.decode('utf-8'))  #TODO DBG
      #TODO: check return, retry
      #else:
      #  raise Exception("DBG something DBG")
      #TODO: cut out extra params
      sshRetval = ssh_session(remoteUser, "localhost", localPort, remotePW, commandStr)
      #TODO: log data & errors (join ip, user, date, data)
      print("\nSession STDOUT:\n", "{}@{}\n".format(remoteUser, remoteIP),
          sshRetval.stdout.decode('utf-8'), sep="")  #TODO DBG
      print("\nSession STDERR:\n", sshRetval.stderr.decode('utf-8'))  #TODO DBG
    except Exception as e:  #TODO: specify & define response
      pass
    finally:
      retval = ssh_socket_forward("cancel", socketPath, localPort, remoteIP, remotePort)
    #TODO: check return, retry


def ssh_session(user, ip, port, password, commandStr):
  #print("DBG: {}".format(commands))
  #TODO: cut out extra params
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
  #TODO: log errors
  #files = list(csv_load)  # will be list of lists
  # for stuff in remoteCreds: forward, scp files, cancel
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
