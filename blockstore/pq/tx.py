from blockstore import ttypes
from block import db2t_block
from helper import get_nettype
from sqlalchemy.sql import text
from binascii import hexlify
from deserialize import extract_public_key
from database import Tx, Block, BlockTx, TxIn, TxOut, engine

def db2t_tx(conn, dtx, db_block=None):
    t = ttypes.Tx(nettype=get_nettype(conn))
    t.hash = hexlify(dtx.hash)
    t.version = dtx.version

    blktx = BlockTx.query.filter(BlockTx.tx_id == dtx.id).limit(1).first()
    if blktx != None:
        blkid = blktx.blk_id
        blk = Block.query.filter(Block.id == blkid).limit(1).first()
        if blk:
            t.block = db2t_block(conn, blk)
            t.blockIndex = BlockTx.query.filter(
                BlockTx.blk_id == blkid, BlockTx.tx_id == dtx.id).first().idx

    txinlist = TxIn.query.filter(TxIn.tx_id == dtx.id).all()
    for vin in txinlist:
        inp = ttypes.TxInput()
        if dtx.coinbase:
            inp.script = vin.script_sig
        else:
            inp.hash = hexlify(vin.prev_out)
            inp.vout = vin.prev_out_index
            inp.script = vin.script_sig
            inp.q = vin.sequence

            prev_tx = Tx.query.filter(Tx.hash == vin.prev_out).first()
            if prev_tx:
                prev_txout = TxOut.query.filter(
                    TxOut.tx_id == prev_tx.id,
                    TxOut.tx_idx == vin.prev_out_index).first()
                if prev_txout:
                    inp.address = ','.join(
                        extract_public_key(prev_txout.pk_script))
                    inp.amountSatoshi = str(prev_txout.value)
        t.inputs.append(inp)

    txoutlist = TxOut.query.filter(TxOut.tx_id == dtx.id).all()
    for vout in txoutlist:
        outp = ttypes.TxOutput()
        outp.address = ','.join(extract_public_key(vout.pk_script))
        outp.amountSatoshi = str(vout.value)
        outp.script = hexlify(vout.pk_script)
        t.outputs.append(outp)

    return t


def get_tx(conn, txid):
    dtx = Tx.query.filter(Tx.hash == txid).limit(1).first()
    if dtx:
        return db2t_tx(conn, dtx)
    else:
       return None


def get_db_tx_list(conn, txids, keep_order=False):
    return [get_tx(conn, txid) for txid in txids]


def get_tx_list(conn, txids, keep_order=False):
    arr = get_db_tx_list(conn, txids, keep_order=keep_order)
    return arr


def db2t_tx_list(conn, txes):
    return [db2t_tx(conn, tx) for tx in txes]


def get_tail_tx_list(conn, n):
    n = min(n, 20)
    arr = list(Tx.query.order_by("id desc").limit(n).all())
    arr.reverse()
    return db2t_tx_list(conn, arr)


def get_tx_list_since(conn, since, n=20):
    arr = list(Tx.query.filter("id >%d and id < %d" % (
        int(since, 0), n
    )).order_by("id desc").limit(n).all())
    return db2t_tx_list(conn, arr)


def get_missing_txid_list(conn, tx_hashs):
    if not tx_hashs:
        return []
    found_set = []
    for tx_hash in tx_hashs:
        if Tx.query.filter(Tx.hash == tx_hash).limit(1).first():
            found_set.append(tx_hash)
    return list(set(tx_hashs) - set(found_set))


def send_tx(conn, stx):
    if Tx.query.filter(Tx.hash == stx.hash).limit(1).first():
        raise ttypes.AppException(
            code="tx_exist",
            message="tx already exists in the blockchain")

def get_unspent(conn, addresses):
    addr_set = set(addresses)

    utxos = []
    utxos.append(get_utxo(conn, dtx, output, i))
    res = UTXO.query.filter(UTXO.addresses in addresses).limit(10)
    for u in res:
        utxo = ttypes.UTXO(nettype=get_nettype(conn))
        utxo.address = u.addresses
        utxo.amountSatoshi = u.value
        utxo.txid = u.txout_txhash
        utxo.vout = u.tx_idx
        utxo.scriptPubKey = u.pk_script
        if u.height>0:
            tip = get_tip_block(conn)
            utxo.confirmations = tip.height - u.height + 1
            utxo.timestamp = u.time
        else:
            utxo.confirmations = 0
            utxo.timestamp = u.rev_time

        utxos.append(utxo)

    return utxos


def get_related_txid_list(conn, addresses):
    params = ''
    for address in addresses:
        params = params + "'" + address + "',"
    params = params[:-1]
    txes = engine.execute(text(
        "select txout_txhash from vout where address in (%s) limit 10"
        % params)).fetchall()
    return [hexlify(tx[0]) for tx in txes]


def get_related_tx_list(conn, addresses):
    params = ''
    for address in addresses:
        params = params + "'" + address + "',"
    params = params[:-1]
    txes = engine.execute(text(
        "select txout_tx_id from vout where address  in (%s) limit 10"
        % params)).fetchall()
    return [db2t_tx(conn, Tx.query.filter(Tx.id == tx[0]).limit(1).first())
            for tx in txes]
