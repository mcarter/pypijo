class PijoInvocationError(Exception):
    pass

def parse_request(protocol, role, args):
    method_name = args.get('name', None)
    method_args = args.get('args', None)
    if not method_name:
        raise PijoInvocationError("Missing method name")
    if method_args == None:
        raise PijoInvocationError("Missing args")
    rpc = protocol.rpcs.get(method_name, None)
    if not rpc:
        raise PijoInvocationError("Invalid Method")
    if not rpc.direction or rpc.direction != role:
        raise PijoInvocationError("Invalid Method (check direction)")
    constructed_args = {}
    print 'method_args', method_args
    for name, arg in rpc.request.args.args.items():
        constructed_args[name] = method_args.pop(name, None)
        # TODO: constraints/conditions checking
    print 'constructed args', constructed_args
    if method_args:
        # TODO: extra arguments. throw them out?
        pass
    return method_name, constructed_args

