class PlaitError(Exception): pass

class StartupError(PlaitError): pass

class NoSuchTaskError(StartupError): pass

