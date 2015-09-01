#
#
#

from BCDataStream import *
from enumeration import Enumeration
from base58 import public_key_to_bc_address, hash_160_to_bc_address, hash_160, public_key_to_bc,hash_160_to_bc
import logging
import socket
import time
from util import short_hex, long_hex
import struct


def parse_CAddress(vds):
  d = {}
  d['nVersion'] = vds.read_int32()
  d['nTime'] = vds.read_uint32()
  d['nServices'] = vds.read_uint64()
  d['pchReserved'] = vds.read_bytes(12)
  d['ip'] = socket.inet_ntoa(vds.read_bytes(4))
  d['port'] = socket.htons(vds.read_uint16())
  return d

def deserialize_CAddress(d):
  return d['ip']+":"+str(d['port'])+" (lastseen: %s)"%(time.ctime(d['nTime']),)

def parse_setting(setting, vds):
  if setting[0] == "f":  # flag (boolean) settings
    return str(vds.read_boolean())
  elif setting == "addrIncoming":
    return "" # bitcoin 0.4 purposely breaks addrIncoming setting in encrypted wallets.
  elif setting[0:4] == "addr": # CAddress
    d = parse_CAddress(vds)
    return deserialize_CAddress(d)
  elif setting == "nTransactionFee":
    return vds.read_int64()
  elif setting == "nLimitProcessors":
    return vds.read_int32()
  return 'unknown setting'

def parse_TxIn(vds):
  d = {}
  d['prevout_hash'] = vds.read_bytes(32)
  d['prevout_n'] = vds.read_uint32()
  d['scriptSig'] = vds.read_bytes(vds.read_compact_size())
  d['sequence'] = vds.read_uint32()
  return d

def deserialize_TxIn(d, transaction_index=None, owner_keys=None):
  if d['prevout_hash'] == "\x00"*32:
    result = "TxIn: COIN GENERATED"
    result += " coinbase:"+d['scriptSig'].encode('hex_codec')
  elif transaction_index is not None and d['prevout_hash'] in transaction_index:
    p = transaction_index[d['prevout_hash']]['txOut'][d['prevout_n']]
    result = "TxIn: value: %f"%(p['value']/1.0e8,)
    result += " prev("+long_hex(d['prevout_hash'][::-1])+":"+str(d['prevout_n'])+")"
  else:
    result = "TxIn: prev("+long_hex(d['prevout_hash'][::-1])+":"+str(d['prevout_n'])+")"
    pk = extract_public_key(d['scriptSig'])
    result += " pubkey: "+pk
    result += " sig: "+decode_script(d['scriptSig'])
  if d['sequence'] < 0xffffffff: result += " sequence: "+hex(d['sequence'])
  result += ' sig type:' + d['scriptSig'][-1].encode('hex')
  return result

def parse_TxOut(vds):
  d = {}
  d['value'] = vds.read_int64()
  d['scriptPubKey'] = vds.read_bytes(vds.read_compact_size())
  d['scripttype'], tmp= parse_txout_script(d['scriptPubKey'])
  d['sender'] = parse_txout_type(d['scriptPubKey'])
  return d

def deserialize_TxOut(d, owner_keys=None):
  result =  "TxOut: value: %f"%(d['value']/1.0e8,)
  pk = extract_public_key(d['scriptPubKey'])
  result += " pubkey: "+pk
  result += " Script: "+decode_script(d['scriptPubKey'])
  if owner_keys is not None:
    if pk in owner_keys: result += " Own: True"
    else: result += " Own: False"
  result += ' script type: %s ' % d['scripttype']
  result += ' script from: %s' %  d['sender']
  print result

  return result

def parse_Transaction(vds, has_nTime=False):
  d = {}
  start_pos = vds.read_cursor
  d['version'] = vds.read_int32()
  if has_nTime:
    d['nTime'] = vds.read_uint32()
  n_vin = vds.read_compact_size()
  d['txIn'] = []
  for i in xrange(n_vin):
    d['txIn'].append(parse_TxIn(vds))
  n_vout = vds.read_compact_size()
  d['txOut'] = []
  for i in xrange(n_vout):
    d['txOut'].append(parse_TxOut(vds))
  d['lockTime'] = vds.read_uint32()
  d['__data__'] = vds.input[start_pos:vds.read_cursor]
  return d

