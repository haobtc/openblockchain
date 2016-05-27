#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, render_template, url_for,redirect,request,jsonify
from flask_sqlalchemy import SQLAlchemy
import simplejson as json
import binascii
from database import *
from sqlalchemy import and_
from sqlalchemy.sql import  select
from datetime import datetime
from util     import calculate_target, calculate_difficulty, decode_check_address
import re
import config
import logging

from flask.ext.cache import Cache

# logging.basicConfig(format='%(asctime)s %(message)s', filename=config.EXPLORER_API_LOG_FILE,level=logging.INFO)
# console = logging.StreamHandler()  
# console.setLevel(logging.DEBUG)  
# formatter = logging.Formatter('%(asctime)-12s: %(message)s')  
# console.setFormatter(formatter)  
# logging.getLogger('').addHandler(console) 

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)


app = Flask(__name__, static_url_path='/static')
cache = Cache(app, config={'CACHE_TYPE': 'redis', 'CACHE_KEY_PREFIX':None, 'CACHE_DEFAULT_TIMEOUT':31536000})

page_size=10

from bitcoinrpc.authproxy import AuthServiceProxy

access = AuthServiceProxy(config.RPC_URL)

def getmininginfo():
  return json.loads(access.getmininginfo())

def get_pool(pool_id):
    res = POOL.query.with_entities(POOL.name, POOL.link).filter(POOL.id==pool_id).first()
    if res != None:
        return res.name, res.link
    else:
        return 'unknown',''

@app.template_filter('datetime')
def _jinja2_filter_datetime(date):
    return datetime.utcfromtimestamp(date).ctime()

@app.template_filter('reward')
def _jinja2_filter_reward(blk):
    halvings = int(blk['height']) / 210000

    # Force block reward to zero when right shift is undefined.
    if halvings >= 64:
        return float(blk['fees'])/100000000

    # Subsidy is cut in half every 210,000 blocks which will occur approximately every 4 years.
    return float(blk['fees'])/100000000 + float(50)/(halvings+1) 

