from __future__ import absolute_import
import rtjp.eventlet
import eventlet
from . import compiler, core
import rtjp.errors
class Server(object):
    __protocol__ = None
    def create_protocol(self, conn):
        return self.__protocol__(self)

def connect(impl_class, port, hostname, protocol=None):
    ev = eventlet.event.Event()
    if not protocol:
        pijo_file = pijo.compiler.parse(impl_class.__source_file__)
        protocol = pijo_file.protocols[impl_class.__protocol_name__]
        
    eventlet.spawn(_connect, ev, impl_class, protocol, port, hostname)
    return ev
    
def _connect(ev, impl_class, protocol, port, hostname):
    pijo_conn = PijoConn(impl_class, protocol, 'client')
    rtjp_conn = rtjp.eventlet.RTJPConnection()
    try:
        rtjp_conn.connect(hostname, port).wait()
    except Exception, e:
        ev.send_exception(e)
    else:
        pijo_conn._make_connection(rtjp_conn)
        ev.send(pijo_conn)

def serve(server, port=None, interface='', protocol=None, sock=None):
    ev = eventlet.event.Event()
    if not protocol:
        pijo_file = compiler.parse(server.__protocol__.__source_file__)
        protocol = pijo_file.protocols[server.__protocol__.__protocol_name__]
    def impl_class(conn):
        p = server.create_protocol(conn)
        p.server = server
        return p
    eventlet.spawn(_serve, ev, impl_class, protocol, port, interface, sock)
    return ev
    
def _serve(ev, impl_class, protocol, port, interface, sock):
    server = rtjp.eventlet.RTJPServer(sock)
    try:
        if not sock:
            server.listen(port, interface).wait()
        while True:
            rtjp_conn = server.accept().wait()
            pijo_conn = PijoConn(impl_class, protocol, 'server', rtjp_conn)
    except Exception, e:
        ev.send_exception(e)

class ExpectedException(Exception):
    pass

class Response(object):
    def __init__(self):
        self._response_queue = eventlet.queue.Queue()
        self._active = True
        
        
    def is_active(self):
        return self._active
    
    def read_response(self):
#        if not self._active:
#            raise Exception("Response already completed")
        ev = eventlet.event.Event()
        eventlet.spawn(self._read_response, ev)
        return ev
    
    def _read_response(self, ev):
        try:
            success, result, partial, complete = self._response_queue.get()
        except Exception, e:
            ev.send_exception(e)
        if partial:
            def loop():
                yield result
                while True:
                    success, _result, partial, complete = self._response_queue.get()
                    if complete:
                        raise StopIteration
                    if success:
                        yield _result
                    else:
                        raise Exception(_result.get('msg', None), _result.get('details', None))
            ev.send(loop())
        else:
            if success:
                ev.send(result)
            else:
                ev.send_exception(Exception(result.get('msg', None), result.get('details', None)))
    
    def _received_response(self, success, result, partial, complete):
        print '_received_response', success, result, partial, complete
        self._active = partial and not complete
        self._response_queue.put((success, result, partial, complete))
    
class PijoRemoteFunction(object):
    def __init__(self, conn, remote):
        self._remote = remote
        self._conn = conn
        
    def __call__(self, **kwargs):
        for key, val in kwargs.items():
            if key not in self._remote.request.args.args:
                raise Exception("Invalid argument: %s" % (key,))
        # ignore event returned by _request
        if self._remote.type == 'rpc':
            r = Response()
            self._conn._request(r, self._remote.name, kwargs)
            return r.read_response().wait()
        else:
            return self._conn._event(self._remote.name, kwargs)

class PijoConn(object):
    
    def __init__(self, impl_class, protocol, direction, conn=None):
        self._implementation = impl_class(self)
        self._protocol = protocol
        self._direction = direction
        self._requests = {}
        remotes = protocol.rpcs.items() + protocol.events.items()
        for name, remote in remotes:
            if not remote.direction or remote.direction != direction:
                setattr(self, name, PijoRemoteFunction(self, remote))
        if conn:
            self._make_connection(conn)
        
    def _request(self, response, name, args):
        ev = eventlet.event.Event()
        eventlet.spawn(self.__request, ev, response, name, args)
        return ev
        
    def __request(self, ev, response, name, args):
        try:
            print 'send a frame2'
            print 'a'
            print 'b'
            print 'rtjp_conn', self._conn
            print 'c'
            print 'wtf'
            print '!'
            id = self._conn.send_frame('REQUEST', {
                'name': name, 
                'args':args
            }).wait()
            print 'id is', id
            self._requests[id] = response
        except Exception, e:
            print 'EXCEPTION!'
            ev.send_exception(e)
            print 'k..'
        else:
            ev.send(None)

    def _event(self, name, args):
        ev = eventlet.event.wait()
        eventlet.spawn(self._event, ev, name, args)
        return ev
        
    def __event(self, ev, name, args):
        try:
            id = self._conn.send_frame('EVENT', {
                'name': name, 
                'args':args
            }).wait()
        except Exception, e:
            ev.send_exception(e)
        else:
            ev.send(None)

    def _event(self, name, args):
        self._rtjp_conn.send_frame('EVENT', {
            'name': name,
            'args': args,
        }).wait()
        
    def _make_connection(self, conn):
        self._conn = conn
        self._implementation._connection_made()
        eventlet.spawn(self._run)


    def _dispatch_request(self, id, method_name, args):
        handler = getattr(self._implementation, method_name, None)
        if not handler:
            self._error_response(id, "Method not implemented")
            return
        try:
            result = handler(**args)
        except ExpectedException, e:
            self._error_response(id, e)
            # TODO: Send Error
        except Exception, e:
            # TODO: log it
            import traceback
            exception, instance, tb = traceback.sys.exc_info()
            output = "".join(traceback.format_tb(tb))
            print output
            self._error_response(id, e)
        else:
            if hasattr(result, 'next'):
                try:
                    for partial in result:
                        self._conn.send_frame('RESPONSE', {
                            'requestId': id, 
                            'success': True,
                            'result': partial,
                            'partial': True
                        })
                    self._conn.send_frame('RESPONSE', {
                        'requestId': id,
                        'complete': True
                    })
                except Exception, e:
                    self._error_response(id, e)
            else:
                self._conn.send_frame('RESPONSE', {
                    'requestId': id, 
                    'success': True,
                    'result': result,
                })

    def _run(self):
        while True:
            try:
                id, name, args = self._conn.recv_frame().wait()
            except rtjp.errors.ConnectionLost:
                print "Connection Lost"
                self._implementation._connection_lost()
                break
            print 'read', id, name, args
            if name == 'REQUEST':
                try:
                    method_name, constructed_args = core.parse_request(self._protocol, self._direction, args)
                except core.PijoInvocationError, e:
                    print 'ivocation error?', e
                    self._error_response(id, str(e))
                    continue
                eventlet.spawn(self._dispatch_request, id, method_name, constructed_args)
                continue
            if name == 'RESPONSE':
                request_id = args.get('requestId', None)
                if request_id not in self._requests:
                    # Invalid response... error?
                    continue
                response = self._requests[request_id]
                result = args.get('result', {})
                partial = args.get('partial', False)
                success = args.get('success', False)
                complete = args.get('complete', False)
                # TODO: figure out request/multi-response 
                if not partial:
                    del self._requests[request_id]
                response._received_response(success, result, partial, complete)
                continue
            
    def _error_response(self, id, msg, details=None):
        return self._conn.send_frame('RESPONSE', {
            "requestId": id,
            "success": False,
            "result": {
                "msg": str(msg),
                "details": details
            }
        })            
            

