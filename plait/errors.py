class PlaitError(Exception): pass

class StartupError(PlaitError): pass

class NoSuchTaskError(StartupError): pass

class TaskError(PlaitError): pass

class TimeoutError(PlaitError): pass

