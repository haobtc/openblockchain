import sys

sys.path.append('gen-py')

from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

from blockstore import BlockStoreService, ttypes
from blockstore.ttypes import *

transport = TSocket.TSocket('127.0.0.1', 19090)
transport = TTransport.TBufferedTransport(transport)

# Wrap in a protocol
protocol = TBinaryProtocol.TBinaryProtocol(transport)

# Create a client to use the protocol encoder
c = BlockStoreService.Client(protocol)
transport.open()

if True:
    txid = '4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b'.decode('hex')
    tx = c.getTx(ttypes.Network.BITCOIN, txid)
    print repr(tx.hash)
    for input in tx.inputs:
        print repr(input.hash)

    #r = c.verifyTx(ttypes.Network.BITCOIN, tx)
    #print 'verified', r

    blockid = '000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f'.decode('hex')
    b = c.getBlock(ttypes.Network.BITCOIN, blockid)
    print b
    exit(0)
    print c.verifyBlock(ttypes.Network.BITCOIN, b)


    r = c.getTipBlock(ttypes.Network.BITCOIN)
    print 'tip', r

    arr = c.getMissingTxIdList(ttypes.Network.BITCOIN, [txid, txid1])
    print 'missing', arr


    # txid = '64a9a0935f50a809b6889f30957c50d4ed5385d4a99e2493118ac5c6fab31b46'.decode('hex')
    # raw = '01000000016ee90b9b6ba5b0da2c60ce58d8d746ecbe267ab722ab4fb048804215f6cc99d5000000006c493046022100b21bba899b0abf882e889006412b26a06d46ce8902a2776a24610ea2ad05be080221008a601e13741eb0bf6ca481513b253f3b29c6f2ec4912a790a38190a4e9493402012103732f4c7ff7b527cfe3cbe8664cb55f6d01067da8212e2486cebff959576f0eefffffffff02c075113b000000001976a914c2784d5ce96b1c23bcb86fcb0fc9a3590cd489ec88ac30c1be77000000001976a9140cb6c275be7f179883bb821ef1dfd6b520fc656988ac00000000'.decode('hex')

    # s = ttypes.SendTx(txid=txid, raw=raw)
    # print c.sendTx(ttypes.Network.BITCOIN, s)

    print c.getRelatedTxList(ttypes.Network.DOGECOIN, ['DTHH6Su9fdx5vMEc6abpFRxZrUTP2MbAq5'])

    blockid1 = '000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce267'.decode('hex')
    print c.getMissingInvList(ttypes.Network.BITCOIN, [ttypes.Inventory(type=ttypes.InvType.BLOCK, hash=blockid), ttypes.Inventory(type=ttypes.InvType.BLOCK, hash=blockid1), ttypes.Inventory(type=ttypes.InvType.TX, hash=txid), ttypes.Inventory(type=ttypes.InvType.TX, hash=txid1)])

if False:
    print c.pushPeers(ttypes.Network.BITCOIN, ['192.168.6.8:9000', '192.168.3.2:8888'])
    print c.popPeers(ttypes.Network.BITCOIN, 3)
