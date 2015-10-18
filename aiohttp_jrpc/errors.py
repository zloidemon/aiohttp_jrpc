""" Error responses """
from aiohttp.web import Response
import json


class JResponse(Response):
    """ Modified Reponse from aohttp """
    def __init__(self, *, status=200, reason=None,
                 headers=None, jsonrpc=None):
        if jsonrpc is not None:
            jsonrpc.update({'jsonrpc': '2.0'})
            text = json.dumps(jsonrpc)
        super().__init__(status=status, reason=reason, text=text,
                         headers=headers, content_type='application/json')


class JError(object):
    """ Class with standart errors """
    def __init__(self, data=None, rid=None):
        if data is not None:
            self.rid = data['id']
        else:
            self.rid = rid

    def parse(self):
        """ json parsing error """
        return JResponse(jsonrpc={
            'id': self.rid,
            'error': {'code': -32700, 'mesage': 'Parse error'},
        })

    def request(self):
        """ incorrect json rpc request """
        return JResponse(jsonrpc={
            'id': self.rid,
            'error': {'code': -32600, 'mesage': 'Invalid Request'},
        })

    def method(self):
        """ Not found method on the server """
        return JResponse(jsonrpc={
            'id': self.rid,
            'error': {'code': -32601, 'mesage': 'Method not found'},
        })

    def params(self):
        """ Incorrect params (used in validate) """
        return JResponse(jsonrpc={
            'id': self.rid,
            'error': {'code': -32602, 'mesage': 'Invalid params'},
        })

    def internal(self):
        """ Internal server error, actually send on every unknow exception """
        return JResponse(jsonrpc={
            'id': self.rid,
            'error': {'code': -32603, 'mesage': 'Internal error'},
        })