def deserialize_Transaction(d, transaction_index=None, owner_keys=None, print_raw_tx=False):
  result = "%d tx in, %d out\n"%(len(d['txIn']), len(d['txOut']))
  for txIn in d['txIn']:
    result += deserialize_TxIn(txIn, transaction_index) + "\n"
  for txOut in d['txOut']:
    result += deserialize_TxOut(txOut, owner_keys) + "\n"
  if print_raw_tx == True:
      result += "Transaction hex value: " + d['__data__'].encode('hex') + "\n"
  
  return result

def parse_MerkleTx(vds):
  d = parse_Transaction(vds)
  d['hashBlock'] = vds.read_bytes(32)
  n_merkleBranch = vds.read_compact_size()
  d['merkleBranch'] = vds.read_bytes(32*n_merkleBranch)
  d['nIndex'] = vds.read_int32()
  return d

def deserialize_MerkleTx(d, transaction_index=None, owner_keys=None):
  tx = deserialize_Transaction(d, transaction_index, owner_keys)
  result = "block: "+(d['hashBlock'][::-1]).encode('hex_codec')
  result += " %d hashes in merkle branch\n"%(len(d['merkleBranch'])/32,)
  return result+tx

def parse_WalletTx(vds):
  d = parse_MerkleTx(vds)
  n_vtxPrev = vds.read_compact_size()
  d['vtxPrev'] = []
  for i in xrange(n_vtxPrev):
    d['vtxPrev'].append(parse_MerkleTx(vds))

  d['mapValue'] = {}
  n_mapValue = vds.read_compact_size()
  for i in xrange(n_mapValue):
    key = vds.read_string()
    value = vds.read_string()
    d['mapValue'][key] = value
  n_orderForm = vds.read_compact_size()
  d['orderForm'] = []
  for i in xrange(n_orderForm):
    first = vds.read_string()
    second = vds.read_string()
    d['orderForm'].append( (first, second) )
  d['fTimeReceivedIsTxTime'] = vds.read_uint32()
  d['timeReceived'] = vds.read_uint32()
  d['fromMe'] = vds.read_boolean()
  d['spent'] = vds.read_boolean()

  return d

def deserialize_WalletTx(d, transaction_index=None, owner_keys=None):
  result = deserialize_MerkleTx(d, transaction_index, owner_keys)
  result += "%d vtxPrev txns\n"%(len(d['vtxPrev']),)
  result += "mapValue:"+str(d['mapValue'])
  if len(d['orderForm']) > 0:
    result += "\n"+" orderForm:"+str(d['orderForm'])
  result += "\n"+"timeReceived:"+time.ctime(d['timeReceived'])
  result += " fromMe:"+str(d['fromMe'])+" spent:"+str(d['spent'])
  return result

# The CAuxPow (auxiliary proof of work) structure supports merged mining.
# A flag in the block version field indicates the structure's presence.
# As of 8/2011, the Original Bitcoin Client does not use it.  CAuxPow
# originated in Namecoin; see
# https://github.com/vinced/namecoin/blob/mergedmine/doc/README_merged-mining.md.
def parse_AuxPow(vds):
  d = parse_MerkleTx(vds)
  n_chainMerkleBranch = vds.read_compact_size()
  d['chainMerkleBranch'] = vds.read_bytes(32*n_chainMerkleBranch)
  d['chainIndex'] = vds.read_int32()
  d['parentBlock'] = parse_BlockHeader(vds)
  return d

def parse_BlockHeader(vds):
  d = {}
  header_start = vds.read_cursor
  d['version'] = vds.read_int32()
  d['hashPrev'] = vds.read_bytes(32)
  d['hashMerkleRoot'] = vds.read_bytes(32)
  d['nTime'] = vds.read_uint32()
  d['nBits'] = vds.read_uint32()
  d['nNonce'] = vds.read_uint32()
  header_end = vds.read_cursor
  d['__header__'] = vds.input[header_start:header_end]
  return d

def parse_Block(vds):
  d = parse_BlockHeader(vds)
  d['transactions'] = []
#  if d['version'] & (1 << 8):
#    d['auxpow'] = parse_AuxPow(vds)
  nTransactions = vds.read_compact_size()
  for i in xrange(nTransactions):
    d['transactions'].append(parse_Transaction(vds))

  return d
  
