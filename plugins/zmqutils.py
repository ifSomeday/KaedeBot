import blosc
import pickle
import sys

def sendObjRouter(socket, ident, obj, flags=0, protocol=-1):
    p = pickle.dumps(obj, protocol=protocol)
    b = blosc.compress(p)
    return(socket.send_multipart([ident, b], flags=flags))

def sendObjDealer(socket, obj, flags=0, protocol=-1):
    p = pickle.dumps(obj, protocol=protocol)
    b = blosc.compress(p)
    return(socket.send(b, flags=flags))    

def recvObjRouter(socket, flags=0, protocol=-1):
    ident, b = socket.recv_multipart(flags=flags)
    p = blosc.decompress(b)
    return(ident, pickle.loads(p))
    
def recvObjDealer(socket, flags=0, protocol=-1):
    b = socket.recv(flags=flags)
    p = blosc.decompress(b)
    return(pickle.loads(p))