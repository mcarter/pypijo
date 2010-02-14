from concurrence import dispatch, Tasklet, Message
from concurrence.io import Server, BufferedStream
import server
import logging
logging.basicConfig()

class TestImplementation(object):
    def __init__(self, server):
        self.server = server
        
    def echo(self, conn, msg):
      return [ "Echo", msg ]



def main():
    s = server.PijoServer('echo.pijo', 'Echo', TestImplementation)
    print "Listening@5555"
    Server.serve(('', 5555), s)
    
if __name__ == "__main__":
    dispatch(main)
