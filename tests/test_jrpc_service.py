import asyncio
import socket
import unittest
import json
import aiohttp
from aiohttp import web
from aiohttp_jrpc import jrpc_errorhandler_middleware
from utils import custom_errorhandler_middleware, MyService
from utils import create_response, create_request
from utils import (
    CUSTOM_ERROR_GT,
    CUSTOM_ERROR_LT,
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    NOT_FOUND,
    PARSE_ERROR,
    SERVER_ERROR,
)


class TestService(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)
        self.client = aiohttp.ClientSession(loop=self.loop)

    def tearDown(self):
        self.loop.run_until_complete(self.client.close())
        self.loop.run_until_complete(self.handler.cleanup())
        self.loop.close()

    def find_unused_port(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
        sock.close()
        return port

    async def request_wrapper(self, request):
        """ It's acctually need for tests on travis I could not reproduce """
        return (await MyService(request))

    async def create_server(self, middlewares=[]):
        app = web.Application(middlewares=middlewares)

        app.router.add_route('*', '/', self.request_wrapper)

        self.handler = web.AppRunner(app)
        port = self.find_unused_port()
        await self.handler.setup()
        srv = web.TCPSite(
            self.handler, '127.0.0.1', port)
        url = "http://127.0.0.1:{}/".format(port)
        self.srv = srv
        await self.srv.start()
        return app, srv, url

    def test_errors(self):

        async def get(check):
            app, srv, url = await self.create_server(middlewares=[
                jrpc_errorhandler_middleware])
            resp = await self.client.get(url)
            self.assertEqual(200, resp.status)
            self.assertEqual(check, (await resp.json()))
            self.assertEqual(None, (await resp.release()))

        async def post(check, data=None):
            app, srv, url = await self.create_server(middlewares=[
                jrpc_errorhandler_middleware])
            resp = await self.client.post(url, data=json.dumps(data))
            self.assertEqual(200, resp.status)
            self.assertEqual(check, (await resp.json()))
            self.assertEqual(None, (await resp.release()))

        self.loop.run_until_complete(get(PARSE_ERROR))
        self.loop.run_until_complete(post(INVALID_REQUEST))
        self.loop.run_until_complete(post(INVALID_REQUEST, {"example": None}))
        self.loop.run_until_complete(post(NOT_FOUND,
                                          create_request("not_found")))
        self.loop.run_until_complete(post(INVALID_PARAMS,
                                          create_request("v_hello")))
        self.loop.run_until_complete(post(INTERNAL_ERROR,
                                          create_request("err_exc")))

    def test_custom_error(self):

        async def post(check, data=None):
            app, srv, url = await self.create_server(middlewares=[
                custom_errorhandler_middleware])
            resp = await self.client.post(url, data=json.dumps(data))
            self.assertEqual(200, resp.status)
            self.assertEqual(check, (await resp.json()))
            self.assertEqual(None, (await resp.release()))

        self.loop.run_until_complete(post(SERVER_ERROR,
                                          create_request("err_exc")))
        self.loop.run_until_complete(post(INTERNAL_ERROR,
                                          create_request("err_exc2")))
        self.loop.run_until_complete(post(CUSTOM_ERROR_GT,
                                          create_request("err_gt")))
        self.loop.run_until_complete(post(CUSTOM_ERROR_LT,
                                          create_request("err_lt")))

    def test_validate(self):
        async def post(check, data=None):
            app, srv, url = await self.create_server()
            resp = await self.client.post(url, data=json.dumps(data))
            self.assertEqual(200, resp.status)
            self.assertEqual(check, (await resp.json()))
            self.assertEqual(None, (await resp.release()))

        self.loop.run_until_complete(post(INVALID_PARAMS,
                                          create_request("v_hello")))
        self.loop.run_until_complete(
            post(create_response(result={"status": "ok"}),
                 create_request("v_hello", params={"data": "ok"})))
        self.loop.run_until_complete(
            post(create_response(1234, {"status": "ok"}),
                 create_request("v_hello", 1234, {"data": "ok"})))
        self.loop.run_until_complete(
            post(create_response(None, {"status": "ok"}),
                 create_request("v_hello", None, {"data": "ok"})))
        self.loop.run_until_complete(
            post(create_response("1", {"status": "OK"}),
                 create_request("v_hello", "1", {"data": "TEST"})))
        self.loop.run_until_complete(
            post(INVALID_REQUEST,
                 create_request("v_hello", True, {"data": "ok"})))
        self.loop.run_until_complete(
            post(INVALID_REQUEST,
                 create_request("v_hello", False, {"data": "ok"})))

    def test_without_validate(self):
        async def post(check, data=None):
            app, srv, url = await self.create_server()
            resp = await self.client.post(url, data=json.dumps(data))
            self.assertEqual(200, resp.status)
            self.assertEqual(check, (await resp.json()))
            self.assertEqual(None, (await resp.release()))

        self.loop.run_until_complete(
            post(create_response(None, {"a": "b"}),
                 create_request("hello")))
        self.loop.run_until_complete(
            post(create_response(123, {"a": "b"}),
                 create_request("hello", 123)))
        self.loop.run_until_complete(
            post(create_response("123", {"a": "b"}),
                 create_request("hello", "123")))