def deserialize_Block(d, print_raw_tx=False):
  result = "Time: "+time.ctime(d['nTime'])+" Nonce: "+str(d['nNonce'])
  result += "\nnBits: 0x"+hex(d['nBits'])
  result += "\nhashMerkleRoot: 0x"+d['hashMerkleRoot'][::-1].encode('hex_codec')
  result += "\nPrevious block: "+d['hashPrev'][::-1].encode('hex_codec')
  result += "\n%d transactions:\n"%len(d['transactions'])
  for t in d['transactions']:
    result += deserialize_Transaction(t, print_raw_tx=print_raw_tx)+"\n"
  result += "\nRaw block header: "+d['__header__'].encode('hex_codec')
  return result

def parse_BlockLocator(vds):
  d = { 'hashes' : [] }
  nHashes = vds.read_compact_size()
  for i in xrange(nHashes):
    d['hashes'].append(vds.read_bytes(32))
  return d

def deserialize_BlockLocator(d):
  result = "Block Locator top: "+d['hashes'][0][::-1].encode('hex_codec')
  return result

opcodes = Enumeration("Opcodes", [
    ("OP_0", 0), ("OP_PUSHDATA1",76), "OP_PUSHDATA2", "OP_PUSHDATA4", "OP_1NEGATE", "OP_RESERVED",
    "OP_1", "OP_2", "OP_3", "OP_4", "OP_5", "OP_6", "OP_7",
    "OP_8", "OP_9", "OP_10", "OP_11", "OP_12", "OP_13", "OP_14", "OP_15", "OP_16",
    "OP_NOP", "OP_VER", "OP_IF", "OP_NOTIF", "OP_VERIF", "OP_VERNOTIF", "OP_ELSE", "OP_ENDIF", "OP_VERIFY",
    "OP_RETURN", "OP_TOALTSTACK", "OP_FROMALTSTACK", "OP_2DROP", "OP_2DUP", "OP_3DUP", "OP_2OVER", "OP_2ROT", "OP_2SWAP",
    "OP_IFDUP", "OP_DEPTH", "OP_DROP", "OP_DUP", "OP_NIP", "OP_OVER", "OP_PICK", "OP_ROLL", "OP_ROT",
    "OP_SWAP", "OP_TUCK", "OP_CAT", "OP_SUBSTR", "OP_LEFT", "OP_RIGHT", "OP_SIZE", "OP_INVERT", "OP_AND",
    "OP_OR", "OP_XOR", "OP_EQUAL", "OP_EQUALVERIFY", "OP_RESERVED1", "OP_RESERVED2", "OP_1ADD", "OP_1SUB", "OP_2MUL",
    "OP_2DIV", "OP_NEGATE", "OP_ABS", "OP_NOT", "OP_0NOTEQUAL", "OP_ADD", "OP_SUB", "OP_MUL", "OP_DIV",
    "OP_MOD", "OP_LSHIFT", "OP_RSHIFT", "OP_BOOLAND", "OP_BOOLOR",
    "OP_NUMEQUAL", "OP_NUMEQUALVERIFY", "OP_NUMNOTEQUAL", "OP_LESSTHAN",
    "OP_GREATERTHAN", "OP_LESSTHANOREQUAL", "OP_GREATERTHANOREQUAL", "OP_MIN", "OP_MAX",
    "OP_WITHIN", "OP_RIPEMD160", "OP_SHA1", "OP_SHA256", "OP_HASH160",
    "OP_HASH256", "OP_CODESEPARATOR", "OP_CHECKSIG", "OP_CHECKSIGVERIFY", "OP_CHECKMULTISIG",
    "OP_CHECKMULTISIGVERIFY",
    "OP_NOP1", "OP_NOP2", "OP_NOP3", "OP_NOP4", "OP_NOP5", "OP_NOP6", "OP_NOP7", "OP_NOP8", "OP_NOP9", "OP_NOP10",
    ("OP_INVALIDOPCODE", 0xFF),
])

