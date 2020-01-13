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
#TODO: add indexed start (for failed/disconnected sessions)

_DBG = True  #TODO DBG

# Global Filepaths
fileDir =             os.path.dirname(os.path.realpath(__file__))
userDir =             os.path.join(fileDir, "user/")
defaultOutputDir =    os.path.join(userDir, "output/", time.strftime("%Y-%m-%d_%H%M%S"))
#errorLogDir =         os.path.join(fileDir, "log/")
#errorLogPath =        os.path.join(errorLogDir, "gopher.log")
scriptsDir =          os.path.join(fileDir, "expect/")
sshMasterScriptPath = os.path.join(scriptsDir, "ssh-socket-open-master.exp")
forwarderScriptPath = os.path.join(scriptsDir, "port-forward.exp")
sshScriptPath =       os.path.join(scriptsDir, "ssh-session.exp")
scpScriptPath =       os.path.join(scriptsDir, "scp-session.exp")
socketPath = os.path.join(fileDir, ".gopher_socket_{}".format(time.strftime("%Y%m%d%H%M%S")))


#TODO
__all__ = [
    ]

#remoteCreds/gateCreds fields ['ip', 'ssh_port', 'username', 'password']

#tunneled_ssh_loop(socketPath, localPort, remoteCreds, commandStr, outputDir, errorLogDir): #TODO DBG

def main():
  args = get_args()
  try:
    # validate/create necessary file structure
    args = setup_outputDir(args)
    global _DBG
    _DBG = args.DEBUG  #TODO: temp - pass args to functions, check DEBUG from there? pass DEBUG?
    if _DBG: print("\n", args, "\n", sep="", file=sys.stderr) #TODO DBG
    #TODO: mkdir from dtg
    #TODO: store raw log
    #TODO: store json
    #TODO: mkdir for each ip (if scpFiles??)
    #TODO: store errors


    # unpack gateCreds from file
    gateIP, gatePort, gateUser, gatePW = next(load_csv(args.gateCreds))

    # open master ssh socket
    retval = ssh_socket_open_master(socketPath, gateIP, gatePort, gateUser, gatePW)
    # call script loop
    if args.bashScripts:
      commandStr = ingest_commands(args.bashScripts, args.formatters)
      remoteCreds = load_csv(args.remoteCreds)
      tunneled_ssh_loop(socketPath, args.localport, remoteCreds, commandStr,
          args.outputLog, args.errorLog)  #TODO: error log filepath
    # call file scp loop
    if args.scpFiles:
      scpFiles = load_csv(args.scpFiles) #TODO: may cause issues with iter instead of list
  except Exception as e:  #TODO: specify
    print("ERROR: {}".format(e), file=sys.stderr)
    if _DBG: #TODO DBG
      print("\n"); raise e
  finally:
    # close master ssh socket
    try:
      retval = ssh_socket_close_master(socketPath)
    except UnboundLocalError:
      pass
    except Exception as e:
      print("ERROR: {}".format(e), file=sys.stderr)
      if _DBG: #TODO DBG
        print("\n"); raise e


def setup_outputDir(args):
  # setup output directory
  if getattr(args, 'outputDir', None) is None:
    args.outputDir = defaultOutputDir
    # if 'output' dir has been deleted or moved, mkdir
    if not os.path.isdir(os.path.dirname(args.outputDir)):
      os.mkdir(os.path.dirname(args.outputDir))
    # check if 'output' dir is writeable
    if not os.access(os.path.dirname(args.outputDir), os.W_OK):  #TODO: specify exc
      raise Exception("'{}' is not a writeable directory".format(os.path.dirname(args.outputDir)))
    #create default outputDir
    if not os.path.exists(args.outputDir):
      os.mkdir(args.outputDir)
    #TODO: check if output files exist/W_OK??
    #TODO: add 'quiet' option
    print("Storing output at '{}'".format(args.outputDir), file=sys.stderr)

  if getattr(args, 'outputLog', None) is None:
    args.outputLog = os.path.join(args.outputDir, "ssh_output.txt")

  # set errorLog path (if not set already)
  if getattr(args, 'errorLog', None) is None:
    args.errorLog = os.path.join(args.outputDir, "error.log")
  # check if errorLog is writeable
  if not os.path.exists(args.errorLog):
    pass
  elif not os.access(args.errorLog, os.W_OK):  #TODO: specify exc
    raise Exception("'{}' is write restricted".format(args.errorLog))

  return args


