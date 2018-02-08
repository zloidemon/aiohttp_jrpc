""" Simple JSON-RPC 2.0 protocol for aiohttp"""
from .exc import (ParseError, InvalidRequest, InvalidParams,
                  InternalError, InvalidResponse)
from .errors import JError, JResponse

from validictory import validate, ValidationError, SchemaError
from functools import wraps
from uuid import uuid4
from aiohttp import ClientSession
import asyncio
import json
import traceback

__version__ = '0.1.0'

REQ_JSONRPC20 = {
    "type": "object",
    "properties": {
        "jsonrpc": {"pattern": r"2\.0"},
        "method": {"type": "string"},
        "params": {"type": "any"},
        "id": {"type": "any"},
    },
}
RSP_JSONRPC20 = {
    "type": "object",
    "properties": {
        "jsonrpc": {"pattern": r"2\.0"},
        "result": {"type": "any"},
        "id": {"type": "any"},
    },
}
ERR_JSONRPC20 = {
    "type": "object",
    "properties": {
        "jsonrpc": {"pattern": r"2\.0"},
        "error": {
            "type": "object",
            "properties": {
                "code": {"type": "number"},
                "message": {"type": "string"},
            }
        },
        "id": {"type": "any"},
    },
}


@asyncio.coroutine
def jrpc_errorhandler_middleware(app, handler):
    @asyncio.coroutine
    def middleware(request):
        try:
            return (yield from handler(request))
        except Exception:
            traceback.print_exc()
            return JError().internal()
    return middleware


@asyncio.coroutine
def decode(request):
    """ Get/decode/validate json from request """
    try:
        data = yield from request.json()
    except Exception as err:
        raise ParseError(err)

    try:
        validate(data, REQ_JSONRPC20)
    except ValidationError as err:
        raise InvalidRequest(err)
    except SchemaError as err:
        raise InternalError(err)
    except Exception as err:
        raise InternalError(err)
    return data


class Service(object):
    """ Service class """

    def __new__(cls, ctx):
        """ Return on call class """
        return cls.__run(cls, ctx)

    def valid(schema=None):
        """ Validation data by specific validictory configuration """
        def dec(fun):
            @wraps(fun)
            def d_func(self, ctx, data, *a, **kw):
                try:
                    validate(data['params'], schema)
                except ValidationError as err:
                    raise InvalidParams(err)
                except SchemaError as err:
                    raise InternalError(err)
                return fun(self, ctx, data['params'], *a, **kw)
            return d_func
        return dec

    @asyncio.coroutine
    def __run(self, ctx):
        """ Run service """
        try:
            data = yield from decode(ctx)
        except ParseError:
            return JError().parse()
        except InvalidRequest:
            return JError().request()
        except InternalError:
            return JError().internal()

        try:
            i_app = getattr(self, data['method'])
            i_app = asyncio.coroutine(i_app)
        except Exception:
            return JError(data).method()

        try:
            resp = yield from i_app(self, ctx, data)
        except InvalidParams:
            return JError(data).params()
        except InternalError:
            return JError(data).internal()

        return JResponse(jsonrpc={
            "id": data['id'], "result": resp
            })


class Response(object):

    __slots__ = ['id', 'error', 'result']

    def __init__(self, id, result=None, error=None, **kw):
        self.id = id
        self.result = result
        self.error = error

    def __repr__(self):
        return "Response(id={rid}, result={res}, error={err}".format(
                    rid=self.id, res=self.result, err=self.error)


class Client(object):
    def __init__(self, url, dumper=None, loop=None):
        self.url = url
        self.dumper = dumper
        if not loop:
            loop = asyncio.get_event_loop()
        if not self.dumper:
            self.dumper = json.dumps

        self.client = ClientSession(
                          loop=loop,
                          headers={'content-type': 'application/json'})

    def __del__(self):
        self.client.close()

    def __encode(self, method, params=None, id=None):
        try:
            data = self.dumper({
                    "jsonrpc": "2.0",
                    "id": id,
                    "method": method,
                    "params": params
                   })
        except Exception as e:
            raise Exception("Can not encode: {}".format(e))

        return data

    @asyncio.coroutine
    def call(self, method, params=None, id=None, schem=None):
        if not id:
            id = uuid4().hex
        try:
            resp = yield from self.client.post(
                   self.url, data=self.__encode(method, params, id))
        except Exception as err:
            raise Exception(err)

        if 200 != resp.status:
            raise InvalidResponse(
                "Error, server retunrned: {status}".format(status=resp.status))

        try:
            data = yield from resp.json(loader=json.loads)
        except Exception as err:
            raise InvalidResponse(err)

        try:
            validate(data, ERR_JSONRPC20)
            return Response(**data)
        except ValidationError:
            # Passing data to validate response.
            # Good if does not valid to ERR_JSONRPC20 object.
            pass
        except Exception as err:
            raise InvalidResponse(err)

        try:
            validate(data, RSP_JSONRPC20)
            if id != data['id']:
                raise InvalidResponse(
                       "Rsponse id {local} not equal {remote}".format(
                            local=id, remote=data['id']))
        except Exception as err:
            raise InvalidResponse(err)

        if schem:
            try:
                validate(data['result'], schem)
            except ValidationError as err:
                raise InvalidResponse(err)
            except Exception as err:
                raise InternalError(err)

        return Response(**data)
