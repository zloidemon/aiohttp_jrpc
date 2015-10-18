""" Exceptions """


class Error(Exception):
    """Generic error class."""


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
