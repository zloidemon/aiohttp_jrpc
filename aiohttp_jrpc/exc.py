""" Exceptions """


class Error(Exception):
    """Generic error class."""
    def __init__(self, msg):
        Exception.__init__(self, msg)


class ParseError(Error):
    """
    Invalid JSON was received by the server.
    An error occurred on the server while parsing the JSON text.
    """


class InvalidRequest(Error):
    """
    The JSON sent is not a valid Request object.
    """


class InvalidParams(Error):
    """
    Invalid method parameter(s).
    """


class InternalError(Error):
    """
    Reserved for implementation-defined server-errors.
    """


class InvalidResponse(Error):
    """
    The JSON sent is not a valid Response object.
    """
