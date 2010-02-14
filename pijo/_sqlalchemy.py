from concurrence.database.ext._sqlalchemy import SqlAlchemyPoolAdapter
from concurrence.database.mysql import dbapi as concurrence_dbapi
from sqlalchemy import *

# monkey patch sqlalchemy to use concurrence mysql driver
import sqlalchemy.databases.mysql as mysql
def dbapi(*args, **kwargs):
   return concurrence_dbapi
mysql.MySQLDialect.dbapi = classmethod(dbapi)
def is_disconnect(self, e):
   # we will disconnect the connection on ALL errors that occur on the database
   return True
mysql.MySQLDialect.is_disconnect = is_disconnect

from datetime import datetime
# create a concurrence database pool with sqlalchemy interface

def create_mysql_engine(username=None, password=None, database=None, hostname='localhost', port=3306, echo=False):
    pool = SqlAlchemyPoolAdapter(concurrence_dbapi, dict(user=username, passwd=password, db=database, host=hostname, port=port))
    engine = create_engine('mysql://', strategy='plain', pool=pool, echo=echo)
    return engine
    

from sqlalchemy import types
from sqlalchemy.databases.mysql import MSBinary
from sqlalchemy.schema import Column
import uuid

class UUID(types.TypeDecorator):
    impl = MSBinary
    def __init__(self):
        self.impl.length = 16
        types.TypeDecorator.__init__(self,length=self.impl.length)
 
    def process_bind_param(self,value,dialect=None):
        if value and isinstance(value,uuid.UUID):
            return value.bytes
        elif value and not isinstance(value,uuid.UUID):
            raise ValueError,'value %s is not a valid uuid.UUID' % value
        else:
            return None
 
    def process_result_value(self,value,dialect=None):
        if value:
            return uuid.UUID(bytes=value)
        else:
            return None
 
    def is_mutable(self):
        return False