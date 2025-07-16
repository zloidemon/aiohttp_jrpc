""" Error responses """
from aiohttp.web import Response
from enum import Enum, unique
import json


@unique
class ErrorCode(Enum):
    INTERNAL_ERROR = (-32603, 'Internal error')
    INVALID_PARAMS = (-32602, 'Invalid params')
    INVALID_REQUEST = (-32600, 'Invalid Request')
    METHOD_NOT_FOUND = (-32601, 'Method not found')
    PARSE_ERROR = (-32700, 'Parse error')
    SERVER_ERROR = (None, 'Server error')


class JResponse(Response):
    """ Modified Reponse from aohttp """
    def __init__(self, *, status=200, reason=None,
                 headers=None, jsonrpc=None):
        if jsonrpc is not None:
            jsonrpc.update({'jsonrpc': '2.0'})
            text = json.dumps(jsonrpc)
        super().__init__(status=status, reason=reason, text=text,
                         headers=headers, content_type='application/json')


def message(error):
    def decorator(func):
        def wrapper(*args, **kwargs):
            return func(*args, error.value, **kwargs)
        return wrapper
    return decorator


class JError:
    """ Class with standart errors """
    def __init__(self, data=None, rid=None):
        if data is not None:
            self.rid = data['id']
        else:
            self.rid = rid

    def __response(self, error, exc=None):
        """ base response """
        code, message = error

        if exc is not None:
            message += ': %s' % str(exc)

        return JResponse(jsonrpc={
            'id': self.rid,
            'error': {
                'code': code,
                'message': message,
            },
        })

    @message(ErrorCode.PARSE_ERROR)
    def parse(self, error, exc=None):
        """ json parsing error """
        return self.__response(error, exc)

    @message(ErrorCode.INVALID_REQUEST)
    def request(self, error, exc=None):
        """ incorrect json rpc request """
        return self.__response(error, exc)

    @message(ErrorCode.METHOD_NOT_FOUND)
    def method(self, error, exc=None):
        """ Not found method on the server """
        return self.__response(error, exc)

    @message(ErrorCode.INVALID_PARAMS)
    def params(self, error, exc=None):
        """ Incorrect params (used in validate) """
        return self.__response(error, exc)

    @message(ErrorCode.INTERNAL_ERROR)
    def internal(self, error, exc=None):
        """ Internal server error, actually send on every unknow exception """
        return self.__response(error, exc)

    def custom(self, code, message):
        """
        The error codes from and including -32768 to -32000
        are reserved for pre-defined errors.

        Specific server side errors use: -32000 to -32099
        reserved for implementation-defined server-errors
        """
        _err_max = -32000
        _err_min = -32099
        _err_reserved = -32768

        if code >= _err_min and code <= _err_max:
            _, message = ErrorCode.SERVER_ERROR.value
        elif code >= _err_reserved and code <= _err_max:
            return self.internal()

        return self.__response((code, message,))