@app.template_filter('btc')
def _jinja2_filter_btc(value):
    if value=='':
       return 0

    if isinstance(value, basestring):
        value = decimal.Decimal(value)

    hold_len = 8
    fmt = '%i.%08i'
    k = 100000000

    sign = ''
    if value < 0:
        value = -value
        sign = '-'

    upv = value
    r = fmt % (upv // k, upv % k)
    r = sign + r.rstrip('0').rstrip('.')
    if r == '-0':
        r = '0'
    return r
 
@app.template_filter('target')
def _jinja2_filter_target(value):
    return calculate_target(value)

@app.template_filter('difficulty')
def _jinja2_filter_difficulty(value):
    return calculate_difficulty(value)

@app.template_filter('coinbase')
def _jinja2_filter_coinbase(value):
    try:
        return value.decode('hex').decode('ascii','replace')
    except:
        value
 
def render_404(render_type='html'):
    if render_type=='html':
        return render_template('404.html'), 404
    elif render_type=='json':
        return jsonify({"error":"Not found"}), 404

def get_tx_addresses(tx=None):

    in_addresses = []
    out_addresses = []

    if tx['removed']==True:
       in_addresses = ALL_VOUT.query.with_entities(ALL_VOUT.address, ALL_VOUT.value, ALL_VOUT.txin_tx_id, ALL_VOUT.txout_tx_hash).filter(ALL_VOUT.txin_tx_id==int(tx['id'])).order_by(ALL_VOUT.in_idx).all()
       out_addresses = ALL_VOUT.query.with_entities(ALL_VOUT.address, ALL_VOUT.value, ALL_VOUT.txin_tx_id, ALL_VOUT.txin_tx_hash).filter(ALL_VOUT.txout_tx_id==int(tx['id'])).order_by(ALL_VOUT.out_idx).all()

       return in_addresses , out_addresses

    s1 = select([STXO.address, STXO.value, STXO.txin_tx_id, STXO.txout_tx_hash, STXO.in_idx]).where(STXO.txin_tx_id == int(tx['id']))
    
    s2 = select([VTXO.address, VTXO.value, VTXO.txin_tx_id, VTXO.txout_tx_hash, VTXO.in_idx]).where(VTXO.txin_tx_id == int(tx['id']))
    
    q = s1.union(s2).alias('in_addresses')
    
    in_addresses=db_session.query(q).order_by('in_idx').all()

    s1 = select([STXO.address, STXO.value, STXO.txin_tx_id, STXO.txout_tx_hash, STXO.out_idx]).where(STXO.txout_tx_id == tx['id'])
    
    s2 = select([VTXO.address, VTXO.value, VTXO.txin_tx_id, VTXO.txout_tx_hash, VTXO.out_idx]).where(VTXO.txout_tx_id == tx['id'])
    
    q = s1.union(s2).alias('out_addresses')
    
    out_addresses=db_session.query(q).order_by('out_idx').all()
 
    return in_addresses , out_addresses
 

def lastest_data(render_type='html'):
    blks=[]
    res = Block.query.order_by(Block.height.desc()).limit(10).all()
    for blk in res:
        blk=blk.todict() 
        blks.append(blk)

    txs=[]
    res = Tx.query.filter(and_(Tx.removed==False,Tx.coinbase==False)).order_by(Tx.id.desc()).limit(5).all()
    for tx in res:
        tx= tx.todict()
        tx['in_addresses'], tx['out_addresses'] = get_tx_addresses(tx)
        if tx['recv_time'] == 0:
            tx['recv_time'] = tx['time']
        txs.append(tx)
    
    last_data={}
    last_data['blks'] = blks
    last_data['txs'] = txs
    # last_data['unconfirmed_txs'] = UTX.query.count()

    # mininginfo = getmininginfo()
    # last_data['difficulty'] = mininginfo['difficulty']
    # last_data['networkhashps'] = mininginfo['networkhashps']
    
    if render_type == 'json':
        return jsonify(last_data)

    return render_template('home.html', blks=blks,txs=txs)
 
@app.route('/')
def home():
    return lastest_data(render_type='html')

@app.route('/news')
def news():
    render_type=request.args.get('type') or 'html'
    return lastest_data(render_type)

@app.route('/checkdb')
def checkdb():
    file = open(config.DB_WARNING_FILE)
 
    for line in file:
        return line
        pass # do something
    return "checking"

    # level= request.args.get('level') or 3
    # return check_db(level)

def render_bip(bip_name=None, render_type='html'):
    blks=[]
    res = Block.query.filter(Block.bip_name==bip_name).order_by(Block.height.desc()).limit(100).all()
    for blk in res:
        blk=blk.todict() 
        blks.append(blk)
   
    last_data={}
    last_data['blks'] = blks
    
    if render_type == 'json':
        return jsonify(last_data)

    return render_template('bip.html', blks=blks)
 
@app.route('/bip/<bip_name>', methods=['GET', 'POST'])
def bip_handle(bip_name):
    render_type=request.args.get('type') or 'html'
    return render_bip(bip_name, render_type)
 

def render_pool(pool_name=None, render_type='html'):
    blks=[]
    res = Block.query.filter(Block.pool_name==pool_name).order_by(Block.height.desc()).limit(100).all()
    for blk in res:
        blk=blk.todict() 
        blks.append(blk)
   
    last_data={}
    last_data['blks'] = blks
    
    if render_type == 'json':
        return jsonify(last_data)

    return render_template('pool.html', blks=blks)
 
@app.route('/pool/<pool_name>', methods=['GET', 'POST'])
def pool_handle(pool_name):
    render_type=request.args.get('type') or 'html'
    return render_pool(pool_name, render_type)
 
def render_tx(txHash=None):
 
    tx = JsonCache.query.filter(JsonCache.key == txHash).first()
    #tx=cache.get(key=txHash)
    if tx !=None:
        tx = tx.val
        tx = json.loads(tx)
    else:
        try:
            txHash = txHash.decode('hex')
        except:
            return None

        tx = Tx.query.filter(Tx.hash == txHash).first()
        if tx==None:
           return None
        tx= tx.todict()

        txins = TxIn.query.filter(TxIn.tx_id==tx['id']).order_by(TxIn.tx_idx.asc()).all()
        tx['vin'] = [txin.todict() for txin in txins ]
        txouts = TxOut.query.filter(TxOut.tx_id==tx['id']).order_by(TxOut.tx_idx.asc()).all()
        tx['vout'] = [txout.todict() for txout in txouts]
        tx['in_addresses'], tx['out_addresses'] = get_tx_addresses(tx)
   
    confirm = db_session.execute('select get_confirm(%d)' % tx['id']).first()[0];
    if confirm ==None:
        tx['confirm'] = 0
        for vin in tx['vin']:
            if int(vin['sequence']) < 4294967294:
               continue
            else:
               break
            tx['rbf'] = True
    else:
        tx['confirm'] = confirm

    return tx

@app.route('/tx/<txHash>', methods=['GET', 'POST'])
def tx_handle(txHash,tx=None):

    render_type=request.args.get('type') or 'html'
 
    tx=render_tx(txHash)
    if tx==None:
        return render_404(render_type)

    if render_type == 'json':
        return jsonify(tx)
    else:
        return render_template("tx.html",tx=tx)

def render_blk(blkHash=None,  page=1):

    if page==1:
        blk=cache.get(key=blkHash)
        if blk !=None:
            return json.loads(blk)

    try:
        blkHash = blkHash.decode('hex')
    except:
        return None
 
    blk = Block.query.filter(Block.hash == blkHash).first()

    if blk==None:
       return None

    blk = blk.todict()

    total_page = blk['tx_count']/page_size
    if blk['tx_count']%page_size:
        total_page+=1
    blk['total_page'] = total_page

    page =int(page)
    if page <1:
        page = 1
    if page > total_page:
        page = total_page

    blk['page'] = page

    res = BlockTx.query.with_entities(BlockTx.tx_id).filter(BlockTx.blk_id == blk['id']).order_by(BlockTx.idx).offset((page-1)*page_size).limit(page_size)
    if res!= None:
        txs=[]
        for txid in res:
           res = Tx.query.filter(Tx.id==txid).first()
           tx= res.todict()
           tx['in_addresses'], tx['out_addresses'] = get_tx_addresses(tx)
           txs.append(tx)
    blk['txs']=txs

    res = Block.query.with_entities(Block.hash).filter(Block.height == (int(blk['height'])+1)).first()
    if res!= None:
        blk['nextblockhash']=res[0]

    return blk


@app.route('/height/<height>', methods=['GET', 'POST'])
def blkheight_handle(height=0):
    render_type=request.args.get('type') or 'html'
    page= request.args.get('page') or 1

    try:
       height=int(height)
    except:
       return render_404(render_type)
 
    blk = Block.query.filter(Block.height == height).first()
    if blk== None:
        return render_404(render_type)

    blk = render_blk(blk.hash, page)

    if blk== None:
        return render_404(render_type)

    if render_type == 'json':
        return jsonify(blk)

    return render_template("blk.html",blk=blk, page=page)
 

@app.route('/blk/<blkHash>', methods=['GET', 'POST'])
def blk_handle(blkHash, blk=None):
    render_type=request.args.get('type') or 'html'
    page= request.args.get('page') or 1

    blk = render_blk(blkHash,page)

    if blk== None:
        return render_404(render_type)

    if render_type == 'json':
        return jsonify(blk)

    return render_template("blk.html",blk=blk, page=page)

def confirm(txs): 
     return txs['confirm'] 

def get_addresses_spent_tx(addr_id=None, page=1, page_size=10, desc=True):

    in_addresses = []
    out_addresses = []

    s1 = select([STXO.txin_tx_id]).where(STXO.addr_id == addr_id)
    s2 = select([VTXO.txin_tx_id]).where(VTXO.addr_id == addr_id)
    
    q = s1.union(s2).alias('spent_btc')
    
    spent_tx=db_session.query(q).order_by('txin_tx_id').desc().offset((page-1)*page_size).limit(page_size) 

def get_addresses_unspent_tx(addr_id=None, page=1, page_size=10, desc=True):

    s1 = select([UTXO.txout_tx_id]).where(UTXO.addr_id == addr_id)
    
    q = s1.alias('unspent_btc')
    
    return db_session.query(q).order_by('txout_tx_id').desc().offset((page-1)*page_size).limit(page_size) 

def get_addresses_recv_tx(addr_id=None, page=1, page_size=10, desc=True):

    s1 = select([VOUT.txout_tx_id]).where(VOUT.addr_id == addr_id)
    
    q = s1.alias('receive_btc')

    if desc:
        return db_session.query(q).order_by('txout_tx_id').desc().offset((page-1)*page_size).limit(page_size) 
    else:
        return db_session.query(q).order_by('txout_tx_id').asc().offset((page-1)*page_size).limit(page_size) 

def get_addresses_unconfirmed_btc(addr_id=None, page=1, page_size=10, desc=True):
 
    s1 = select([UTXO.txout_tx_id]).where(UTXO.addr_id == addr_id)
    q = s1.alias('unconfirmed_btc')
    return db_session.query(q).order_by('txout_tx_id').desc().offset((page-1)*page_size).limit(page_size) 

def get_addresses_confirmed_btc(addr_id=None, page=1, page_size=10, desc=True):
 
    s1 = select([UTXO.txout_tx_id]).where(UTXO.addr_id == addr_id)
    q = s1.alias('confirmed_btc')
    return db_session.query(q).order_by('txout_tx_id').desc().offset((page-1)*page_size).limit(page_size) 
 
def render_addr(address=None, page=1, render_type='html', filter=0):
    addr = Addr.query.filter(Addr.address == address).first()
    if addr == None:
        ver,hash160=decode_check_address(address)
        if hash160==None or (ver !='\x00' and ver != '\x05'):
            return render_404(render_type)
        else:
            addr = {}
            addr['hash160'] = ''
            addr['txs']=[]
            addr['txs_len']= 0
            addr['page_size'] = 0
            addr['address']=address
            addr['total_page'] = 0
            addr['tx_count']=0
            addr['page'] = 0
            addr['recv_value'] = 0
            addr['spent_value'] = 0
            addr['balance'] = 0
            addr['group_id']    = 0
            addr['wallet_name'] = ''
            addr['wallet_link'] = ''

        if render_type == 'json':
            return jsonify(addr)

        return render_template("addr.html", addr=addr,page=page)
 

    addr=addr.todict()
    if addr['balance']<0:
        addr['balance'] = 0
       
    addr['tx_count']=AddrTx.query.filter(AddrTx.addr_id==int(addr["id"])).count();
    total_page = addr['tx_count']/page_size
    if addr['tx_count']%page_size:
        total_page+=1
    addr['total_page'] = total_page

    page =int(page)
    if page <1:
        page = 1

    addr['page'] = page

    txs=[]
    txids=[]
    txout_tx_ids =[]
    txin_tx_ids = []
    txidlist=None
    if filter==0:   #all
        txidlist = AddrTx.query.with_entities(AddrTx.tx_id).filter(AddrTx.addr_id==int(addr["id"])).order_by(AddrTx.tx_id.desc()).offset((page-1)*page_size).limit(page_size)
    elif filter==1: #spent
        txidlist = get_addresses_spent_tx(int(addr['id']), page, page_size, desc=True)
    elif filter==2: #recv
        txidlist = get_addresses_recv_tx(int(addr['id']), page, page_size, desc=True)
    elif filter==3: #utxo
        txidlist = get_addresses_unspent_tx(int(addr['id']), page, page_size, desc=True)
    elif filter==4: #unconfirm
        txidlist =  AddrTxUC.query.with_entities(AddrTx.tx_id).filter(AddrTx.addr_id==int(addr["id"])).order_by(AddrTx.tx_id.desc()).offset((page-1)*page_size).limit(page_size)
    elif filter==5: #confirm
        txidlist = AddrTxC.query.with_entities(AddrTx.tx_id).filter(AddrTx.addr_id==int(addr["id"])).order_by(AddrTx.tx_id.desc()).offset((page-1)*page_size).limit(page_size)
    else:
        return render_404(render_type)

    if txidlist==None:
        return render_404(render_type)

    in_value = 0 
    out_value = 0 
    for txid in txidlist:
        tx_in_value = 0 
        tx_out_value = 0 

        txid=txid[0]
        res = Tx.query.filter(Tx.id==txid).first()
        tx= res.todict()

        txins, txouts = get_tx_addresses(tx)
        for vin in txins:
            if vin.address==address:
                tx_in_value = tx_in_value - vin.value
                in_value = in_value - vin.value
        tx['vin'] = txins

        for vout in txouts:
            if vout.address==address:
                tx_out_value = tx_out_value + vout.value
                out_value = out_value + vout.value
        tx['vout'] = txouts

        tx['confirm'] = db_session.execute('select get_confirm(%d)' % tx['id']).first()[0];
        tx['spent']= tx_in_value + tx_out_value
        txs.append(tx)
    
    addr['txs']=txs
    addr['txs_len']=len(txs)
    addr['page_size'] =page_size
    addr['address']=address

    if render_type == 'json':
        return jsonify(addr)

    return render_template("addr.html", addr=addr,page=page)

@app.route('/addr/<address>', methods=['GET', 'POST'])
def address_handle(address):
    render_type=request.args.get('type') or 'html'
    page= request.args.get('page') or 1
    filter= request.args.get('filter') or 0

    return render_addr(address, page, render_type, int(filter))

def render_wallet(wallet_id=0, page=1, render_type='html'):
    wallet = {}
    page =int(page)
    wallet['wallet_id'] = int(wallet_id)
    addr_list = Addr.query.filter(Addr.group_id== wallet_id).offset((page-1)*page_size).limit(page_size)
    if addr_list == None:
       return render_404(render_type)

    wallet['addresses'] = addr_list 
    res = AddrTag.query.with_entities(AddrTag.name,AddrTag.link).filter(AddrTag.id == wallet_id).first()
    if res !=None:
        wallet['name'], wallet['link'] = res.name, res.link
    else:
        wallet['name'], wallet['link'] = wallet_id, wallet_id
 
    if render_type == 'json':
        return jsonify(wallet)

    return render_template("wallet.html", wallet=wallet,page=page)
 
@app.route('/wallet/<wallet_id>', methods=['GET', 'POST'])
def wallet_handle(wallet_id=0):
    render_type=request.args.get('type') or 'html'
    page= request.args.get('page') or 1
    return render_wallet(wallet_id, page, render_type)

@app.route('/search', methods=['GET', 'POST'])
def search(sid=0):
    sid = request.args.get('sid') or sid
    render_type=request.args.get('type') or 'html'

    sid.strip()
    slen = len(sid)
    if slen == 64:
        #should be tx hash or blk hash
        try:
            hashHex = sid.decode('hex')
        except:
            return render_404(render_type)
     
        blk = Block.query.filter(Block.hash == hashHex).first()
        if blk!=None:
            blk = render_blk(sid, 1)
            if blk!=None:
                 if render_type == 'json':
                     return jsonify(blk)
                 return render_template("blk.html",blk=blk, page=1)
        else:
            tx=render_tx(sid)
            if tx!=None:
               if render_type == 'json':
                   return jsonify(tx)
               else:
                   return render_template("tx.html",tx=tx)
            return render_404(render_type)
    elif slen <= 34 and slen >=26:
        addr = sid
        return render_addr(addr,1, render_type)
    elif slen <9:
        #as blk height
        blk = Block.query.filter(Block.height == int(sid)).first()
        if blk== None:
            return render_404(render_type)

        blk = render_blk(blk.hash, 1)
        if blk!=None:
             if render_type == 'json':
                 return jsonify(blk)
             return render_template("blk.html",blk=blk, page=1)
    else:
        return render_404(render_type)

if __name__ == '__main__':
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
