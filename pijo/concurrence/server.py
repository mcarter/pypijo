import rtjp.concurrence as rtjp
from concurrence import Tasklet
#from db.models import *
from pijo import compiler
class ExpectedException(Exception):
    pass

class PijoServer(object):
    
    def __init__(self, filename, protocol_name, impl_class):
        pijo_file = compiler.parse(filename)
        print 'found', pijo_file.protocols.keys()
        print 'need', protocol_name
        print repr(pijo_file.protocols.keys()[0])
        print repr(protocol_name)
        print protocol_name in pijo_file.protocols.keys()
        if protocol_name not in pijo_file.protocols:
            raise Exception("Protocol %s not found in %s" % (protocol_name, filename))
        self.protocol = pijo_file.protocols[protocol_name]
        self.implementation = impl_class(self)
        self._server = None
        
    def listen(self, port, interface=''):
        self._server = rtjp.RTJPServer()
        self._server.listen(port, interface).wait()
        while True:
            conn = self._server.accept().wait()
            Tasklet.new(self._loop)(conn)
            
    def _loop(self, conn):
        try:
            while True:
                try:
                    id, name, args = conn.recv_frame().wait()
                except:
                    print "Connection Lost"
                    break
                if name == 'REQUEST':
                    method_name = args.get('name', None)
                    method_args = args.get('args', None)
                    if not method_name:
                        self.error_response(conn, id, "Missing method name")
                        continue
                    if method_args == None:
                        self.error_response(conn, id, "Missing args")
                        continue
                    rpc = self.protocol.rpcs.get(method_name, None)
                    if not rpc:
                        self.error_response(conn, id, "Invalid Method")
                        # TODO: Error
                        continue
                    if rpc.direction != 'server':
                        self.error_response(conn, id, "Invalid Method (check direction)")
                        continue
                    constructed_args = {}
                    for name, arg in rpc.request.args.args.items():
                        if name in method_args:
                            constructed_args[name] = method_args[name]
                            del method_args[name]
                        # TODO: constraints/conditions checking
                    if method_args:
                        # TODO: extra arguments. throw them out?
                        pass
                    handler = getattr(self.implementation, method_name, None)
                    if not handler:
                        self.error_response(conn, id, "Method not implemented")
                        continue
                    try:
                        print 'constructed_args', constructed_args
                        result = handler(conn, **constructed_args)
                        print 'result is', result
                    except ExpectedException, e:
                        self.error_response(conn, id, e)
                        # TODO: Send Error
                    except Exception, e:
                        # TODO: log it
                        import traceback
                        exception, instance, tb = traceback.sys.exc_info()
                        output = "".join(traceback.format_tb(tb))
                        print output
                        self.error_response(conn, id, e)
                    else:
                        conn.send_frame('RESPONSE', {
                            'requestId': id, 
                            'success': True,
                            'result': result,
                        })
        except Exception, e:
            print "wtf", e
            raise
    def error_response(self, conn, id, msg, details=None):
        conn.send_frame('RESPONSE', {
            "requestId": id,
            "success": False,
            "result": {
                "msg": str(msg),
                "details": details
            }
        })