def get_args():
  #TODO: how to allow multiple of a flag?
  #d = defaults.copy()
  #d.update(os.environ)
  #d.update(command_line_args)
  #ChainMap
  parser = ap.ArgumentParser()  #TODO: add desc
  # Hidden 'DEBUG' option, displays debug messages to terminal (stderr)
  parser.add_argument('--DEBUG', action='store_true', required=False, help=ap.SUPPRESS)
  parser.add_argument('-g', '--gateCreds', action=_readable_file, required=True)
  parser.add_argument('-r', '--remoteCreds', action=_readable_file, required=True)
  #TODO: required=False, default=defaultOutputDir
  #TODO create if default, else don't? (no default value if not, check if None, mkdir)
  parser.add_argument('-o', '--outputDir', action=_readable_dir, required=False,
      help="###output help - not required. default is timestamped subdirectory in ./user/output")
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
      raise ap.ArgumentError(self, "{} is not a valid path".format(values))
    if os.access(values, os.R_OK):
      setattr(namespace,self.dest,values)
    else:
      raise ap.ArgumentError(self, "{} is not a readable directory".format(values))


class _readable_file(ap.Action):
  def __call__(self, parser, namespace, values, option_string=None):
    if not os.path.isfile(values):
      raise ap.ArgumentError(self, "{} is not a valid file".format(values))
    if os.access(values, os.R_OK):
      setattr(namespace,self.dest,values)
    else:
      raise ap.ArgumentError(self, "{} is not a readable file".format(values))


def _DBG_readable_file(filepath):  #TODO DBG - remove
  if not os.path.isfile(filepath):
    print("DBG Readable File: '{}': file is invalid".format(filepath))
  if os.access(filepath, os.R_OK):
    print("DBG Readable File: '{}': file is valid".format(filepath))
  else:
    print("DBG Readable File: '{}': file isn't readable".format(filepath))


class _readable_file_append(ap.Action):
  '''
  @class: Takes value or values and appends to or creates list with key 'dest'
          - after validating provided file(s) are valid and readable.
  '''
  def __call__(self, parser, namespace, values, option_string=None):
    def _check_append(self, parser, namespace, values, option_string=None):
      if not os.path.isfile(values):
        raise ap.ArgumentError(self, "{} is not a valid file".format(values))
      if os.access(values, os.R_OK):
        # likely exception if 'dest' holds something other than a list
        items = _copy.copy(_ensure_value(namespace, self.dest, []))
        items.append(values)
        setattr(namespace, self.dest, items)
      else:
        raise ap.ArgumentError(self, "{} is not a readable file".format(values))
    if isinstance(values, list):
      for item in values:
        _check_append(self, parser, namespace, item, option_string=None)
    else:
      _check_append(self, parser, namespace, values, option_string=None)


def _ensure_value(namespace, name, value):
  if getattr(namespace, name, None) is None:
    setattr(namespace, name, value)
  return getattr(namespace, name)


def _ensure_dir(dirPath):  #TODO: remove?
  fullDirPath = os.realpath(dirPath)
  if not os.exists(fullDirPath):
    os.mkdir(fullDirPath)
  if not os.access(fullDirPath, os.W_OK):
    raise Exception("ERROR: restricted directory '{}'".format(dirPath))



def _store_key_pairs_factory(separator):
  class _store_key_pairs(ap.Action):
    '''
    @func: Takes key value pairs (separated by 'separator') and updates dict 'dest'
           note: If dest isn't a dictionary, its value will be replaced by a new dict
    '''
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


#TODO: include formatter instructions in docs

def _date_formatter(dateStr):
  #TODO: call _key_val_pair with keys and modified values. DON'T overwrite existing values.
  pass


class _update_dict_nargs(ap.Action):
  '''
  @func:
         note: If dest isn't a dictionary, its value will be replaced by a new dict
  '''
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
  if port >= 1 and port <= 65535:
    return int(port)
  else:
    raise ap.ArgumentTypeError("Invalid Port {}: out of range".format(port))


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
  commands = join_commands(commands)
  #try:
  if formatters is None:
    return commands
  else:
    return commands.format(**formatters)
  #except KeyError as e:


def join_commands(commandsLst):
  # comments must be on their own line or no subsequent commands will be run
  # skip commented (#) lines
  commands = [cmd for cmd in commandsLst if not cmd.startswith("#")]
  commands = ";".join(commands)
  # strip w/s around ';'
  commands = re.sub("\s*;\s*", ";", commands)
  # fix repeated ';' and trailing newline
  commands = re.sub(";+", ";", commands).strip(";").strip()
  return commands


def ssh_socket_open_master(socketPath, gateIP, gatePort, gateUser, gatePW):
  attemptLim = 5
  attempt = 1
  while attempt <= attemptLim and not ssh_socket_check_master(socketPath):
    print("Opening SSH Socket: attempt {}/{}".format(attempt, attemptLim), file=sys.stderr)
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
    attempt += 1

  # raise exception if fails to create socket
  if not ssh_socket_check_master(socketPath):
    #TODO: log error
    raise Exception("Failed to create multiplex socket. Check ssh settings and try again.")
    #TODO: specify exc?
  else:
    print("  ...done", file=sys.stderr)

  if _DBG:  #TODO DBG
    print("\nSocket STDOUT:\n", retval.stdout.decode('utf-8'), sep="", file=sys.stderr)
    print("\nSocket STDERR:\n", retval.stderr.decode('utf-8'), sep="", file=sys.stderr)
  return retval


