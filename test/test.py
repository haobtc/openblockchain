#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os 
import sys
import simplejson as json
import binascii
import plyvel
from BCDataStream import *
from deserialize import *
from util import double_sha256

import requests
from database import *
from sqlalchemy import and_

datadir = '~/.bitcoin' #bitcoin data directory
verifystatics =False

def _open_blkindex(datadir):
  try:
    db=plyvel.DB(os.path.join(datadir, 'blocks', 'index'),compression=None)
  except:
    logging.error("Couldn't open blocks/index.  Try quitting any running Bitcoin apps.")
    sys.exit(1)
  return db
 
db = _open_blkindex(datadir)

def _dump_tx(datadir, tx_hash, tx_pos):
  BLOCK_HEADER_SIZE = 80
  blockfile = open(os.path.join(datadir, "blocks","blk%05d.dat"%(tx_pos[0],)), "rb")
  ds = BCDataStream()
  ds.map_file(blockfile, tx_pos[1]+BLOCK_HEADER_SIZE+tx_pos[2])
  tx = parse_Transaction(ds)
  tx['hash'] = tx_hash[::-1]
  ds.close_file()
  blockfile.close()
  return tx

def _read_CDiskTxPos(stream):
  n_file = stream.read_var_int()
  n_block_pos = stream.read_var_int()
  n_tx_pos = stream.read_var_int()
  return (n_file, n_block_pos, n_tx_pos)
 
def _read_tx(db, txhash):
  kds = BCDataStream()
  vds = BCDataStream()

  key_prefix = "t"+txhash
  cursor = db.iterator(prefix=key_prefix)
  (key, value) = cursor.next()
  kds.clear(); kds.write(key)
  vds.clear(); vds.write(value)

  kds.read_bytes(1)
  hash256 = (kds.read_bytes(32))
  tx_pos = _read_CDiskTxPos(vds)
  return _dump_tx(datadir, hash256, tx_pos)
 

def read_tx(txhash):
   return _read_tx(db, txhash)
   
def _parse_block_index(vds):
  d = {}
  d['version'] = vds.read_var_int()
  d['nHeight'] = vds.read_var_int()
  d['nStatus'] = vds.read_var_int()
  d['nTx'] = vds.read_var_int()
  d['nFile'] = vds.read_var_int()
  d['nBlockPos'] = vds.read_var_int()
  d['nUndoPos'] = vds.read_var_int()

  header_start = vds.read_cursor
  d['b_version'] = vds.read_int32()
  d['hashPrev'] = vds.read_bytes(32)
  d['hashMerkle'] = vds.read_bytes(32)
  d['nTime'] = vds.read_var_int()
  d['nBits'] = vds.read_int32()
  d['nNonce'] = vds.read_int32()
  header_end = vds.read_cursor
  d['__header__'] = vds.input[header_start:header_end]
  return d

def _dump_block(datadir, nFile, nBlockPos, blkhash):
  blockfile = open(os.path.join(datadir,"blocks","blk%05d.dat"%(nFile,)), "rb")
  ds = BCDataStream()
  ds.map_file(blockfile, nBlockPos)
  block_start = ds.read_cursor
  block = parse_Block(ds)
  block_end = ds.read_cursor
  block['blk_size'] = (block_end - block_start)
  ds.close_file()
  blockfile.close()
  return block
 

def _read_block(db, blkhash):
  key_prefix = "b"+(blkhash.decode('hex_codec')[::-1])
  cursor = db.iterator(prefix=key_prefix)
  (key, value) = cursor.next()
  vds = BCDataStream()
  vds.clear(); vds.write(value)
  block_data = _parse_block_index(vds)
  block = _dump_block(datadir, block_data['nFile'], block_data['nBlockPos'], blkhash)
  block['hash256'] = blkhash
  block['nHeight'] = block_data['nHeight']
  return block

def read_block(blkhash):
  return _read_block(db, blkhash)

def verifyTxIn(txin1, txin2, coinbase):  

    assert txin1.tx_idx         == txin2['tx_idx']
    #assert txin1.sequence       == txin2['sequence']
    assert txin1.script_sig     == txin2['scriptSig']
    if not coinbase:
        assert txin1.prev_out_index == txin2['prevout_n']
        assert txin1.prev_out       == txin2['prevout_hash'][::-1]

