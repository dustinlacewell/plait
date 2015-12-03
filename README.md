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

Let's run our Plait Task against the server. In these examples we'll be using the details of the `fake_server` **as described in the section above** regarding Docker. If you're using your own server make sure to use the **correct username, hostname and port information**:


    $ plait -h root@0.0.0.0:49154 uname

    ✓  root@0.0.0.0:32768
    ↳  uname
    Linux 26d61d0e567f 3.13.0-65-generic #106-Ubuntu SMP Fri Oct 2 22:08:27 UTC 2015 x86_64 x86_64 x86_64 GNU/Linux


Once Plait is finished executing the task, it will print a "host header" indicating whether the Task was a success, whether the Task failed or if there was a connection problem. If there was no connection problem, then each Task is listed followed by its output. Here we can see the output of running `uname` on the remote server.

## Tasks

Tasks are just normal Python functions. They are able to call other Python functions or other Tasks. Tasks may utilize `print` to emit output or can return values. Returned values will be added to the end of the Task's output. For example, changing the `plaitfile.py` to use `return` instead of `print` produces the same report:

    from plait.api import run

    def uname():
        return run('uname -a')

Then running it:

    $ plait -h root@0.0.0.0:49154 uname

    ✓  root@0.0.0.0:32768
    ↳  uname
    Linux 26d61d0e567f 3.13.0-65-generic #106-Ubuntu SMP Fri Oct 2 22:08:27 UTC 2015 x86_64 x86_64 x86_64 GNU/Linux

## Multiple Tasks

Let's add another task to our `plaitfile.py`:

    from plait.api import run

    def uname():
        return run('uname -a')

    def disk_space():
        return run('df -h')

Plait allows for calling multiple Tasks, sequentially. Each Task output is listed:

    plait -h root@0.0.0.0:32768 uname disk_space
    ✓ root@0.0.0.0:32768
    ↳ uname
    Linux 26d61d0e567f 3.13.0-65-generic #106-Ubuntu SMP Fri Oct 2 22:08:27 UTC 2015 x86_64 x86_64 x86_64 GNU/Linux
    ↳ disk_space
    Filesystem                                              Size  Used Avail Use% Mounted on
    rootfs                                                  216G  108G   98G  53% /
    none                                                    216G  108G   98G  53% /
    tmpfs                                                   3.9G     0  3.9G   0% /dev
    shm                                                      64M     0   64M   0% /dev/shm
    tmpfs                                                   3.9G     0  3.9G   0% /sys/fs/cgroup
    /dev/disk/by-uuid/3be76936-38f6-45fb-89a9-451186428331  216G  108G   98G  53% /etc/hosts
    tmpfs                                                   3.9G     0  3.9G   0% /proc/kcore
    tmpfs                                                   3.9G     0  3.9G   0% /proc/latency_stats
    tmpfs                                                   3.9G     0  3.9G   0% /proc/timer_stats

## Task Arguments

Tasks can also take arguments which can be passed in on the commandline. Let's adjust the `disk_space` Task to filter for specific filesystems:

    from plait.api import run

    def uname():
        return run('uname -a')

    def disk_space(*args):
        return run('df -h {}'.format(' '.join(args)))

This new `disk_space` Task now takes any number of arguments. Those arguments are now interpolated into the eventual `df -h` shell command ran on the remote host. We can pass these arguments to the Task on the commandline by following the Task name with a colon `:` and separating each argument with a comma `,`:

    plait -h root@0.0.0.0:32768 disk_space:/,/etc/hosts
    ✓ root@0.0.0.0:32768
    ↳ disk_space / /etc/hosts
    Filesystem                                              Size  Used Avail Use% Mounted on
    none                                                    216G  108G   98G  53% /
    /dev/disk/by-uuid/3be76936-38f6-45fb-89a9-451186428331  216G  108G   98G  53% /etc/hosts

## Task Warnings

Any Tasks that result in an exception will appear differently than successful ones. Let's create a Task for demonstration purposes

    def fail():
        raise Exception("This is a test exception!")

If we call this Task we see that the output changes slightly. You can't see it here, but Task warnings will be output in yellow:

    plait -h root@0.0.0.0:32768 fail
    ✗ root@0.0.0.0:32768
    ↳ fail
    This is a test exception!

If multiple tasks are passed, any exceptional Task will mark the whole Host with as warning, and no subsequent Tasks will be executed:

    plait -h root@0.0.0.0:32768 fail uname
    ✗ root@0.0.0.0:32768
    ↳ fail
    This is a test exception!


# Multiple Servers

Plait supports executing Tasks on multiple hosts in parallel and does so fairly efficiently. To execute tasks on multiple hosts you can pass additional `-h` flags. Let's create another SSHd server container:

    $ docker run -d -P --name fake_server2 rastasheep/ubuntu-ssh

As before we need to discover the port that Docker assigned for the container so that we can connect to it:

    $ docker port fake_server2 22
    0.0.0.0:32769

