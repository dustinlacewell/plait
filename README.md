# plait

Plait is a command-line utility for executing tasks across one or more remote hosts over SSH. Using Python, Tasks are able to generate shell-code and which is executed against the host, the results of which are then made available to the Task. Task results are aggregated and Plait offers a number of features reporting and filtering of those results.

# Installation

Plait may be installed via **pip**:

    $ pip install plait

Or you may clone the **development version**:

    $ git clone https://github.com/dustinlacewell/plait.git
    $ cd plait
    $ python setup.py install

The Plait command should now be available:

    $ plait --help
    Usage: plait [OPTIONS] [TASKS]...

      * can be supplied multiple times

    Options:
      -h, --host *        [$USER@]hostname[:22]
      -H, --hostfile      Read hosts from a line delimited file
      -p, --plaitfile     Read tasks from specified file
      -I, --interactive   Display results graphically
      -A, --all-tasks     Tasks with no output result in a warning
      -R, --report        Print summary report
      -q, --quiet         Hide hosts that produce no result
      -Q, --quiet-report  Only print summary report (implies -R)
      -e, --errors        Only show sessions with an error
      -E, --hide-errors   Hide sessions with an error
      -g, --grep          Only display sessions matching a pattern
      -G, --hide-grep     Hide sessions matching a pattern
      -s, --scale         Number of hosts to execute in parallel
      -r, --retries       Times to retry SSH connection
      -t, --timeout       Seconds to wait for SSH
      -i, --identity *    Public key to use
      -a, --agent         Whether to use system ssh-agent for auth
      -k, --knownhosts    File with authorized hosts
      -l, --logging       Show twisted logging
      --help              Show this message and exit.

# Remote Servers

In order to use Plait usefully you'll need access to a **remote SSH server**. However, Plait only supports **password-less login**. This means you'll need a public and private key-pair registered with the remote server so that you are not prompted for a password when logging in. Test that you are able to login to your server without a password:

    $ ssh -o PasswordAuthentication=no username@host

If you are prompted for a password, please **setup public-key authentication** before continuing.

## Using Docker

If you have [Docker](https://www.docker.com/) installed you can spin up a container that is running an SSH server so that you can test with a throw-away environment. For this we'll use the `rastasheep/ubuntu-sshd` image which provides a simple SSHd configuration over the official Ubuntu image:

    $ docker run -d -P --name fake_server rastasheep/ubuntu-sshd

Docker will pull down the image and start the container. Docker will expose the internal SSH port (22) to some **random port on your host**. Run the following command to list it. Note, **your port may be different**:

    $ docker port fake_server 22
    0.0.0.0:49154

Now we can install our public key into the `fake_server` so that we are not prompted for a password when logging in with Plait. The username and password **are both** `root`:

    $ ssh-copy-id -p 49154 root@0.0.0.0

You should now be able to login to the `fake_server` **as root** without a password:

    $ ssh -o PasswordAuthentication=no -p 49154 root@host

# Tasks and the Plaitfile

Plait's job is to execute Tasks. Those Tasks are written by you to perform the work you want to execute on remote hosts. Those Tasks are contained within a file called `plaitfile.py`. Plait will look for this file in the directory where it is invoked - otherwise **you can specify the Plaitfile to use** with the `-p` flag.

Let's create a simple `plaitfile.py` with the following content:

    from plait.api import run

    def uname():
        print run('uname -a')

This is a simple Plaitfile but let's break it down anyway. There is only one import `plait.api.run`. This function accepts a string containing shell-code and executes it on the remote host. The output of the remote command is **returned as a string**.

A single Task `uname` is defined and it uses `run` to execute `uname -a` on the remote server. It prints out the result and then returns. `uname` is a unix command for listing information about the kernel version and other host details.

Let's run plait against our server. In these examples we'll be using the details of the `fake_server` **as described in the section above** regarding Docker. If you're using your own server make sure to use the correct username, hostname and port information:


    $ plait -h root@0.0.0.0:49154 uname

    ✓  root@0.0.0.0:32768
    ↳  uname
    Linux 26d61d0e567f 3.13.0-65-generic #106-Ubuntu SMP Fri Oct 2 22:08:27 UTC 2015 x86_64 x86_64 x86_64 GNU/Linux


Once Plait is finished executing the task, it will print a "host header" indicating whether the Task was a success, whether the Task failed or if there was a connection problem. If there was no connection problem, then each Task is listed followed by its output. Here we can see the output of running `uname` on the remote server.
