import blosc
import pickle
import sys

from steam.enums.emsg import EMsg
from dota2.enums import EDOTAGCMsg as dGCMsg
from dota2.enums import ESOMsg as dEMsg
from dota2.enums import ESOType as dEType
from dota2.enums import DOTA_GameState as dGState
from dota2.enums import EMatchOutcome as dOutcome
from dota2.enums import GCConnectionStatus as dConStat
from dota2.enums import EGCBaseClientMsg as dGCbase

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