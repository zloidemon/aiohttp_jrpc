from aiohttp_jrpc import Service, JError
from aiohttp.web import middleware


PARSE_ERROR = {
    'jsonrpc': '2.0', 'id': None,
    'error': {'code': -32700, 'message': 'Parse error'}
}
INVALID_REQUEST = {
    'jsonrpc': '2.0', 'id': None,
    'error': {'code': -32600, 'message': 'Invalid Request'}
}
NOT_FOUND = {
    'jsonrpc': '2.0', 'id': None,
    'error': {'code': -32601, 'message': 'Method not found'}
}
INVALID_PARAMS = {
    'jsonrpc': '2.0', 'id': None,
    'error': {'code': -32602, 'message': 'Invalid params'}
}
INTERNAL_ERROR = {
    'jsonrpc': '2.0', 'id': None,
    'error': {'code': -32603, 'message': 'Internal error'}
}
SERVER_ERROR = {
    'jsonrpc': '2.0', 'id': None,
    'error': {'code': -32000, 'message': 'Server error'}
}
CUSTOM_ERROR_GT = {
    'jsonrpc': '2.0', 'id': None,
    'error': {'code': -31999, 'message': 'Custom error gt'}
}
CUSTOM_ERROR_LT = {
    'jsonrpc': '2.0', 'id': None,
    'error': {'code': -32769, 'message': 'Custom error lt'}
}
REQ_SCHEM = {
    "type": "object",
    "properties": {
        "data": {"type": "string"},
    }
}


@middleware
async def custom_errorhandler_middleware(request, handler):
    try:
        return (await handler(request))
    except AttributeError:
        return JError().custom(-31999, 'Custom error gt')
    except LookupError:
        return JError().custom(-32769, 'Custom error lt')
    except NameError:
        return JError().custom(-32768, 'Bad code')
    except Exception:
        return JError().custom(-32000, 'Bad code')


class MyService(Service):
    def hello(self, ctx, data):
        return {"a": "b"}

    @Service.valid(REQ_SCHEM)
    def v_hello(self, ctx, data):
        if data["data"] == "TEST":
            return {"status": "OK"}
        return {"status": "ok"}

    def err_exc(self, ctx, data):
        raise Exception("test middleware, exception is ok")

    def err_exc2(self, ctx, data):
        raise NameError("test custom middleware, exception is ok")

    def err_gt(self, ctx, data):
        raise AttributeError("test custom middleware, exception is ok")

    def err_lt(self, ctx, data):
        raise LookupError("test custom middleware, exception is ok")


def create_response(id=None, result=None):
    return {"jsonrpc": "2.0", "id": id, "result": result}


def create_request(method, id=None, params=None):
    return {
        "jsonrpc": "2.0", "id": id,
        "method": method, "params": params
    }
