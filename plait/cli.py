
import os, imp, getpass, sys, traceback

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

from plait.runner import PlaitRunner
from plait.viewer import create_loop, Viewer
from plait.task import NoSuchTaskError, task
from plait.errors import *
from plait.utils import parse_task_calls

def echo_host_count(nhosts):
    if nhosts >= 2:
        post = "{} hosts".format(nhosts)
    elif nhosts:
        post = "1 host"
    else:
        raise StartupError("No hosts specified")
    log.info("Executing on {}".format(post))

def readKey(path):
    try:
        return Key.fromFile(path)
    except EncryptedKeyError:
        passphrase = getpass.getpass("%r keyphrase: " % (path,))
        return Key.fromFile(path, passphrase=passphrase)

def getKeys(identity):
    key_path = os.path.expanduser(identity)
    if os.path.exists(key_path):
        return [readKey(key_path)]

def find_plaitfile(path=os.getcwd()):
    files = os.listdir(path)
    parent = os.path.dirname(path)
    if 'plaitfile.py' in files:
        fullpath = os.path.join(path, 'plaitfile.py')
        return os.path.abspath(fullpath)
    elif parent != path:
        return find_plaitfile(parent)
    raise StartupError("Couldn't find plaitfile.py")

def getKnownHosts(knownhosts):
    known_hosts_path = FilePath(os.path.expanduser(knownhosts))
    if known_hosts_path.exists():
        return KnownHostsFile.fromPath(known_hosts_path)

def getAgentEndpoint(use_agent):
    if "SSH_AUTH_SOCK" in os.environ and use_agent:
        auth_socket = os.environ["SSH_AUTH_SOCK"]
        return UNIXClientEndpoint(reactor, auth_socket)

def import_plaitfile(filename):
    try:
        err = None
        return imp.load_source('plaitfile', filename)
    except Exception as e:
        e = StartupError("Couldn't import plaitfile")
        e.tb = traceback.format_exc()
        raise e

def gather_tasks(plaitfile, task_specs):
    parsed_tasks = parse_task_calls(task_specs)
    task_calls = []
    for task_name, args, kwargs in parsed_tasks:
        task_func = getattr(plaitfile, task_name, None)
        if not task_func:
            error = "Task `{}` does not exist in plaitfile: {}"
            error = error.format(task_name, plaitfile.__file__)
            raise NoSuchTaskError(error)
        task_func = task(task_func)
        task_calls.append((task_name, task_func, args, kwargs))
    return task_calls

@click.command()
@click.option('--host', '-h', multiple=True, help="[$USER@]hostname[:22]", metavar='*')
@click.option('--scale', '-s', default=0, help="Number of hosts to execute in parallel", metavar='')
@click.option('--identity', '-i', default="~/.ssh/id_rsa", help="Public key to use", metavar="*")
@click.option('--agent', '-a', is_flag=True, help="Whether to use system ssh-agent for auth")
@click.option('--knownhosts', '-k', default="~/.ssh/known_hosts", metavar='', help="File with authorized hosts")
@click.option('--retries', '-r', default=10, help="Times to retry SSH connection", metavar='')
@click.option('--timeout', '-t', default=3, help="Seconds to wait for SSH", metavar='')
@click.option('--logging', '-l', is_flag=True, help="Show twisted logging")
@click.argument('tasks', nargs=-1)
def run(host, scale, identity, agent, knownhosts, retries, timeout, logging, tasks):
    """
    * can be supplied multiple times
    """
    if not tasks:
        raise StartupError("Must specify at least one task to execute.")
    if logging:
        logger.startLogging(sys.stdout, setStdout=1)
    echo_host_count(len(host))

    viewer = Viewer(host)

    keys = getKeys(identity)
    known_hosts = getKnownHosts(knownhosts)
    agent = getAgentEndpoint(agent)
    plaitfile = import_plaitfile(find_plaitfile())
    task_calls = gather_tasks(plaitfile, tasks)
    runner = PlaitRunner(viewer, host, task_calls, scale=scale,
                         retries=retries, timeout=timeout,
                         keys=keys, agent=agent,
                         known_hosts=known_hosts)
    runner.run()
    loop = create_loop(viewer)
    loop.run()

def main():
    try:
        run()
    except StartupError as e:
        log.error(" * " + e.message)
        if hasattr(e, 'tb'):
            log.error(e.tb)
