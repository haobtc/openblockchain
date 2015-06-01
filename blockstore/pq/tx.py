from blockstore import ttypes
from block import db2t_block
from helper import get_nettype
from sqlalchemy.sql import text
from binascii import hexlify
from deserialize import extract_public_key

blkColumns = ('hash', 'height', 'version', 'prev_hash', 'mrkl_root', 'time',
              'bits', 'nonce', 'blk_size', 'work')
txColumns = ('id', 'hash', 'version', 'lock_time', 'coinbase', 'size')
txInColumns = ('q', 's', 'prev_out', 'n')
txOutColumns = ('s', 'v', 'type')


def db2t_tx(conn, dtx, db_block=None):
    t = ttypes.Tx(nettype=get_nettype(conn))
    t.hash = hexlify(dtx['hash'])
    t.version = dtx['version']

    blkid = conn.engine.execute(text(
        'select blk_id from blk_tx where tx_id=:val limit 1'),
                                val=dtx['id']).first()
    blkid = blkid[0]
    blk = conn.engine.execute(text(
        'select id,hash,height,version,prev_hash,mrkl_root,time,bits,nonce,blk_size,work from blk where id=:val limit 1'),
                              val=blkid).first()
    if blk:
        block = (dict(zip(blkColumns, blk[1:])))
        txcount = conn.engine.execute(text(
            'select count(*) from blk_tx where blk_id=:val limit 1'),
                                      val=blk[0]).first()[0]
        block['cntTxes'] = txcount
        t.block = db2t_block(conn, block)
        #t.blockIndex = index

    txinlist = conn.engine.execute(text(
        'select sequence, script_sig, prev_out, prev_out_index from txin where tx_id=:val order by tx_idx'),
                                   val=dtx['id'])
    for vin in txinlist:
        txin = {}
        inp = ttypes.TxInput()
        if dtx['coinbase']:
            txin['coinbase'] = vin[1]
        else:
            txin = dict(zip(txInColumns, vin))
            if 'hash' in txin:
                inp.hash = hexlify(txin['prev_out'])
            if 'n' in txin:
                inp.vout = txin['n']
            inp.script = txin['s']
            if 'q' in txin:
                inp.q = txin['q']

            prev_tx = conn.engine.execute(
                text('select id from tx where hash=:val limit 1'),
                val="\\x" + hexlify(txin['prev_out'][::-1])).first()
            tx_id = prev_tx[0]
            vout = conn.engine.execute(text(
                'select pk_script, value, type from txout where tx_id=%d and tx_idx=%d'
                % (tx_id, txin['n']))).first()
            prev_txout = dict(zip(txOutColumns, vout))
            txin['s'] = hexlify(txin['s'])
            txin['value'] = str(prev_txout['value'])
            txin['addr'] = extract_public_key(prev_txout['scriptPubKey'])
            inp.address = ','.join(txin['addr'])
            inp.amountSatoshi = txin['v']
        t.inputs.append(inp)

    txoutlist = conn.engine.execute(
        text('select pk_script, value, type from txout where tx_id=%d' %
             dtx['id'])).fetchall()
    for vout in txoutlist:
        txOut = dict(zip(txOutColumns, vout))
        outp = ttypes.TxOutput()
        txOut['addr'] = extract_public_key(txOut['s'])
        outp.address = ','.join(txOut['addr'])
        outp.amountSatoshi = str(txOut['v'])
        outp.script = hexlify(txOut['s'])
        t.outputs.append(outp)

    return t


def get_tx(conn, txid):
    tx = conn.engine.execute(text(
        'select id, hash, version, lock_time, coinbase, tx_size from tx where hash=:val limit 1'),
                             val=("\\x" + txid.encode('hex'))).first()
    if tx:
        dtx = dict(zip(txColumns, tx))
        return db2t_tx(conn, dtx)
    else:
      return None
