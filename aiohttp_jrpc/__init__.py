""" Simple JSON-RPC 2.0 protocol for aiohttp"""
from .exc import (
    InternalError,
    InvalidParams,
    InvalidRequest,
    InvalidResponse,
    ParseError,
)
from .errors import JError, JResponse

from jsonschema import validate, ValidationError, SchemaError, FormatChecker
from functools import wraps
from uuid import uuid4
from aiohttp.web import middleware
import asyncio
import json
import traceback

__version__ = '0.2.0'

REQ_JSONRPC20 = {
    "type": "object",
    "properties": {
        "jsonrpc": {"pattern": r"2\.0"},
        "method": {"type": "string"},
        "params": {
            "anyOf": [
                {"type": "array"},
                {"type": "boolean"},
                {"type": "integer"},
                {"type": "null"},
                {"type": "number"},
                {"type": "object"},
                {"type": "string"},
            ]
        },
        "id": {
            "anyOf": [
                {"type": "null"},
                {"type": "number"},
                {"type": "string"},
            ]
        },
    },
    "required": ["jsonrpc", "method", "id"],
}
RSP_JSONRPC20 = {
    "type": "object",
    "properties": {
        "jsonrpc": {"pattern": r"2\.0"},
        "result": {
            "anyOf": [
                {"type": "array"},
                {"type": "boolean"},
                {"type": "integer"},
                {"type": "null"},
                {"type": "number"},
                {"type": "object"},
                {"type": "string"},
            ]
        },
        "id": {
            "anyOf": [
                {"type": "string"},
                {"type": "number"},
            ]
        },
    },
    "required": ["jsonrpc", "result", "id"],
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
                "data": {
                    "anyOf": [
                        {"type": "array"},
                        {"type": "boolean"},
                        {"type": "integer"},
                        {"type": "null"},
                        {"type": "number"},
                        {"type": "object"},
                        {"type": "string"},
                    ]
                }
            },
            "required": ["code", "message"],
        },
        "id": {
            "anyOf": [
                {"type": "null"},
                {"type": "number"},
                {"type": "string"},
            ]
        },
    },
    "required": ["jsonrpc", "error", "id"],
}


@middleware
async def jrpc_errorhandler_middleware(request, handler):
    try:
        return (await handler(request))
    except Exception:
        traceback.print_exc()
        return JError().internal()


async def decode(request):
    """ Get/decode/validate json from request """
    try:
        data = await request.json()
    except Exception as err:
        raise ParseError(err)

    try:
        validate(data, REQ_JSONRPC20, format_checker=FormatChecker())
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
                    validate(
                        data['params'],
                        schema,
                        format_checker=FormatChecker()
                    )
                except ValidationError as err:
                    raise InvalidParams(err)
                except SchemaError as err:
                    raise InternalError(err)
                return fun(self, ctx, data['params'], *a, **kw)
            return d_func
        return dec

    async def __run(self, ctx):
        """ Run service """
        try:
            data = await decode(ctx)
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
            resp = await i_app(self, ctx, data)
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
    def __init__(self, client, url, dumper=None):
        self.url = url
        self.dumper = dumper
        if not self.dumper:
            self.dumper = json.dumps

        self.client = client

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

    async def call(self, method, params=None, id=None, schem=None):
        if not id:
            id = uuid4().hex

        async with self.client.post(
                self.url, data=self.__encode(method, params, id),
                headers={'content-type': 'application/json'}) as resp:

            if 200 != resp.status:
                raise InvalidResponse(
                    "Error, server retunrned: {status}".format(
                        status=resp.status))

            try:
                data = await resp.json()
            except Exception as err:
                raise InvalidResponse(err)

        try:
            validate(data, ERR_JSONRPC20, format_checker=FormatChecker())
            return Response(**data)
        except ValidationError:
            # Passing data to validate response.
            # Good if does not valid to ERR_JSONRPC20 object.
            pass
        except Exception as err:
            raise InvalidResponse(err)

        try:
            validate(data, RSP_JSONRPC20, format_checker=FormatChecker())
            if id != data['id']:
                raise InvalidResponse(
                       "Rsponse id {local} not equal {remote}".format(
                            local=id, remote=data['id']))
        except Exception as err:
            raise InvalidResponse(err)

        if schem:
            try:
                validate(data['result'], schem, format_checker=FormatChecker())
            except ValidationError as err:
                raise InvalidResponse(err)
            except Exception as err:
                raise InternalError(err)

        return Response(**data)
