import socket
import struct
import asyncio
import logging
log = logging.getLogger("live-mir."+__name__)

class MetadataListenerProtocol(object):
    def __init__(self, listener):
        self.listener = listener          
            
    def connection_made (self, transport):
        self.listener.transport = transport
        
    def connection_lost (self, transport):
        pass
        
    def datagram_received (self, data, addr):
        #log.debug('Received {!r} from {!r}'.format(data, addr))
        self.listener.add_datagram(data)

class MetadataListener:
    def __init__(self, queueSize = None):
        if queueSize is None:
            queueSize = 0
        self.queue = asyncio.Queue(queueSize)
        self.transport = None
        
    def add_datagram(self, data):
        try:
            self.queue.put_nowait(data)
            #log.debug("Added. Queue depth = %s" % self.queue.qsize())
        except asyncio.QueueFull:
            log.warning ("Queue full, dropping datagram")
           
    async def receive(self):
        data = await self.queue.get()
        return data
        
    def bind_socket (self, multicastAddress, multicastPort, listenInterface):
        try:
            self.socket = socket.socket( socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.socket.bind(('', multicastPort))            
            try:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
                self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)                
            except AttributeError:
                pass
            
            group = socket.inet_aton(multicastAddress)
            mreq = struct.pack('4sL', group, listenInterface)
            self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            log.debug("Socket bound")
            
        except IOError as e:
            log.Error("Error setting up multicast socket: {}".format(e))
            

    def stop (self):
        self.transport.close()
        self.socket.close()
        self.queue.put_nowait(b"exiting")

    async def start_listener (self):
        loop = asyncio.get_event_loop()
        
        await loop.create_datagram_endpoint(lambda:MetadataListenerProtocol(self), sock = self.socket)
              
        
    
        
        



