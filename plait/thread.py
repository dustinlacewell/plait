from twisted.internet import reactor
from twisted.python import failure
from twisted.internet import defer
from threading import Thread

def deferToDaemonThread(f, *args, **kw):
    """Run function in thread and return result as Deferred."""

    def putResultInDeferred(d, f, args, kw):
        """Run a function and give results to a Deferred."""
        try:
            result = f(*args, **kw)
        except:
            f = failure.Failure()
            reactor.callFromThread(d.errback, f)
        else:
            reactor.callFromThread(d.callback, result)

    d = defer.Deferred()
    thread = Thread(target=putResultInDeferred,
                    args=(d, f, args, kw))
    thread.setDaemon(1)
    thread.start()
    d.thread = thread
    return d
