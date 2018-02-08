import asyncio
import socket
import unittest
from aiohttp import web
from aiohttp_jrpc import Client, Response
from utils import custom_errorhandler_middleware, MyService
from utils import create_response
from utils import (NOT_FOUND, INVALID_PARAMS, INTERNAL_ERROR,
                   CUSTOM_ERROR_GT, CUSTOM_ERROR_LT)


class TestClient(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)

    def tearDown(self):
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

    async def request_wrapper(self, request):
        """ It's acctually need for tests on travis I could not reproduce """
        return (await MyService(request))

    async def create_server(self, middlewares=[]):
        app = web.Application(loop=self.loop,
                              middlewares=middlewares)

        port = self.find_unused_port()
        self.handler = app.make_handler(
            debug=False, keep_alive_on=False)
        app.router.add_route('*', '/', self.request_wrapper)
        srv = await self.loop.create_server(
            self.handler, '127.0.0.1', port)
        url = "http://127.0.0.1:{}/".format(port)
        self.srv = srv
        client = Client(url, loop=self.loop)
        return app, srv, client

    def test_validate(self):
        async def call(check, method, data=None, id=None):
            app, srv, client = await self.create_server(middlewares=[
                custom_errorhandler_middleware])

            resp = Response(**check)

            if not id:
                id = resp.id

            ret = await client.call(method, data, id=id)

            self.assertEqual(resp.error, ret.error)
            self.assertEqual(resp.result, ret.result)

            if resp.id:
                self.assertEqual(resp.id, ret.id)

        self.loop.run_until_complete(call(INVALID_PARAMS, "v_hello"))
        self.loop.run_until_complete(
            call(create_response(result={"status": "ok"}),
                 "v_hello", {"data": "ok"}))
        self.loop.run_until_complete(
            call(create_response(1234, {"status": "ok"}),
                 "v_hello", {"data": "ok"}, 1234))
        self.loop.run_until_complete(
            call(create_response(None, {"status": "ok"}),
                 "v_hello", {"data": "ok"}, None))
        self.loop.run_until_complete(
            call(create_response("1", {"status": "OK"}),
                 "v_hello", {"data": "TEST"}, "1"))
        self.loop.run_until_complete(
            call(create_response(True, {"status": "ok"}),
                 "v_hello", {"data": "ok"}, True))
        self.loop.run_until_complete(
            call(create_response(False, {"status": "ok"}),
                 "v_hello", {"data": "ok"}, False))

        self.loop.run_until_complete(call(NOT_FOUND, "not_found"))
        self.loop.run_until_complete(call(INVALID_PARAMS, "v_hello"))
        self.loop.run_until_complete(call(INTERNAL_ERROR, "err_exc"))
        self.loop.run_until_complete(call(INTERNAL_ERROR, "err_exc2"))
        self.loop.run_until_complete(call(CUSTOM_ERROR_GT, "err_gt"))
        self.loop.run_until_complete(call(CUSTOM_ERROR_LT, "err_lt"))
