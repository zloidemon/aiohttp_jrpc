import asyncio
import socket
import unittest
import json
import aiohttp
from aiohttp import web
from aiohttp_jrpc import Service, JError, jrpc_errorhandler_middleware

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
CUSTOM_ERROR_GT = {
    'jsonrpc': '2.0', 'id': None,
    'error': {'code': -32000, 'message': 'Custom error gt'}
}
CUSTOM_ERROR_LT = {
    'jsonrpc': '2.0', 'id': None,
    'error': {'code': -32099, 'message': 'Custom error lt'}
}

REQ_SCHEM = {
    "type": "object",
    "properties": {
        "data": {"type": "string"},
    }
}


@asyncio.coroutine
def custom_errorhandler_middleware(app, handler):
    @asyncio.coroutine
    def middleware(request):
        try:
            return (yield from handler(request))
        except AttributeError:
            return JError().custom(-32000, 'Custom error gt')
        except LookupError:
            return JError().custom(-32099, 'Custom error lt')
        except NameError:
            return JError().custom(-32100, 'Bad custom error')
        except Exception:
            return JError().custom(-31999, 'Bad custom error')
    return middleware


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


class TestService(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)
        self.client = aiohttp.ClientSession(loop=self.loop)

    def tearDown(self):
        self.client.close()
        self.loop.run_until_complete(self.handler.finish_connections())
        self.srv.close()
        self.loop.run_until_complete(self.srv.wait_closed())
        self.loop.close()

    def find_unused_port(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
        sock.close()
        return port

    @asyncio.coroutine
    def request_wrapper(self, request):
        """ It's acctually need for tests on travis I could not reproduce """
        return (yield from MyService(request))

    @asyncio.coroutine
    def create_server(self, middlewares=[]):
        app = web.Application(loop=self.loop,
                              middlewares=middlewares)

        port = self.find_unused_port()
        self.handler = app.make_handler(
            debug=False, keep_alive_on=False)
        app.router.add_route('*', '/', self.request_wrapper)
        srv = yield from self.loop.create_server(
            self.handler, '127.0.0.1', port)
        url = "http://127.0.0.1:{}/".format(port)
        self.srv = srv
        return app, srv, url

    def create_request(self, method, rid=None, params=None):
        return {
            "jsonrpc": "2.0", "id": rid,
            "method": method, "params": params
        }

    def create_response(self, rid=None, result=None):
        return {"jsonrpc": "2.0", "id": rid, "result": result}

    def test_errors(self):

        @asyncio.coroutine
        def get(check):
            app, srv, url = yield from self.create_server(middlewares=[
                jrpc_errorhandler_middleware])
            resp = yield from self.client.get(url)
            self.assertEqual(200, resp.status)
            self.assertEqual(check, (yield from resp.json()))
            self.assertEqual(None, (yield from resp.release()))

        @asyncio.coroutine
        def post(check, data=None):
            app, srv, url = yield from self.create_server(middlewares=[
                jrpc_errorhandler_middleware])
            resp = yield from self.client.post(url, data=json.dumps(data))
            self.assertEqual(200, resp.status)
            self.assertEqual(check, (yield from resp.json()))
            self.assertEqual(None, (yield from resp.release()))

        self.loop.run_until_complete(get(PARSE_ERROR))
        self.loop.run_until_complete(post(INVALID_REQUEST))
        self.loop.run_until_complete(post(INVALID_REQUEST, {"example": None}))
        self.loop.run_until_complete(post(NOT_FOUND,
                                          self.create_request("not_found")))
        self.loop.run_until_complete(post(INVALID_PARAMS,
                                          self.create_request("v_hello")))
        self.loop.run_until_complete(post(INTERNAL_ERROR,
                                          self.create_request("err_exc")))

    def test_custom_error(self):

        @asyncio.coroutine
        def post(check, data=None):
            app, srv, url = yield from self.create_server(middlewares=[
                custom_errorhandler_middleware])
            resp = yield from self.client.post(url, data=json.dumps(data))
            self.assertEqual(200, resp.status)
            self.assertEqual(check, (yield from resp.json()))
            self.assertEqual(None, (yield from resp.release()))

        self.loop.run_until_complete(post(INTERNAL_ERROR,
                                          self.create_request("err_exc")))
        self.loop.run_until_complete(post(INTERNAL_ERROR,
                                          self.create_request("err_exc2")))
        self.loop.run_until_complete(post(CUSTOM_ERROR_GT,
                                          self.create_request("err_gt")))
        self.loop.run_until_complete(post(CUSTOM_ERROR_LT,
                                          self.create_request("err_lt")))

    def test_validate(self):
        @asyncio.coroutine
        def post(check, data=None):
            app, srv, url = yield from self.create_server()
            resp = yield from self.client.post(url, data=json.dumps(data))
            self.assertEqual(200, resp.status)
            self.assertEqual(check, (yield from resp.json()))
            self.assertEqual(None, (yield from resp.release()))

        self.loop.run_until_complete(post(INVALID_PARAMS,
                                          self.create_request("v_hello")))
        self.loop.run_until_complete(
            post(self.create_response(result={"status": "ok"}),
                 self.create_request("v_hello", params={"data": "ok"})))
        self.loop.run_until_complete(
            post(self.create_response(1234, {"status": "ok"}),
                 self.create_request("v_hello", 1234, {"data": "ok"})))
        self.loop.run_until_complete(
            post(self.create_response(None, {"status": "ok"}),
                 self.create_request("v_hello", None, {"data": "ok"})))
        self.loop.run_until_complete(
            post(self.create_response("1", {"status": "OK"}),
                 self.create_request("v_hello", "1", {"data": "TEST"})))
        self.loop.run_until_complete(
            post(self.create_response(True, {"status": "ok"}),
                 self.create_request("v_hello", True, {"data": "ok"})))
        self.loop.run_until_complete(
            post(self.create_response(False, {"status": "ok"}),
                 self.create_request("v_hello", False, {"data": "ok"})))

    def test_without_validate(self):
        @asyncio.coroutine
        def post(check, data=None):
            app, srv, url = yield from self.create_server()
            resp = yield from self.client.post(url, data=json.dumps(data))
            self.assertEqual(200, resp.status)
            self.assertEqual(check, (yield from resp.json()))
            self.assertEqual(None, (yield from resp.release()))

        self.loop.run_until_complete(
            post(self.create_response(None, {"a": "b"}),
                 self.create_request("hello")))
        self.loop.run_until_complete(
            post(self.create_response(123, {"a": "b"}),
                 self.create_request("hello", 123)))
        self.loop.run_until_complete(
            post(self.create_response("123", {"a": "b"}),
                 self.create_request("hello", "123")))
