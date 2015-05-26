from blockstore import ttypes

from binascii import hexlify
from sqlalchemy.sql import text

blkColumns = ('hash', 'height', 'version', 'prev_hash', 'mrkl_root', 'time',
              'bits', 'nonce', 'blk_size', 'work')


def db2t_block(conn, block):
    b = {}
    b = ttypes.Block(nettype=1)
    b.hash = hexlify(block['hash'])
    b.version = block['version']
    b.prevHash = hexlify(block['prev_hash'])
    b.cntTxes = block['cntTxes']
    b.height = block['height']
    b.merkleRoot = hexlify(block['mrkl_root'])
    b.timestamp = block['time']
    b.isMain = True

    if block.get('next_hash'):
        b.nextHash = block['next_hash']
    if block.get('_id'):
        b.objId = block['_id'].binary
    if block.get('bits'):
        b.bits = block['bits']
    return b


def get_block(conn, blockHash):
    if blockHash is None:
        return None
    blk = conn.engine.execute(text(
        'select id,hash,depth,version,prev_hash,mrkl_root,time,bits,nonce,blk_size,work from blk where hash=:val limit 1'),
                              val=("\\x" + blockHash.encode('hex'))).first()
    if blk:
        block = (dict(zip(blkColumns, blk[1:])))
        txCount = conn.engine.execute(text(
            'select count(*) from blk_tx where blk_id=:val limit 1'),
                                      val=blk[0]).first()[0]
        block['cntTxes'] = txCount
        return db2t_block(conn, block)
    else:
      return None
