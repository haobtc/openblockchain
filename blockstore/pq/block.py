from blockstore import ttypes

from helper import get_nettype
from binascii import hexlify
from sqlalchemy.sql import text
from database import Block, BlockTx

blkColumns = ('hash', 'height', 'version', 'prev_hash', 'mrkl_root', 'time',
              'bits', 'nonce', 'blk_size', 'work')


def db2t_block(conn, block):
    b = {}
    b = ttypes.Block(nettype=get_nettype(conn))
    b.cntTxes = BlockTx.query.filter(BlockTx.blk_id==block.id).count()
    b.hash = hexlify(block.hash)
    b.version = block.version
    b.prevHash = hexlify(block.prev_hash)
    b.height = block.height
    b.merkleRoot = hexlify(block.mrkl_root)
    b.timestamp = block.time
    b.isMain = block.chain
    b.bits = block.bits

    b.objId = hex(block.id)
    block_next = Block.query.filter(Block.prev_hash==block.hash).limit(1).first()
    if block_next:
       b.nextHash = hexlify(block_next.hash)
    return b


def get_block(conn, blockHash):
    if blockHash is None:
        return None
    block = Block.query.filter(Block.hash==blockHash).limit(1).first()
    if block:
        return db2t_block(conn, block)
    else:
      return None

def get_tip_block(conn):
    block = Block.query.order_by("height desc").limit(1).first()
    if block:
       return db2t_block(conn, block)
    else:
      return None

def get_missing_block_hash_list(conn, bhashes):
    if not bhashes:
        return []
    binary_bhash_list = [Binary(bhash) for bhash in bhashes]
    hash_set = set(binary_bhash_list)
    found_set = []
    for block_hash in hash_set:
        if  Block.query.filter(Block.hash==block_hash).limit(1).first():
            found_set.append(block_hash)
    return list(hash_set - found_set)

def get_tail_block_list(conn, n):
    n = min(n, 10)
    arr = Block.query.order_by("height desc").limit(10).all()
    arr = list(arr)
    arr.reverse()
    return [db2t_block(conn, b) for b in arr]
