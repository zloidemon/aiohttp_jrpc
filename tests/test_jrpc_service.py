import asyncio
import socket
import unittest
import json
import aiohttp
from aiohttp import web
from aiohttp_jrpc import Service

PARSE_ERROR = {
    'jsonrpc': '2.0', 'id': None,
    'error': {'code': -32700, 'mesage': 'Parse error'}
}
INVALID_REQUEST = {
    'jsonrpc': '2.0', 'id': None,
    'error': {'code': -32600, 'mesage': 'Invalid Request'}
}
NOT_FOUND = {
    'jsonrpc': '2.0', 'id': None,
    'error': {'code': -32601, 'mesage': 'Method not found'}
}
INVALID_PARAMS = {
    'jsonrpc': '2.0', 'id': None,
    'error': {'code': -32602, 'mesage': 'Invalid params'}
}

REQ_SCHEM = {
    "type": "object",
    "properties": {
        "data": {"type": "string"},
    }
}


class MyService(Service):
    def hello(self, ctx, data):
        return {"a": "b"}

    @Service.valid(REQ_SCHEM)
    def v_hello(self, ctx, data):
        if data["data"] == "TEST":
            return {"status": "OK"}
        return {"status": "ok"}


class TestErrors(unittest.TestCase):

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
    def create_server(self):
        app = web.Application(loop=self.loop)

        port = self.find_unused_port()
        self.handler = app.make_handler(
            debug=False, keep_alive_on=False)
        app.router.add_route('*', '/', MyService)
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
            app, srv, url = yield from self.create_server()
            resp = yield from self.client.get(url)
            self.assertEqual(200, resp.status)
            self.assertEqual(check, (yield from resp.json()))
            self.assertEqual(None, (yield from resp.release()))

        @asyncio.coroutine
        def post(check, data=None):
            app, srv, url = yield from self.create_server()
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
