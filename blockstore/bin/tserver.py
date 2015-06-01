#!/usr/bin/env python

#import eventlet
#eventlet.monkey_patch()

import os
import signal
import getopt, sys

import logging
logging.basicConfig()

from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
#from thrift.server.TServer import TSimpleServer
from thrift.server.TProcessPoolServer import TProcessPoolServer
from TGEventServer import TProcessPoolGEventServer, TSimpleGEventServer, patch_thrift
from blockstore import BlockStoreService, ttypes
from pq.handler import BlockStoreHandler

patch_thrift()

def run(host='localhost', port=19090):
    handler = BlockStoreHandler()
    processor = BlockStoreService.Processor(handler)
    transport = TSocket.TServerSocket(host=host, port=port)
    tfactory = TTransport.TBufferedTransportFactory()
    pfactory = TBinaryProtocol.TBinaryProtocolFactory()

    #server = TServer.TSimpleServer(processor, transport, tfactory, pfactory)
    #server = TProcessPoolServer(processor, transport, tfactory, pfactory)
    server = TSimpleGEventServer(processor, transport, tfactory, pfactory)
    #server.setNumWorkers(2)
    server.serve()


def usage():
    print 'blockstored: thrift server for block db of bitcoin, litecoin and dogecoin'
    print 'Usage: %s [opts]' % sys.argv[0]
    print ' -h|--host <host> server host, default = "localhost"'
    print ' -p|--port <port> server port, default = 19090'
    print ' -u               print this message'
    
def main():
    # parse arguments
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'h:p:u', ['host=', 'port=', 'usage'])
    except getopt.GetoptError as err:
        print str(err)
        usage()
        sys.exit(2)
    
    kwargs = {}
    for o, a in opts:
        if o == '-h':
            kwargs['host'] = a
        elif o == '-p':
            kwargs['port'] = int(a)
        elif o == '-u':
            usage()
            sys.exit(0)
    run(**kwargs)

if __name__ == '__main__':
    main()