def verifyTxOut(txout1,  txout2):  

    assert txout1.tx_idx    == txout2['tx_idx']
    assert txout1.pk_script == txout2['scriptPubKey']
    assert txout1.value     == txout2['value']
    assert txout1.type      == txout2['scripttype']

def verifyTx(txhash, coinbase):  
    tx1 = Tx.query.filter(Tx.hash == txhash.decode('hex')).first()
    txhash=txhash.decode('hex_codec')[::-1]
    tx2 = read_tx(txhash)
    
    assert tx1.hash      == tx2['hash']
    assert tx1.version   == tx2['version'] 
    assert tx1.lock_time == tx2['lockTime'] 
    assert tx1.tx_size   == len(tx2['__data__'])

    assert tx1.in_count  == len(tx2['txIn'])
    assert tx1.out_count == len(tx2['txOut'])
    assert tx1.coinbase  == coinbase

    invalue = 0
    for i, txin2 in enumerate(tx2['txIn']):
        txin1 = TxIn.query.filter(and_(TxIn.tx_id == tx1.id, TxIn.tx_idx==i)).first()
        txin2['tx_idx'] = i
        verifyTxIn(txin1, txin2, coinbase)
        prevtx = read_tx(txin2['prevout_hash'])
        invalue += prevtx['txOut'][txin2['prevout_n']]['value'] 
         
    outvalue = 0
    for j, txout2 in enumerate(tx2['txOut']):
        txout1 = TxOut.query.filter(and_(TxOut.tx_id == tx1.id, TxOut.tx_idx==j)).first()
        txout2['tx_idx'] = j
        verifyTxOut(txout1, txout2)
        outvalue += txout2['value']

    assert tx1.out_value == outvalue
    assert tx1.in_value  == invalue
    assert tx1.fee       == (invalue-outvalue)
    return tx1

def verifyBlkTx(tx2,blkid, idx,coinbase):  
    blktx = BlockTx.query.filter(and_(BlockTx.blk_id==blkid, BlockTx.idx==idx)).first()
    tx1 = Tx.query.filter(Tx.id==blktx.tx_id).first()
    
    assert tx1.hash      == double_sha256(tx2['__data__'])[::-1]
    assert tx1.version   == tx2['version'] 
    assert tx1.lock_time == tx2['lockTime'] 
    assert tx1.tx_size   == len(tx2['__data__'])

    assert tx1.in_count  == len(tx2['txIn'])
    assert tx1.out_count == len(tx2['txOut'])
    assert tx1.coinbase  == coinbase

    invalue = 0
    for i, txin2 in enumerate(tx2['txIn']):
        txin1 = TxIn.query.filter(and_(TxIn.tx_id == tx1.id, TxIn.tx_idx==i)).first()
        txin2['tx_idx'] = i
        verifyTxIn(txin1, txin2,coinbase)
        if not coinbase:
            prevtx = read_tx(txin2['prevout_hash'])
            invalue += prevtx['txOut'][txin2['prevout_n']]['value'] 
         
    outvalue = 0
    for j, txout2 in enumerate(tx2['txOut']):
        txout1 = TxOut.query.filter(and_(TxOut.tx_id == tx1.id, TxOut.tx_idx==j)).first()
        txout2['tx_idx'] = j
        verifyTxOut(txout1, txout2)
        outvalue += txout2['value']

    assert tx1.out_value == outvalue
    assert tx1.in_value  == invalue
    if not coinbase:
        assert tx1.fee       == (invalue-outvalue)
    return tx1
 
 