**Remember**: install your keypair so you are not prompted for a password!

Now we can execute tasks on multiple hosts:

    plait -h root@0.0.0.0:32768 -h root@0.0.0.0:32769 uname
    ✓ root@0.0.0.0:32768
    ↳  uname
    Linux 26d61d0e567f 3.13.0-65-generic #106-Ubuntu SMP Fri Oct 2 22:08:27 UTC 2015 x86_64 x86_64 x86_64 GNU/Linux

    ✓ root@0.0.0.0:32769
    ↳  uname
    Linux 07ae69833024 3.13.0-65-generic #106-Ubuntu SMP Fri Oct 2 22:08:27 UTC 2015 x86_64 x86_64 x86_64 GNU/Linux

## Piping hosts

If you have many hosts it may be inconvenient to pass them all as `-h` flags. Another option is to store the host strings inside of a file and pipe them into Plait. Let's create a file `/tmp/hosts.txt` with the following content:

    root@0.0.0.0:32768
    root@0.0.0.0:32769

Now we can perform the same multi-host operations with a pipe:

    cat /tmp/hosts.txt | plait uname
    ✓ root@0.0.0.0:32768
    ↳  uname
    Linux 26d61d0e567f 3.13.0-65-generic #106-Ubuntu SMP Fri Oct 2 22:08:27 UTC 2015 x86_64 x86_64 x86_64 GNU/Linux

    ✓ root@0.0.0.0:32769
    ↳  uname
    Linux 07ae69833024 3.13.0-65-generic #106-Ubuntu SMP Fri Oct 2 22:08:27 UTC 2015 x86_64 x86_64 x86_64 GNU/Linux

## Connection Failures

If Plait is not able to connect or authenticate with the remote host for any reason the host will render in red with lightning-bold glyph:

   plait -h root@nosuchhost uname
   ⚡ root@nosuchhost
   DNS lookup failed: address 'nosuchhost' not found: [Errno -2] Name or service not known.

# Reporting

One of the advantages of Plait over similar tools is its functionality related to Task result reporting. You have already seen some of the ways that Plait makes it very easy to visually identify what Tasks succeeded, which failed and which were unable to connect. The following are the ways in which a Task can complete:

  * **Failure** - Plait was unable to connect to the remote host to perform any work
  * **Warning** - A Task raised an exception while running
  * **Empty** - A Task finished without error but produced no output
  * **Success** - A Task finished without error and produced output

## Summary Report

By passing the `-R` flag, Plait will print a Summary Report of how many of each exit condition was experienced:

    plait -R -h root@0.0.0.0:32768 -h root@0.0.0.0:32769 -h root@nosuchhost uname
    ⚡  root@nosuchhost
    DNS lookup failed: address 'nosuchhost' not found: [Errno -2] Name or service not known.

    ✓  root@0.0.0.0:32768
    ↳ uname
    Linux 26d61d0e567f 3.13.0-65-generic #106-Ubuntu SMP Fri Oct 2 22:08:27 UTC 2015 x86_64 x86_64 x86_64 GNU/Linux

    ✓  root@0.0.0.0:32769
    ↳ uname
    Linux 07ae69833024 3.13.0-65-generic #106-Ubuntu SMP Fri Oct 2 22:08:27 UTC 2015 x86_64 x86_64 x86_64 GNU/Linux

    Plait results:
    ↳  ✓ 2/0/2, ✗ 0, ⚡ 1

The first grouping of numbers after the `✓` indicate `success`/`empty`/`total successes`.

The second and third groups show `warnings` and `failures` respectively.

## Failures and Warnings

If you interested in the hosts that are unreachable or otherwise did not complete succesfully, you can pass the `-e` flag which will **only show failures and warnings**.

If you do not want to see warnings or failures you can pass `-E`.

## Empties

Plait maintains a concept of the "empty success" wherin a Task does not raise an exception but does not produce any output either. This is useful for calling Tasks on the commandline which are usually called from other Tasks and expected to return data or return None.

If you are only interested in Tasks that produced output you can pass the `-S` flag.

## Grepping

If there Tasks with specific output that interest you, you can pass the `-g $PATTERN` flag which will only show Tasks who's output matches the provided regular expression.

If there are Tasks with specific output that you wish to hide you can pass the `-G $PATTERN` flag.

# Controlling Concurrency

By default Plait will attempt to execute Tasks across all hosts concurrently. However, if there are many hosts Plait may experience large amounts of "contention". Contention can slow down individual tasks. If the contention is bad enough, Plait's connections will timeout. In order to reduce the amount of concurrency you can pass the `-s $NUM` flag which will control how many hosts to process at any given time.

The timeout for connections is set to 10 seconds by default. You can change this default with the `-t $SECONDS` flag.

Plait will attempt to connect to a host 2 times by default. You can change this default with the `-r $RETRIES` flag.
