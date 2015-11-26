
import os, imp, getpass, sys, traceback, re

from twisted.python.filepath import FilePath
from twisted.internet.task import react
from twisted.internet import reactor
from twisted.internet.endpoints import UNIXClientEndpoint
from twisted.conch.ssh.keys import EncryptedKeyError, Key
from twisted.conch.client.knownhosts import KnownHostsFile
from twisted.python import log as logger

import click

from structlog import PrintLogger
log = PrintLogger()

from plait.app.console import ConsoleApp
from plait.app.terminal import TerminalApp
from plait.runner import PlaitRunner
from plait.task import NoSuchTaskError, task
from plait.errors import *
from plait.utils import parse_task_calls, Bag

def findPlaitfile(path=os.getcwd()):
    files = os.listdir(path)
    parent = os.path.dirname(path)
    if 'plaitfile.py' in files:
        fullpath = os.path.join(path, 'plaitfile.py')
        return os.path.abspath(fullpath)
    elif parent != path:
        return findPlaitfile(parent)
    raise StartupError("Couldn't find plaitfile.py")

def importPlaitfile(filename):
    try:
        err = None
        return imp.load_source('plaitfile', filename)
    except Exception as e:
        e = StartupError("Couldn't import plaitfile")
        e.tb = traceback.format_exc()
        raise e

def gatherTasks(tasks, pf_module):
    parsed_tasks = parse_task_calls(tasks)
    for task_name, args, kwargs in parsed_tasks:
        task_func = getattr(pf_module, task_name, None)
        if not task_func:
            error = "Task `{}` does not exist in pf_module: {}"
            error = error.format(task_name, pf_module.__file__)
            raise NoSuchTaskError(error)
        task_func = task(task_func)
        yield task_name, task_func, args, kwargs

def getTasks(tasks, plaitfile, **kwargs):
    if not tasks:
        raise StartupError("Must specify at least one task to execute.")

    pf_module = importPlaitfile(plaitfile or findPlaitfile())
    return list(gatherTasks(tasks, pf_module))

def setupLogging(logging, **kwargs):
    if logging:
        logger.startLogging(sys.stdout, setStdout=1)

def readKey(path):
    try:
        return Key.fromFile(path)
    except EncryptedKeyError:
        passphrase = getpass.getpass("%r keyphrase: " % (path,))
        return Key.fromFile(path, passphrase=passphrase)

def getKeys(identity, **kwargs):
    key_path = os.path.expanduser(identity)
    if os.path.exists(key_path):
        return [readKey(key_path)]

def getKnownHosts(knownhosts, **kwargs):
    known_hosts_path = FilePath(os.path.expanduser(knownhosts))
    if known_hosts_path.exists():
        return KnownHostsFile.fromPath(known_hosts_path)

def getAgentEndpoint(agent, **kwargs):
    if "SSH_AUTH_SOCK" in os.environ and agent:
        auth_socket = os.environ["SSH_AUTH_SOCK"]
        return UNIXClientEndpoint(reactor, auth_socket)

def getHosts(host, hostfile, **kwargs):
    hosts = list(host)
    if hostfile:
        with open(hostfile, 'r') as fobj:
            hosts += tuple(l.strip() for l in fobj.readlines())
    if not sys.stdin.isatty():
        hosts += tuple(l.strip() for l in sys.stdin.readlines())
    if not len(hosts):
        raise StartupError("Must specify at least one host.")
    return hosts

def getErrorFilter(errors, hide_errors, **kwargs):
    if errors and hide_errors:
        msg = "`-e` and `-E` cannot be used simultaneously."
        raise StartupError(msg)
    elif errors:
        # only show errors
        return True
    elif hide_errors:
        # don't show errors
        return False
    else:
        # show all sessions
        return None

def getGrepFilter(grep, hide_grep, **kwargs):
    if grep and hide_grep:
        msg = "`-g` and `-G` cannot be used simultaneously."
        raise StartupError(msg)
    elif grep:
        return lambda x: re.search(grep, x)
    elif hide_grep:
        return lambda x: re.search(hide_grep, x) is None
    else:
        return lambda x: re.search(".*", x)

def getConnectSettings(scale, retries, timeout, **kwargs):
    return Bag(scale=scale,
               retries=retries,
               timeout=timeout,
               keys = getKeys(**kwargs),
               known_hosts = getKnownHosts(**kwargs),
               agent_endpoint = getAgentEndpoint(**kwargs))

@click.command()
@click.argument('tasks', nargs=-1)
@click.option('--interactive', '-I',
              is_flag=True,
              help="Display results graphically")
@click.option('--plaitfile', '-p',
              default=None, metavar='',
              help="Read tasks from specified file")
@click.option('--host', '-h',
              multiple=True, metavar='*',
              help="[$USER@]hostname[:22]")
@click.option('--hostfile', '-H',
              default=False, metavar='',
              help="Read hosts from a line delimited file")
@click.option('--scale', '-s',
              default=0, metavar='',
              help="Number of hosts to execute in parallel")
@click.option('--errors', '-e',
              is_flag=True, metavar='',
              help="Only show sessions with an error")
@click.option('--hide-errors', '-E',
              is_flag=True, metavar='',
              help="Hide sessions with an error")
@click.option('--grep', '-g',
              default=None, metavar='',
              help="Only display sessions matching a pattern")
@click.option('--hide-grep', '-G',
              default=None, metavar='',
              help="Hide sessions matching a pattern")
@click.option('--identity', '-i',
              default="~/.ssh/id_rsa", metavar="*",
              help="Public key to use")
@click.option('--agent', '-a',
              is_flag=True,
              help="Whether to use system ssh-agent for auth")
@click.option('--knownhosts', '-k',
              default="~/.ssh/known_hosts", metavar='',
              help="File with authorized hosts")
@click.option('--retries', '-r',
              default=1, metavar='',
              help="Times to retry SSH connection")
@click.option('--timeout', '-t',
              default=10, metavar='',
              help="Seconds to wait for SSH")
@click.option('--logging', '-l',
              is_flag=True,
              help="Show twisted logging")
def run(tasks, interactive, **kwargs):
    """
    * can be supplied multiple times
    """
    setupLogging(**kwargs)

    tasks = getTasks(tasks, **kwargs)
    hosts = getHosts(**kwargs)
    connect_settings = getConnectSettings(**kwargs)
    runner = PlaitRunner(hosts, tasks, connect_settings)

    errorFilter = getErrorFilter(**kwargs)
    grepFilter = getGrepFilter(**kwargs)

    if interactive:
        console = ConsoleApp(title="plait 1.0")
    else:
        console = TerminalApp(errorFilter, grepFilter)

    console.run(runner)
def main():
    try:
        run()
    except StartupError as e:
        log.error(" * " + e.message)
        if hasattr(e, 'tb'):
            log.error(e.tb)
