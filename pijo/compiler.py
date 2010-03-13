import re

TYPES = ['arg', 'string', 'date', 'int', 'decimal', 'struct']

class PijoException(Exception):
    def __init__(self, msg, line=None):
        self.line = line
        if line:
            msg = msg + '; line ' + str(line)
        Exception.__init__(self, msg)

def tokenize(raw):
    # Remove comments
    raw = re.sub(r'//(.*?)($|\n)', '\n', raw)
    pattern = r'(\".*?\"|\b\w+?\b|[,;(){}<>\[\]]|->|\n)'
    return re.findall(pattern, raw)


def parse(target):
    p = PijoParser(target)
    p.parse()
    
    return p.file

class PijoParser(object):
    def __init__(self, filename):
        self.raw = open(filename).read()
        self.tokens = tokenize(self.raw)
        self.file = PijoFile(filename)
        self.line = 0
        
    def peek(self):
        while True:
            if not self.tokens:
                return None
            token = self.tokens[0]
            if token == '\n':
                self.line += 1
                self.tokens.pop(0)
                continue
            return token
        
    def peek_compare(self, expected):
        if not isinstance(expected, list):
            expected = [expected]
        token = self.peek()
        return token in expected
        
    def shift(self):
        token = self.peek()
        if token != None:
            self.tokens.pop(0)
#        print 'shift', token
        return token
    
    def shift_expected(self, expected, msg=None):
        if not isinstance(expected, list):
            expected = [expected]
        token = self.shift()
        if token not in expected:
            raise PijoException(msg or "Unexpected token %s. Expected one of: %s" % (token, expected), self.line)
        return token

    def shift_word(self, msg=None):
        token = self.shift()
        # true if token contains only alphanumerical characters
        if not len(re.match(r'\w*', token).group(0)) == len(token):
            raise PijoException(msg or "Expected alphanumeric string, not %s" %(token,))
        return token
        
        
    def parse(self):
        self.state = 'top'
        while self.state != 'finished':
            getattr(self, 'state_' + self.state)()


    def parse_args(self, into_args, allow_conditions=False):
        while True:
            if self.peek_compare('}'):
                return
            type = self.shift_expected(TYPES)
            struct_name = None
            if type == 'struct':
                self.shift_expected('<')
                struct_name = self.shift_word()
                self.shift_expected('>')
            name = self.shift_word()
            self.shift_expected(';')
            conditions = []
            if allow_conditions and self.peek_compare('['):
                self.shift()
                while True:
                    condition = [self.shift_word()] # symbol
                    if self.peek_compare('('):
                        self.shift()
                        while True:
                            condition.append(self.shift_word()) # arg
                            if self.shift_expected([',', ')']) == ')':
                                break
                    conditions.append(condition)
                    if self.shift_expected([']', ',']) == ']':
                        break
            into_args.add_arg(PijoArg(name, type, conditions, struct_name))


    def state_top(self):
        if self.peek_compare(None):
            self.state = 'finished'
            return
        type = self.shift_expected(['protocol', 'struct'])
        self.state = 'top_' + type
        
    def state_top_struct(self):
        self.shift_expected('<')
        name = self.shift_word()
        self.shift_expected('>')
        struct = PijoStruct(name)
        self.file.add_struct(struct)
        self.shift_expected('{')
        self.parse_args(struct.args)
        self.shift_expected('}')
        self.state = 'top'
    
    def state_top_protocol(self):
        name = self.shift_word()
        self._protocol = PijoProtocol(name)
        self.file.add_protocol(self._protocol)
        self.shift_expected('{')
        self.state = 'protocol_block'
        while self.state.startswith('protocol'):
            getattr(self, 'state_' + self.state)()
        del self._protocol
        self.shift_expected('}')
        self.state = 'top'


    def state_protocol_block(self):
        if self.peek_compare('}'):
            self.state = 'done'
            return
        type = self.shift_expected(['rpc', 'event'])
        self._direction = None
        if self.peek_compare('->'):
            self.shift()
            self._direction = self.shift_expected(['server', 'client'])
        self.state = 'protocol_' + type
        getattr(self, 'state_' + self.state)()
        del self._direction
        self.shift_expected('}')
        self.state = 'protocol_block'
        
    def state_protocol_rpc(self):
        name = self.shift_word()
        rpc = PijoRPC(name, self._direction)
        self._protocol.add_rpc(rpc)
        self.shift_expected('{')
        while not self.peek_compare('}'):
            type = self.shift_expected(['request', 'response'])
            if getattr(rpc, type) != None:
                raise PicoExcepction("Redefinition of RPC %s %s" % name, type)
            item = None
            if type == 'request':
                item = rpc.request = PijoRPCRequest()
            else:
                item = rpc.response = PijoRPCResponse()
            self.shift_expected('{')
            self.parse_args(item.args, allow_conditions=True)
            self.shift_expected('}')
            
    def state_protocol_event(self):
        name = self.shift_word()
        event = PijoEvent(name, self._direction)
        self._protocol.add_event(event)
        self.parse_args(event.args, allow_conditions=True)

class PijoFile(object):
    def __init__(self, name):
        self.structs = {}
        self.protocols = {}
    
    def add_struct(self, struct):
        if struct.name in self.structs:
            raise PijoException("Redefinition of struct " + struct.name)
        self.structs[struct.name] = struct
        
    def add_protocol(self, protocol):
        if protocol.name in self.protocols:
            raise pijoException("Redefinition of protocol " + protocol.name)
        self.protocols[protocol.name] = protocol
        
    
class PijoStruct(object):
    def __init__(self, name):
        self.args = PijoArgGroup()
        self.name = name
        
        
class PijoProtocol(object):
    def __init__(self, name):
        self.name = name
        self.rpcs = {}
        self.events = {}
        
    def add_rpc(self, rpc):
        if rpc.name in self.rpcs:
            raise PijoException("redefinition of rpc " + rpc.name)
        if rpc.name in self.events:
            raise PijoException("conflicting event and rpc definitions of " + rpc.name)
        self.rpcs[rpc.name] = rpc

    def add_event(self, event):
        if event.name in self.events:
            raise PijoException("redefinition of rpc " + event.name)
        if event.name in self.events:
            raise PijoException("conflicting event and rpc definitions of " + event.name)
        self.events[event.name] = event


class PijoRPC(object):
    type = 'rpc'
    def __init__(self, name, direction=None):
        self.name = name
        self.direction = direction
        self.request = None
        self.response = None
        
class PijoEvent(object):
    type = 'event'
    def __init__(self, name, direction=None):
        self.name = name
        self.direction = direction
        self.args = {}

class PijoArgGroup(object):
    def __init__(self):
        self.args = {}
    
    def add_arg(self, arg):
        if arg.name in self.args:
            raise PijoException("redefinition of argument %s" % (arg.name,))
        self.args[arg.name] = arg
        
class PijoArg(object):
    def __init__(self, name, type, conditions, struct_name = None):
        self.name = name
        self.type = type
        self.conditions = conditions
        self.struct_name = struct_name

class PijoRPCRequest(object):
    def __init__(self):
        self.args = PijoArgGroup()
        
class PijoRPCResponse(object):
    def __init__(self):
        self.args = PijoArgGroup()


        
