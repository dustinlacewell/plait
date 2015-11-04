import getpass
from functools import partial

from twisted.conch.client.knownhosts import ConsoleUI
from twisted.internet.defer import succeed, Deferred
from twisted.internet import reactor, defer

from plait.errors import TimeoutError

def clean_utf8(data):
    return data.decode('utf8', 'replace').encode('utf8')

class QuietConsoleUI(ConsoleUI):

    def __init__(self, *args, **kwargs):
        pass

    def warn(self, text): pass

    def prompt(self, text):
        return succeed(True)

class CFTResult(object):
    def __init__(self, stdout, stderr=""):
        self.stdout = stdout
        self.stderr = stderr

    @property
    def output(self):
        return self.stdout + self.stderr

def parse_host_string(host_string):
    if '@' in host_string:
        user, host_string = host_string.split('@', 1)
    else:
        user = getpass.getuser()

    if ':' in host_string:
        host, port = host_string.split(':', 1)
    else:
        host = host_string
        port = 22
    return user.encode('utf8'), host.encode('utf8'), port

def _escape_split(sep, argstr):
    """
    Allows for escaping of the separator: e.g. task:arg='foo\, bar'

    It should be noted that the way bash et. al. do command line parsing, those
    single quotes are required.

    (copied from fabric/main.py)
    """
    escaped_sep = r'\%s' % sep

    if escaped_sep not in argstr:
        return argstr.split(sep)

    before, _, after = argstr.partition(escaped_sep)
    startlist = before.split(sep)  # a regular split is fine here
    unfinished = startlist[-1]
    startlist = startlist[:-1]

    # recurse because there may be more escaped separators
    endlist = _escape_split(sep, after)

    # finish building the escaped value. we use endlist[0] becaue the first
    # part of the string sent in recursion is the rest of the escaped value.
    unfinished += sep + endlist[0]

    return startlist + [unfinished] + endlist[1:]  # put together all the parts

def parse_task_calls(calls):
    """
    Parse string list into list of tuples: task_name, args, kwargs

    (modified from fabric/main.py)
    """
    parsed_calls = []
    for call in calls:
        args = []
        kwargs = {}
        if ':' in call:
            call, argstr = call.split(':', 1)
            for pair in _escape_split(',', argstr):
                result = _escape_split('=', pair)
                if len(result) > 1:
                    k, v = result
                    kwargs[k] = v
                else:
                    args.append(result[0])
        parsed_calls.append((call, args, kwargs))
    return parsed_calls

def timeout(t, original):

    d = defer.Deferred()
    d._suppressAlreadyCalled = True

    def late():
        if not original.called:
            original.cancel()
            msg = "Operation failed to finish within {} seconds.".format(t)
            d.errback(TimeoutError(msg))

    def errback(failure):
        if not timeout.called:
            timeout.cancel()
            original.cancel()
        d.errback(failure)

    def callback(value):
        if not timeout.called:
            timeout.cancel()
        d.callback(value)

    original.addCallbacks(callback, errback)
    timeout = reactor.callLater(t, late)

    return d

def retry(times, func, *args, **kwargs):
    """retry a defer function

    @param times: how many times to retry
    @param func: defer function
    """
    errorList = []
    deferred = Deferred()

    def run():
        # run target function
        d = func(*args, **kwargs)
        # call outgoing deferred or errback
        d.addCallbacks(deferred.callback, error)

    def error(error):
        # add new error to list
        errorList.append(error)
        # retry if under quota
        if len(errorList) < times:
            run()
        # otherwise errback outgoing deferred
        else:
            deferred.errback(errorList[-1])
    run()
    return deferred