def ssh_socket_check_master(socketPath):
  '''
  @func: determines if a socket at the given path is active
  @return: True if socket open, else False
  '''
  retval = sp.run(
      "ssh -S {} -O check towel@42".format(socketPath),
      shell=True,
      stdout=sp.PIPE,
      stderr=sp.PIPE
      )
  return True if retval.returncode == 0 else False


def ssh_socket_close_master(socketPath):
  attemptLim = 5
  attempt = 1
  while attempt <= attemptLim and ssh_socket_check_master(socketPath):
    print("Closing SSH Socket: attempt {}/{}".format(attempt, attemptLim), file=sys.stderr)
    retval = sp.run(
        # parameter after 'exit' is irrelevant, but something must be put in this slot
        "ssh -S {} -O exit towel@42".format(socketPath),
        shell=True,
        stdout=sp.PIPE,
        stderr=sp.PIPE
        )
    attempt += 1

  # raise exception if fails to close socket
  if ssh_socket_check_master(socketPath):
    #TODO: log error
    raise Exception("Failed to close multiplex ssh socket '{}'".format(socketPath))
    #TODO: specify exc?
  else:
    print("  ...done", file=sys.stderr)

  if _DBG:  #TODO DBG
    print("\nSocket STDOUT:\n", retval.stdout.decode('utf-8'), sep="", file=sys.stderr)
    print("\nSocket STDERR:\n", retval.stderr.decode('utf-8'), sep="", file=sys.stderr)
  return retval


# ssh command strings
_sshOptions = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
# parameter after forwarder settings is irrelevant, but something must be put in this slot
_sshSocketForwardFormatStr = "ssh -S {} -O {} {} -L localhost:{}:{}:{} towel@42 -fN"


def ssh_socket_forward(action, socketPath, localPort, remoteIP, remotePort):
  assert action in ["forward", "cancel"], \
      "ssh_socket_forward: action parameter must be in [\"forward\", \"cancel\"]"
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


def tunneled_ssh_loop(socketPath, localPort, remoteCreds, commandStr, outputLog, errorLog):
  #TODO: add jsonPath
  for remoteIP, remotePort, remoteUser, remotePW in remoteCreds:
    try:
      timestamp = time.ctime()
      retval = ssh_socket_forward("forward", socketPath, localPort, remoteIP, remotePort)
      if _DBG:  #TODO DBG
        print("\nForwarder STDERR:\n", retval.stderr.decode('utf-8'),
            sep="", file=sys.stderr)  #TODO DBG
      #TODO: check return, retry
      #else:
      #  raise Exception("DBG something DBG")
      #TODO: cut out extra params
      sshRetval = ssh_session(remoteUser, "localhost", localPort, remotePW, commandStr)
      #TODO: log data & errors (join ip, user, date, data)
      if _DBG:  #TODO DBG
        print("\nSession STDOUT:\n", "{}@{}\n".format(remoteUser, remoteIP),
            sshRetval.stdout.decode('utf-8'), sep="", file=sys.stderr)  #TODO DBG
        print("\nSession STDERR:\n", sshRetval.stderr.decode('utf-8'),
            sep="", file=sys.stderr)  #TODO DBG
      log_ssh_output(outputLog, remoteIP, remoteUser, timestamp,
          sshRetval.stdout.decode('utf-8'))
    except Exception as e:  #TODO: specify & define response
      log_error(errorLog, remoteIP, remoteUser, timestamp, e.__repr__())
      #TODO: e.__repr__ is clumsy, better solution needed
      #TODO: check retval for error logging
    finally:
      retval = ssh_socket_forward("cancel", socketPath, localPort, remoteIP, remotePort)


def ssh_session(user, ip, port, password, commandStr):
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
  return retval


def log_ssh_output(outputLog, ip, user, timestamp, data):
  #TODO: lock file if changed to threads
  writeStr = "\n".join(["### SSH SESSION HEADER ###", ip, user, timestamp, data, "\n\n"])
  with open(outputLog, 'a') as fp:
    written = fp.write(writeStr)
  return written


def log_error(errorLog, ip, user, timestamp, error):
  #TODO: lock file if changed to threads
  writeStr = "\n".join(["{} : {} : {}".format(timestamp, ip, user), error, "\n"])
  with open(errorLog, 'a') as fp:
    written = fp.write(writeStr)
  return written


def tunneled_scp_loop(socketPath, localPort, remoteCreds, fileLst, outputDir, errorLogDir):
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


def log_session_data_text(ip, user, data, timestamp, logfilePath):
  with open(logfilePath, 'a') as fp:
    pass


def log_session_data_json():
  pass


if __name__ == "__main__":
  main()