def script_GetOp(bytes):
  i = 0
  while i < len(bytes):
    vch = None
    opcode = ord(bytes[i])
    i += 1

    if opcode <= opcodes.OP_PUSHDATA4:
      nSize = opcode
      if opcode == opcodes.OP_PUSHDATA1:
        if i + 1 > len(bytes):
          vch = "_INVALID_NULL"
          i = len(bytes)
        else:
          nSize = ord(bytes[i])
          i += 1
      elif opcode == opcodes.OP_PUSHDATA2:
        if i + 2 > len(bytes):
          vch = "_INVALID_NULL"
          i = len(bytes)
        else:
          (nSize,) = struct.unpack_from('<H', bytes, i)
          i += 2
      elif opcode == opcodes.OP_PUSHDATA4:
        if i + 4 > len(bytes):
          vch = "_INVALID_NULL"
          i = len(bytes)
        else:
          (nSize,) = struct.unpack_from('<I', bytes, i)
          i += 4
      if i+nSize > len(bytes):
        vch = "_INVALID_"+bytes[i:]
        i = len(bytes)
      else:
        vch = bytes[i:i+nSize]
        i += nSize
    elif opcodes.OP_1 <= opcode <= opcodes.OP_16:
      vch = chr(opcode - opcodes.OP_1 + 1)
    elif opcode == opcodes.OP_1NEGATE:
      vch = chr(255)

    yield (opcode, vch)

def script_GetOpName(opcode):
  try:
    return (opcodes.whatis(opcode)).replace("OP_", "")
  except KeyError:
    return "InvalidOp_"+str(opcode)

def decode_script(bytes):
  result = ''
  for (opcode, vch) in script_GetOp(bytes):
    if len(result) > 0: result += " "
    if opcode <= opcodes.OP_PUSHDATA4:
      result += "%d:"%(opcode,)
      result += long_hex(vch)
    else:
      result += script_GetOpName(opcode)
  return result

def match_decoded(decoded, to_match):
  if len(decoded) != len(to_match):
    return False;
  j=0
  for i in range(len(decoded)):
    if to_match[i] == opcodes.OP_PUSHDATA4 and decoded[i][0] <= opcodes.OP_PUSHDATA4:
      continue  # Opcodes below OP_PUSHDATA4 all just push data onto stack, and are equivalent.
    if to_match[i] != decoded[i][0]:
      return False
    j+=1
    if to_match[i] == opcodes.OP_RETURN:
      break
  if j==0: 
     return False
  return True

def extract_public_key(bytes, version='\x00'):
  try:
    decoded = [ x for x in script_GetOp(bytes) ]
  except struct.error:
    return "(None)"

  # non-generated TxIn transactions push a signature
  # (seventy-something bytes) and then their public key
  # (33 or 65 bytes) onto the stack:
  match = [ opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4 ]
  if match_decoded(decoded, match):
    return public_key_to_bc_address(decoded[1][1], version=version)

  # The Genesis Block, self-payments, and pay-by-IP-address payments look like:
  # 65 BYTES:... CHECKSIG
  match = [ opcodes.OP_PUSHDATA4, opcodes.OP_CHECKSIG ]
  if match_decoded(decoded, match):
    return public_key_to_bc_address(decoded[0][1], version=version)

  # Pay-by-Bitcoin-address TxOuts look like:
  # DUP HASH160 20 BYTES:... EQUALVERIFY CHECKSIG
  match = [ opcodes.OP_DUP, opcodes.OP_HASH160, opcodes.OP_PUSHDATA4, opcodes.OP_EQUALVERIFY, opcodes.OP_CHECKSIG ]
  if match_decoded(decoded, match):
    return hash_160_to_bc_address(decoded[2][1], version=version)

  # BIP11 TxOuts look like one of these:
  # Note that match_decoded is dumb, so OP_1 actually matches OP_1/2/3/etc:
  multisigs = [
    [ opcodes.OP_1, opcodes.OP_PUSHDATA4, opcodes.OP_1, opcodes.OP_CHECKMULTISIG ],
    [ opcodes.OP_2, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_2, opcodes.OP_CHECKMULTISIG ],
    [ opcodes.OP_3, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_3, opcodes.OP_CHECKMULTISIG ]
  ]
  for match in multisigs:
    if match_decoded(decoded, match):
      return "["+','.join([public_key_to_bc_address(decoded[i][1]) for i in range(1,len(decoded)-2)])+"]"

  # BIP16 TxOuts look like:
  # HASH160 20 BYTES:... EQUAL
  match = [ opcodes.OP_HASH160, 0x14, opcodes.OP_EQUAL ]
  if match_decoded(decoded, match):
    return hash_160_to_bc_address(decoded[1][1], version="\x05")

  return "(None)"

