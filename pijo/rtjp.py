from concurrence import dispatch, Tasklet, Message
from concurrence.io import BufferedStream, Socket, Server
from concurrence.core import Channel
import logging
try:
    import json
except ImportError:
    import simplejson as json

class RTJPConnection(object):
    logger = logging.getLogger('RTJPConnection')
    
    def __init__(self, sock, delimiter='\r\n'):
        self.frame_id = 0
        self.stream = BufferedStream(sock)
        self._frame_channel = Channel()
        self.delimiter = delimiter
        t = Tasklet.new(self._read_forever)()
        
    def _read_forever(self):
        lines = self.stream.reader.read_lines()
        while True:
            try:
                line = lines.next()
            except Exception, e:
                print 'a problem:', repr(e)
                self._frame_channel.send_exception(Exception, "Connection Lost")
                return
            print 'READ', line
            try:
                frame = json.loads(line)
            except:
                self.logger.warn("Error parsing frame: " + repr(line), exc_info=True)
                # TODO: Error?
                continue
            if not isinstance(frame, list):
                self.logger.warn("Invalid frame (not a list): " + repr(frame))
                continue
            if not len(frame) == 3:
                self.logger.warn("Invalid frame length for: " + repr(frame))
                continue
            if (isinstance(frame[1], unicode)):
                frame[1] = str(frame[1])
            if not isinstance(frame[0], int):
                self.logger.warn("Invalid frame id: " + repr(frame[0]))
                continue
            if not isinstance(frame[1], str) or len(frame[1]) == 0:
                self.logger.warn("Invalid frame name: " + repr(frame[1]))
                continue
            if not isinstance(frame[2], dict):
                self.logger.warn("Invalid frame kwargs: " + repr(frame[2]))
                continue
#            print 'frame is', frame
            self._frame_channel.send(frame)
            
    def recv_frame(self):
        return self._frame_channel.receive()

    def send_frame(self, name, args={}):
        self.logger.debug('send_frame', name, args)
        self.frame_id += 1
        raw_frame = json.dumps([self.frame_id, name, args]) + self.delimiter
        print "SEND", raw_frame
        self.stream.writer.write_bytes(raw_frame)
        self.stream.writer.flush()
            
    def send_error(self, reference_id, msg):
        self.send_frame('ERROR', { 'reference_id': reference_id, 'msg': str(msg) })
        
      