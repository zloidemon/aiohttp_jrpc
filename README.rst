aiohttp_jrpc
============
.. image:: https://travis-ci.org/zloidemon/aiohttp_jrpc.svg?branch=master
    :target: https://travis-ci.org/zloidemon/aiohttp_jrpc
.. image:: https://coveralls.io/repos/zloidemon/aiohttp_jrpc/badge.svg
    :target: https://coveralls.io/r/zloidemon/aiohttp_jrpc
.. image:: https://badge.fury.io/py/aiohttp_jrpc.svg
    :target: https://badge.fury.io/py/aiohttp_jrpc

jsonrpc_ protocol implementation for `aiohttp.web`__.

__ aiohttp_web_


Example
-------

.. code:: python

    import asyncio
    from aiohttp import web
    from aiohttp_jrpc import Service, JError, jrpc_errorhandler_middleware

    SCH = {
        "type": "object",
        "properties": {
            "data": {"type": "string"},
        },
    }

    @asyncio.coroutine
    def custom_errorhandler_middleware(app, handler):
        @asyncio.coroutine
        def middleware(request):
            try:
                return (yield from handler(request))
            except Exception:
                """ Custom errors: -32000 to -32099 """
                return JError().custom(-32000, "Example error")
        return middleware

    class MyJRPC(Service):
        @Service.valid(SCH)
        def hello(self, ctx, data):
            if data["data"] == "hello":
                return {"status": "hi"}
            return {"status": data}

        def error(self, ctx, data):
            raise Exception("Error which will catch middleware")

        def no_valid(self, ctx, data):
            """ Method without validation incommig data """
            return {"status": "ok"}

    @asyncio.coroutine
    def init(loop):
        app = web.Application(loop=loop, middlewares=[jrpc_errorhandler_middleware])
        #app = web.Application(loop=loop, middlewares=[custom_errorhandler_middleware])
        app.router.add_route('POST', "/api", MyJRPC)

        srv = yield from loop.create_server(app.make_handler(),
                                            "127.0.0.1", 8080)
        print("Server started at http://127.0.0.1:8080")
        return srv

    loop = asyncio.get_event_loop()
    loop.run_until_complete(init(loop))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

License
-------

``aiohttp_jrpc`` BSD license.


.. _jsonrpc: http://www.jsonrpc.org/specification
.. _aiohttp_web: http://aiohttp.readthedocs.org/en/latest/web.html
