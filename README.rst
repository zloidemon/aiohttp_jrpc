aiohttp_jrpc
============
.. image:: https://travis-ci.org/zloidemon/aiohttp_jrpc.svg?branch=master
    :target: https://travis-ci.org/zloidemon/aiohttp_jrpc
.. image:: https://coveralls.io/repos/zloidemon/aiohttp_jrpc/badge.svg
    :target: https://coveralls.io/r/zloidemon/aiohttp_jrpc

jsonrpc_ protocol implementation for `aiohttp.web`__ .

__ aiohttp_web_


Example
-------

.. code:: python

    import asyncio
    from aiohttp import web
    from aiohttp_jrpc import Service

    SCH = {
        "type": "object",
        "properties": {
            "data": {"type": "string"},
        },
    }

    class MyJRPC(Service):
        @Service.valid(SCH)
        def hello(self, ctx, data):
            if data["data"] == "hello":
                return {"status": "hi"}
            return {"status": data}


    @asyncio.coroutine
    def init(loop):
        app = web.Application(loop=loop)
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