def extract_hash160(bytes, version='\x00'):
    try:
        decoded = [x for x in script_GetOp(bytes)]
    except struct.error:
        return "(None)"

    # non-generated TxIn transactions push a signature
    # (seventy-something bytes) and then their public key
    # (33 or 65 bytes) onto the stack:
    match = [opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4]
    if match_decoded(decoded, match):
        return hash_160(decoded[1][1])

    # The Genesis Block, self-payments, and pay-by-IP-address payments look like:
    # 65 BYTES:... CHECKSIG
    match = [opcodes.OP_PUSHDATA4, opcodes.OP_CHECKSIG]
    if match_decoded(decoded, match):
        return hash_160(decoded[0][1])

    # Pay-by-Bitcoin-address TxOuts look like:
    # DUP HASH160 20 BYTES:... EQUALVERIFY CHECKSIG
    match = [opcodes.OP_DUP, opcodes.OP_HASH160, opcodes.OP_PUSHDATA4,
             opcodes.OP_EQUALVERIFY, opcodes.OP_CHECKSIG]
    if match_decoded(decoded, match):
        return decoded[2][1]

    # BIP11 TxOuts look like one of these:
    multisigs = [
        [opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_1,
         opcodes.OP_CHECKMULTISIG], [
             opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4,
             opcodes.OP_2, opcodes.OP_CHECKMULTISIG
         ], [opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4,
             opcodes.OP_PUSHDATA4, opcodes.OP_3, opcodes.OP_CHECKMULTISIG]
    ]
    for match in multisigs:
        if match_decoded(decoded, match):
            return "[" + ','.join([hash_160(decoded[i][1])
                                   for i in range(1, len(decoded) - 2)]) + "]"

    # BIP16 TxOuts look like:
    # HASH160 20 BYTES:... EQUAL
    match = [opcodes.OP_HASH160, 0x14, opcodes.OP_EQUAL]
    if match_decoded(decoded, match):
        return decoded[1][1]

    return "(None)"

def extract_key(bytes, version='\x00'):
  try:
    decoded = [ x for x in script_GetOp(bytes) ]
  except struct.error:
    return [None]

  # non-generated TxIn transactions push a signature
  # (seventy-something bytes) and then their public key
  # (33 or 65 bytes) onto the stack:
  match = [ opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4 ]
  if match_decoded(decoded, match):
    return public_key_to_bc(decoded[1][1], version=version,typeret=0)

  # The Genesis Block, self-payments, and pay-by-IP-address payments look like:
  # 65 BYTES:... CHECKSIG
  match = [ opcodes.OP_PUSHDATA4, opcodes.OP_CHECKSIG ]
  if match_decoded(decoded, match):
    return [public_key_to_bc(decoded[0][1], version=version,typeret=1)]

  # Pay-by-Bitcoin-address TxOuts look like:
  # DUP HASH160 20 BYTES:... EQUALVERIFY CHECKSIG
  match = [ opcodes.OP_DUP, opcodes.OP_HASH160, opcodes.OP_PUSHDATA4, opcodes.OP_EQUALVERIFY, opcodes.OP_CHECKSIG ]
  if match_decoded(decoded, match):
    return [hash_160_to_bc(decoded[2][1], version=version,typeret=2)]

  # BIP11 TxOuts look like one of these:
  # Note that match_decoded is dumb, so OP_1 actually matches OP_1/2/3/etc:
  multisigs = [
    [ opcodes.OP_1, opcodes.OP_PUSHDATA4, opcodes.OP_1, opcodes.OP_CHECKMULTISIG ],
    [ opcodes.OP_2, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_2, opcodes.OP_CHECKMULTISIG ],
    [ opcodes.OP_3, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_3, opcodes.OP_CHECKMULTISIG ]
  ]
  for match in multisigs:
    if match_decoded(decoded, match):
      return [public_key_to_bc(decoded[i][1],typeret=4) for i in range(1,len(decoded)-2)]

  # BIP16 TxOuts look like:
  # HASH160 20 BYTES:... EQUAL
  match = [ opcodes.OP_HASH160, 0x14, opcodes.OP_EQUAL ]
  if match_decoded(decoded, match):
    return [hash_160_to_bc(decoded[1][1], version="\x05",typeret=3)]

  return [None]
   

