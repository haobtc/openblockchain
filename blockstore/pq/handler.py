from blockstore import ttypes
from helper import resolve_network
from block import get_block
from tx import get_tx
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

    def getTx(self, nettype, txid):
        conn = network_conn(nettype)
        dtx = get_tx(conn, txid)
        if not dtx:
            raise ttypes.NotFound()
        return dtx