def verifyBlk(blkhash):  

    blk1 = Block.query.filter(Block.hash == blkhash.decode('hex')).first()
    blk2 = read_block(blkhash)
    
    assert blk1.hash            == blk2['hash256'].decode('hex')
    assert blk1.height          == blk2['nHeight']
    assert blk1.version         == blk2['version']
    assert blk1.prev_hash       == blk2['hashPrev'][::-1]
    assert blk1.mrkl_root       == blk2['hashMerkleRoot'][::-1]
    assert blk1.time            == blk2['nTime']
    assert blk1.bits            == blk2['nBits']
    assert blk1.nonce           == blk2['nNonce']
    assert blk1.blk_size        == blk2['blk_size']

    total_in_count  = 0
    total_in_value  = 0
    fees            = 0
    total_out_count = 0
    total_out_value = 0
    tx_count        = 0

    for i,tx in enumerate(blk2['transactions']):
        tx1 = verifyBlkTx(tx,blk1.id,i, i==0)
        total_in_count  +=tx1.in_count
        total_in_value  +=tx1.in_value
        fees            +=tx1.fee
        total_out_count +=tx1.out_count
        total_out_value +=tx1.out_value
        tx_count        +=1

    #assert blk1.work            == blk2['work']
    assert blk1.total_in_count  == total_in_count  
    assert blk1.total_in_value  == total_in_value  
    assert blk1.fees            == fees            
    assert blk1.total_out_count == total_out_count 
    assert blk1.total_out_value == total_out_value 
    assert blk1.tx_count        == tx_count        

def get_addr_info_blockchain(address):
    result = requests.get('https://blockchain.info/zh-cn/address/%s?format=json' % address, verify=False)
    return json.loads(result.content)

def get_addr_info_blockmeta(address):
    result = requests.get('http://blockmeta.com/api/v1/address/info/%s' % address)
    return json.loads(result.content)['data'][0]

def verifyAddr(address):  

    addr1 = get_addr_info_blockchain(address)
    addr2 = Addr.query.filter(Addr.address == address).first()

    assert addr2.address == addr1['address']
    assert addr2.hash160 == addr1['hash160']
    assert addr2.balance == int(addr1['final_balance'])

verifyBlk('000000000000000007b66b3ca329af38380bfd6bed9df8f3fa14d74ddee8d3dc')
verifyTx('aeca55bbeb9495e50500fefcd1e80d4c4aa592f5c277a2a859494ae4b06818a4',False)

