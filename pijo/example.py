custom Username string {
    max_length 50;
    min_length 2;
}

custom Password string {
    max_length 50;
    min_length 2;
}

struct<User> {
    custom<Username> username;
    custom<Password> password;
    Date created;
};




rpc->server getUserByUsername {
    request {
        custom<Username> username;
        custom<Password> password;
    }
    response {
        int ids;
    }
}


Protocol UserService {
    RPC->Server create {
        string username {
            required;
            max_length(10);
            
}



# data.pijo
"""
Protocol UserService {
    RPC->Server create {
        Request {
            String username [
                
            ];
            string username {
                non_empty;
                max_length 50;
                min_length 2;
            };
            string password {
                non_empty
                max_length 50;
                min_length 10;
            };
            string email;
            string first_name;
            string last_name;
        }
        Response {
            int id;
        }
    }
    RPC->Server authenticate {
        Request {
            string username;
            string password;
        }
        Response {
            int id;
        }
    }
    RPC->Server 
    
}
"""

class pijo.DataService(object):
    protocol_file = 'data.pijo'
    
    def create(session, **kw):
        u = User(**kw)
        session.save(u)

    def authenticate(session, username, password):
        u = session.query(User).filter_by(username=username).one()
        if not u:
            raise ExpectedException("User not found")
        if not u.authenticate(password):
            raise ExpectedException("Invalid password")
        return u.id
        
    def 

