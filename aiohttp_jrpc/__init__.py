""" Simple JSON-RPC 2.0 protocol for aiohttp"""
from .exc import (ParseError, InvalidRequest, InvalidParams,
                  InternalError)
from .errors import JError, JResponse

from validictory import validate, ValidationError, SchemaError
from functools import wraps
import asyncio
import json
import traceback

__version__ = '0.0.1'

JSONRPC20 = {
    "type": "object",
    "properties": {
        "jsonrpc": {"pattern": r"2\.0"},
        "method": {"type": "string"},
        "params": {"type": "any"},
        "id": {"type": "any"},
    },
}


@asyncio.coroutine
def decode(request):
    """ Get/decode/validate json from request """
    try:
        data = yield from request.json(loader=json.loads)
    except Exception as err:
        raise ParseError(err)

    try:
        validate(data, JSONRPC20)
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
                except Exception as err:
                    traceback.print_exc()
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
        except Exception:
            traceback.print_exc()
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
        except Exception:
            traceback.print_exc()
            return JError(data).internal()

        return JResponse(jsonrpc={
            "id": data['id'], "result": resp
            })
