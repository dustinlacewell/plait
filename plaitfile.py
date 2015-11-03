from plait.api import run, sudo, RemoteCallError
from plait.task import task

def uname(flag="a"):
    sudo("uname -" + flag)

def disk_space(filter=""):
    run("df -h | sed '1 d' | tr -s ' ' | cut -d ' ' -f 1,5 | grep /dev")

def listdir(path, long=False, all=False):
    cmd = "ls "
    if long or all:
        cmd += "-"
    if long: cmd += "l"
    if all: cmd += "a"
    run("{} {}".format(cmd, path))

def randomtail():
    run("cat /dev/urandom")

def dockerps(all=False):
    cmd = "docker ps"
    if all:
        cmd += " -a"
    run(cmd)

def workerlogs(tail=False):
    run("docker logs " + ("-f" if tail else "") + " worker")

def dockerlogs(tail=False):
    run("tail " + ("-f" if tail else "") + " /var/log/upstart/docker.log")

def deploy():
    ls("/")
    dockerps()