def extract_type(bytes, version='\x00'):
  try:
    decoded = [ x for x in script_GetOp(bytes) ]
  except struct.error:
    return 0

  # The Genesis Block, self-payments, and pay-by-IP-address payments look like:
  # 65 BYTES:... CHECKSIG
  match = [ opcodes.OP_PUSHDATA4, opcodes.OP_CHECKSIG ]
  if match_decoded(decoded, match):
    return 1

  # Pay-by-Bitcoin-address TxOuts look like:
  # DUP HASH160 20 BYTES:... EQUALVERIFY CHECKSIG
  match = [ opcodes.OP_DUP, opcodes.OP_HASH160, opcodes.OP_PUSHDATA4, opcodes.OP_EQUALVERIFY, opcodes.OP_CHECKSIG ]
  if match_decoded(decoded, match):
    return 2

  # BIP11 TxOuts look like one of these:
  # Note that match_decoded is dumb, so OP_1 actually matches OP_1/2/3/etc:
  multisigs = [
    [ opcodes.OP_1, opcodes.OP_PUSHDATA4, opcodes.OP_1, opcodes.OP_CHECKMULTISIG ],
    [ opcodes.OP_2, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_2, opcodes.OP_CHECKMULTISIG ],
    [ opcodes.OP_3, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_3, opcodes.OP_CHECKMULTISIG ]
  ]
  for match in multisigs:
    if match_decoded(decoded, match):
      return 4

  # BIP16 TxOuts look like:
  # HASH160 20 BYTES:... EQUAL
  match = [ opcodes.OP_HASH160, 0x14, opcodes.OP_EQUAL ]
  if match_decoded(decoded, match):
    return 3

  match = [ opcodes.OP_RETURN,  0]
  if match_decoded(decoded, match):
    return 5

  return 0
   
                     

PUBKEY_HASH_LENGTH = 20
MAX_MULTISIG_KEYS = 3

# Template to match a pubkey hash ("Bitcoin address transaction") in
# txout_scriptPubKey.  OP_PUSHDATA4 matches any data push.
SCRIPT_ADDRESS_TEMPLATE = [
    opcodes.OP_DUP, opcodes.OP_HASH160, opcodes.OP_PUSHDATA4, opcodes.OP_EQUALVERIFY, opcodes.OP_CHECKSIG ]

# Template to match a pubkey ("IP address transaction") in txout_scriptPubKey.
SCRIPT_PUBKEY_TEMPLATE = [ opcodes.OP_PUSHDATA4, opcodes.OP_CHECKSIG ]

# Template to match a BIP16 pay-to-script-hash (P2SH) output script.
SCRIPT_P2SH_TEMPLATE = [ opcodes.OP_HASH160, PUBKEY_HASH_LENGTH, opcodes.OP_EQUAL ]

# Template to match a script that can never be redeemed, used in Namecoin.
SCRIPT_BURN_TEMPLATE = [ opcodes.OP_RETURN,  0]
 

SIGHASH_ALL = 1
SIGHASH_NONE = 2
SIGHASH_SINGLE = 3
SIGHASH_ANYONECANPAY = 128
sigType = {
SIGHASH_ALL:'SIGHASH_ALL',
SIGHASH_NONE:'SIGHASH_NONE',
SIGHASH_SINGLE:'SIGHASH_SINGLE',
SIGHASH_ANYONECANPAY:'SIGHASH_ANYONECANPAY'
}

SCRIPT_TYPE_INVALID = -1
SCRIPT_TYPE_UNKNOWN = 0
SCRIPT_TYPE_PUBKEY = 1
SCRIPT_TYPE_ADDRESS = 2
SCRIPT_TYPE_P2SH = 3
SCRIPT_TYPE_MULTISIG = 4
SCRIPT_TYPE_BURN = 5