verifyAddr('1AytLgGSigqiMGYyy4ces7rSHm7hgCJTv2')
verifyAddr('1dice8EMZmqKvrGE4Qc9bUFf9PX3xaYDp')
verifyAddr('1LuckyR1fFHEsXYyx5QK4UFzv3PEAepPMK')
verifyAddr('1dice9wcMu5hLF4g81u8nioL5mmSHTApw')
verifyAddr('1dice7fUkz5h4z2wPc1wLMPWgB5mDwKDx')
verifyAddr('1dice7W2AicHosf5EL3GFDUVga7TgtPFn')
verifyAddr('1dice6YgEVBf88erBFra9BHf6ZMoyvG88')
verifyAddr('1LuckyG4tMMZf64j6ea7JhCz7sDpk6vdcS')
verifyAddr('1diceDCd27Cc22HV3qPNZKwGnZ8QwhLTc')
verifyAddr('1dice5wwEZT2u6ESAdUGG6MHgCpbQqZiy')
verifyAddr('1dice7EYzJag7SxkdKXLr8Jn14WUb3Cf1')
verifyAddr('1dice1e6pdhLzzWQq7yMidf6j8eAg7pkY')
verifyAddr('1Bd5wrFxHYRkk4UCFttcPNMYzqJnQKfXUE')
verifyAddr('1NDpZ2wyFekVezssSXv2tmQgmxcoHMUJ7u')
verifyAddr('15fXdTyFL1p53qQ8NkrjBqPUbPWvWmZ3G9')
verifyAddr('1J4yuJFqozxLWTvnExR4Xxe9W4B89kaukY')
verifyAddr('14719bzrTyMvEPcr7ouv9R8utncL9fKJyf')
verifyAddr('18uvwkMJsg9cxFEd1QDFgQpoeXWmmSnqSs')
verifyAddr('1Bqm5MDo82m1FTxV3qYNUUEKnESPRhk9jd')
verifyAddr('13h1DP2Boo9TAsenphroACxhNy7pGxDYXd')
verifyAddr('1HVpyjYEPwQhvRQ3dL8tGe9kiydti616sX')
verifyAddr('1HjDauL2kth6KJUz5vX198Nvp1xN1hgYRb')
verifyAddr('1MSzmVTBaaSpKDARK3VGvP8v7aCtwZ9zbw')
verifyAddr('1GoK6fv4tZKXFiWL9NuHiwcwsi8JAFiwGK')
verifyAddr('13HFqPr9Ceh2aBvcjxNdUycHuFG7PReGH4')
verifyAddr('17NKcZNXqAbxWsTwB1UJHjc9mQG3yjGALA')
verifyAddr('1L4EThM6x3Rd2PjNbs1U136FpMq4Gmo3fJ')
verifyAddr('14ChPPM8rPYJeHnw6kMVUDnNNKx1KnjYW4')
verifyAddr('1DpsR91YmHUDTtiuH1pPCuG3RqAkmg6YKB')
verifyAddr('1AdN2my8NxvGcisPGYeQTAKdWJuUzNkQxG')
verifyAddr('1PeohaRGaTF8cSzDqP1yYfzDah66xiriEQ')
verifyAddr('1HZHBnH2FbHNWieMxAh4xBPfgfuxW15UPt')
verifyAddr('1JmcV7G3r8k7ev2EkS84MmsvxGyhiRGP84')
verifyAddr('18czPiA9PcCs7rFTBZnhvNAWuh1pEZRpGJ')
verifyAddr('1MPerpQzTABa1K2eXQxsQTDSZtDQHWf6vk')
verifyAddr('18XSLnBZ8ydMUkaifU6sQBMJzmm7JvDeUp')
verifyAddr('12Cf6nCcRtKERh9cQm3Z29c9MWvQuFSxvT')
verifyAddr('1dice6DPtUMBpWgv8i4pG8HMjXv9qDJWN')
verifyAddr('1Bet32kBtZzXViMs1PQHninHs4LADhCwtB')
verifyAddr('1dicec9k7KpmQaA8Uc8aCCxfWnwEWzpXE')
verifyAddr('1Fi57hAqyYYwaQVdA7a9qSKfiukBbt31G3')
verifyAddr('1dicegEArYHgbwQZhvr5G9Ah2s7SFuW1y')
verifyAddr('1changemCPo732F6oYUyhbyGtFcNVjprq')
verifyAddr('1HWqsgnSd12Gv8SpoUMi1Cj8hp79BTSpW7')
verifyAddr('1bonesF1NYidcd5veLqy1RZgF4mpYJWXZ')
verifyAddr('1Bet5o5o23jaRB9kKNxqZ5KeBqoSm5Fh56')
verifyAddr('1dice6wBxymYi3t94heUAG6MpG5eceLG1')
verifyAddr('1dice6GV5Rz2iaifPvX7RMjfhaNPC8SXH')
verifyAddr('1dice4J1mFEvVuFqD14HzdViHFGi9h4Pp')
verifyAddr('17qq5A3XKfrxpJRSC5LH6APjvTDb9hTmma')
verifyAddr('14gZfnEn8Xd3ofkjr5s7rKoC3bi8J4Yfyy')
verifyAddr('19ngVyAav9JLE6gVfeQB6zgHEpTZhxJ2qJ')
verifyAddr('1KyYkZ8wJ7ybvGWxSuZqsm6FuthsALSXq5')
verifyAddr('1PG1DB6uKdT9uwPBooAjRsNyewmrDrteMT')
verifyAddr('15tvWYtQq8A4m6N1QGLLADfaLA8C1mKCZv')
verifyAddr('13ARRimWwGhXt7ozfRy6PTyZcyWxhmM1Gp')
verifyAddr('13c7aMAEoS1QkwK49GctvEE7ZBkSfvaXCo')
verifyAddr('1HZK8q2RhY718CZee51D5v7xtiHp9T92pN')
verifyAddr('1PU4vjyEnMTVCmcoAZgVKFByTzbEnEryaX')
verifyAddr('1Sb9oSA4bkm7GxPWzubRKtqc4pFa1pf3D')
verifyAddr('1MtPYAjqohLH5gMq3PH5xKVFWWDxrRQEbh')
verifyAddr('15svFBR3qDuXoqTR3J2CQAiizNaE4v9CAG')
verifyAddr('1EekHaBpdaxAFTyYLWApegYWPoBBcgknon')
verifyAddr('1MBtmmai5T9kx5LxhkDPCybWXBLaYagFHu')
verifyAddr('126vMmY1fyznpZiFTTnty3cm1Rw8wuheev')
verifyAddr('19NmcoeHo2qwEFjQdUrbGuk34SU2fgfDeg')
verifyAddr('12K5SyY2Z3DNsqFtTCnyGC3J7jYTCjM54m')
verifyAddr('1J15UnwBV2uQtgPpEcmaaEbysqtNBCqMGQ')
verifyAddr('186pHM1up927B9MC27aaics6B8W7bfVpQn')
verifyAddr('1KJTGpNzYsFibLmq9WaTGAXQbhRFUgnG3z')
verifyAddr('1MW2LCfz7bvFZJG88QTeC3a1cUHLSbS2ty')
verifyAddr('198bLhyREhk2u94F5TnD8E8edbAEqEhPjE')
verifyAddr('15pWzRf8tkKNLbDxsqGVySXfMM2vz5yuo5')
verifyAddr('14uDeJYMp3Fr2Wm7biCvwqmf6To8rLt3hJ')
verifyAddr('1JceroDThChGfsfTC2ZbGjafPQoFm5mZbF')
verifyAddr('1bones2wX8sqGHcuXeKPzHgZegtL2dnGC')
verifyAddr('1dice6gJgPDYz8PLQyJb8cgPBnmWqCSuF')
verifyAddr('1Bet56kWEpCq8ugG9tqAkLNXqaAQ4eUALp')
verifyAddr('1Gemk2fKb3hvgs4bi3hW3y8vCaJJrx42NC')
verifyAddr('1bones5gF1HJeiexQus6UtvhU4EUD4qfj')
verifyAddr('1bonesUhqtbLAGKWZuawCzsYqmYWEgPwH')
verifyAddr('1Bet6okTDPYGHZ9ukKf2FFSc5EjRoFipTD')
verifyAddr('1dice2xkjAAiphomEJA5NoowpuJ18HT1s')
verifyAddr('1bonesEeTcABPjLzAb1VkFgySY6Zqu3sX')
verifyAddr('15ZY5nbr2SLtAP22La7323uTBEsM9XxfTZ')
verifyAddr('1PzYwVuTotg15ridCGNnAo8u3dr6bE2Yxy')
verifyAddr('1sLiMbvDGgJjKKzUYsJ2QB9MXiHeeRnCD')
verifyAddr('1bonesBjs3DQUbx4wxPQwrbwCkNjWtLB4')
verifyAddr('1dice2zdoxQHpGRNaAWiqbK82FQhr4fb5')
verifyAddr('1HC3dc4DubRat1P39YBBkwVRbph3ijbtPQ')
verifyAddr('1dice61SNWEKWdA8LN6G44ewsiQfuCvge')
verifyAddr('17gfUvseEjp3aKwReMYUawYxsd25Wq6CjN')
verifyAddr('1Bet16kGTPwHKEbvNK4uQKtYC61Q4MHBst') 

#verifyAddr('1dice97ECuByXAvqXpaYzSaQuPVvrtmz6')  #hot 
#verifyAddr('1MPxhNkSzeTNTHSZAibMaS8HS1esmUL1ne') #hot
#verifyAddr('1NxaBCFQwejSZbQfWcYNwgqML5wWoE3rK4') #hot
#verifyAddr('1LuckyB5VGzdZLZSBZvw8DR17iiFCpST7L') #hot
#verifyAddr('1VayNert3x1KzbpzMGt2qdqrAThiRovi8')  #blockchain error, not add multisig
#verifyAddr('1LuckyY9fRzcJre7aou7ZhWVXktxjjBb9S') #blockchain error, negative balance
#verifyAddr('1LuckyP83urTUEJE9YEaVG2ov3EDz3TgQw') #blockchian error, compare with blockmeta
#verifyAddr('1HTjJ7Ri6LNvbu8GEAeArkFcmTWrb8zqVA') #blockchain error, compare with blockmeta 
db.close()
