from plait.api import run, sudo, RemoteCallError
from plait.task import task

def touch(file='/tmp/touch'):
    run("touch {}".format(file))

def uname(flag="a"):
    print "Kernel info:"
    sudo("uname -" + flag)

def disk_space(filter=""):
    run("df -h | sed '1 d' | grep ^/dev")

def listdir(path, long=False, all=False):
    cmd = "ls "
    if long or all:
        cmd += "-"
    if long: cmd += "l"
    if all: cmd += "a"
    run("{} {}".format(cmd, path))

def dockerps(all=False):
    cmd = "docker ps"
    if all:
        cmd += " -a"
    run(cmd)