scriptType = {
SCRIPT_TYPE_INVALID   :"SCRIPT_TYPE_INVALID",
SCRIPT_TYPE_UNKNOWN   :"SCRIPT_TYPE_UNKNOWN",
SCRIPT_TYPE_PUBKEY    :"SCRIPT_TYPE_PUBKEY",
SCRIPT_TYPE_ADDRESS   :"SCRIPT_TYPE_ADDRESS",
SCRIPT_TYPE_BURN      :"SCRIPT_TYPE_BURN",
SCRIPT_TYPE_MULTISIG  :"SCRIPT_TYPE_MULTISIG" ,
SCRIPT_TYPE_P2SH      :"SCRIPT_TYPE_P2SH"
}
 

def parse_txout_script(script):
    """
    Return TYPE, DATA where the format of DATA depends on TYPE.

    * SCRIPT_TYPE_INVALID  - DATA is the raw script
    * SCRIPT_TYPE_UNKNOWN  - DATA is the decoded script
    * SCRIPT_TYPE_PUBKEY   - DATA is the binary public key
    * SCRIPT_TYPE_ADDRESS  - DATA is the binary public key hash
    * SCRIPT_TYPE_BURN     - DATA is None
    * SCRIPT_TYPE_MULTISIG - DATA is {"m":M, "pubkeys":list_of_pubkeys}
    * SCRIPT_TYPE_P2SH     - DATA is the binary script hash
    """
    if script is None:
        raise ValueError()
    try:
        decoded = [ x for x in script_GetOp(script) ]
    except Exception:
        return SCRIPT_TYPE_INVALID, script
    return parse_decoded_txout_script(decoded)

def parse_decoded_txout_script(decoded):
    if match_decoded(decoded, SCRIPT_ADDRESS_TEMPLATE):
        pubkey_hash = decoded[2][1]
        if len(pubkey_hash) == PUBKEY_HASH_LENGTH:
            return SCRIPT_TYPE_ADDRESS, pubkey_hash

    elif match_decoded(decoded, SCRIPT_PUBKEY_TEMPLATE):
        pubkey = decoded[0][1]
        return SCRIPT_TYPE_PUBKEY, pubkey

    elif match_decoded(decoded, SCRIPT_P2SH_TEMPLATE):
        script_hash = decoded[1][1]
        assert len(script_hash) == PUBKEY_HASH_LENGTH
        return SCRIPT_TYPE_P2SH, script_hash

    elif match_decoded(decoded, SCRIPT_BURN_TEMPLATE):
        return SCRIPT_TYPE_BURN, None

    elif len(decoded) >= 4 and decoded[-1][0] == opcodes.OP_CHECKMULTISIG:
        # cf. bitcoin/src/script.cpp:Solver
        n = decoded[-2][0] + 1 - opcodes.OP_1
        m = decoded[0][0] + 1 - opcodes.OP_1
        if 1 <= m <= n <= MAX_MULTISIG_KEYS and len(decoded) == 3 + n and \
                all([ decoded[i][0] <= opcodes.OP_PUSHDATA4 for i in range(1, 1+n) ]):
            return SCRIPT_TYPE_MULTISIG, \
                { "m": m, "pubkeys": [ decoded[i][1] for i in range(1, 1+n) ] }

    # Namecoin overrides this to accept name operations.
    return SCRIPT_TYPE_UNKNOWN, decoded
 

txlistedPrefixes = [
    (0x946cb2e0, 0x946cb2e0,  1), # "Mastercoin"),                                   #1), #
    (0x06f1b600, 0x06f1b6ff,  2), # "SatoshiDice"),                                  #2), #
    (0x74db3700, 0x74db59ff,  3), # "BetCoin Dice"),                                 #3), #
    (0xc4c5d791, 0xc4c5d791,  4), # "CHBS"),  # 1JwSSubhmg6iPtRjtyqhUYYH7bZg3Lfy1T   #4), #
    (0x434e5452, 0x434e5452,  5), # "Counterparty"),                                 #5), #
    (0x069532d8, 0x069532da,  6), # "SatoshiBones"),                                 #6), #
    (0xda5dde84, 0xda5dde94,  7), # "Lucky Bit"),                                    #7), #
    ]                                
def parse_txout_type(script):
    """
    """
    if (len(script) >=7) and (script[0].encode('hex') == '76'):
        pfx = int(script.encode('hex')[6:14], 16) #ntohl and to int
        for l in txlistedPrefixes:
            if (pfx >= l[0]) and (pfx <= l[1]):
                return l[2]

    return 0
 
