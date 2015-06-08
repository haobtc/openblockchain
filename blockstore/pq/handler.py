from blockstore import ttypes
from helper import resolve_network
from block import get_block, get_tip_block, get_missing_block_hash_list, get_tail_block_list

from tx import get_tx, get_tx_list, get_missing_txid_list
from tx import get_tail_tx_list, get_tx_list_since
from tx import get_related_txid_list, get_related_tx_list

import database


def network_conn(nettype):
    netname = resolve_network(nettype)
    conn = database.database(netname)
    conn.nettype = nettype
    return conn


class BlockStoreHandler:
    def getBlock(self, nettype, blockhash):
        conn = network_conn(nettype)
        block = get_block(conn, blockhash)
        if not block:
            raise ttypes.NotFound()
        return block

    def getTipBlock(self, nettype):
        conn = network_conn(nettype)
        block = get_tip_block(conn)
        if not block:
            raise ttypes.NotFound();
        return block

    def getTx(self, nettype, txid):
        conn = network_conn(nettype)
        dtx = get_tx(conn, txid)
        if not dtx:
            raise ttypes.NotFound()
        return dtx

    def getTailBlockList(self, nettype, n):
        conn = network_conn(nettype)
        return get_tail_block_list(conn, n)

    def getTxList(self, nettype, txids):
        conn = network_conn(nettype)
        return get_tx_list(conn, txids, keep_order=True)

    def getTxListSince(self, nettype, since, n):
        conn = network_conn(nettype)
        return get_tx_list_since(conn, since, n)

    def getTailTxList(self, nettype, n):
        conn = network_conn(nettype)
        return get_tail_tx_list(conn, n)

    def getRelatedTxIdList(self, nettype, addresses):
        conn = network_conn(nettype)
        return get_related_txid_list(conn, addresses)

    def getRelatedTxList(self, nettype, addresses):
        conn = network_conn(nettype)
        return get_related_tx_list(conn, addresses)

    def getUnspent(self, nettype, addresses):
        conn = network_conn(nettype)
        return get_unspent(conn, addresses)

    def getMissingTxIdList(self, nettype, txids):
        conn = network_conn(nettype)
        return get_missing_txid_list(conn, txids)

    def sendTx(self, nettype, stx):
        conn = network_conn(nettype)
        return send_tx(conn, stx)
