import pytz
from datetime import datetime
from blockstore import BlockStoreService, ttypes

def resolve_network(nettype):
    if nettype == ttypes.Network.BITCOIN:
        return 'bitcoin'
    elif nettype == ttypes.Network.LITECOIN:
        return 'litecoin'
    elif nettype == ttypes.Network.DOGECOIN:
        return 'dogecoin'
    elif nettype == ttypes.Network.DARKCOIN:
        return 'darkcoin'

def netname2type(netname):
    return getattr(ttypes.Network, netname.upper())

def get_netname(conn):
    s = conn.name.split('_', 1)
    return s[1]

def get_nettype(conn):
    netname = get_netname(conn)
    return netname2type(netname)

def utc_now():
    return datetime.utcnow().replace(tzinfo=pytz.utc)

def generated_seconds(gtime):
    d = utc_now() - gtime
    return d.days * 86400 + d.seconds

def fee_rate_satoshi(netname):
    if netname == 'bitcoin':
        return 10000
    elif netname == 'litecoin':
        return 100000
    elif netname == 'dogecoin':
        return 100000000
    elif netname == 'darkcoin':
        return 100000
    else:
        raise NotImplemented

def minimum_fee_satoshi(netname):
    if netname == 'bitcoin':
        return 10000
    elif netname == 'litecoin':
        return 1000
    elif netname == 'dogecoin':
        return 1000000
    elif netname == 'darkcoin':
        return 1000
    else:
        raise NotImplemented
