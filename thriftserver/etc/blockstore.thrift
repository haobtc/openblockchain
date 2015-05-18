namespace js blockstore
namespace py blockstore

/* Enums and exceptions */
enum Network {
  BITCOIN = 1,
  LITECOIN = 2,
  DOGECOIN = 3,
  DARKCOIN = 4  
}

exception AppException {
 1: string code,
 2: string message = ""
}

exception NotFound {
 1: string message = "not_found"
}

struct Verification {
  1:bool verified,
  2:string message
}


/* block related */

struct Block {
  1:Network nettype,
  2:binary hash,
  3:i32 version,
  4:binary prevHash,
  5:binary merkleRoot,
  6:bool isMain,
  7:optional binary nextHash,
  8:i32 cntTxes,
  9:i32 height,
  10:i32 timestamp,
  11:optional binary objId;
  12:optional i64 bits;
}


/* Tx related */
struct TxInput {
  1:binary hash,
  2:i32 vout,
  3:binary script
  4:optional string address,
  5:optional string amountSatoshi,
  6:optional i64 q
}

struct TxOutput {
  1:string address,
  2:string amountSatoshi,
  3:binary script
}

struct Tx {
  1:Network nettype,
  2:binary hash,
  3:optional i32 version,
  4:optional Block block,
  5:optional i32 blockIndex,
  6:optional binary objId;
  7:list<TxInput> inputs = [],
  8:list<TxOutput> outputs = []
}

struct TxVerification {
  1:bool verified,
  2:string message
}

/* UTXO related */
struct UTXO {
  1:Network nettype,
  2:string address,
  3:string amountSatoshi,
  4:binary txid,
  5:i32 vout
  6:i32 confirmations,
  7:binary scriptPubKey,
  8:i32 timestamp
}

/* Sending TX */
struct SendTx {
  1:binary hash,
  2:binary raw,
  4:optional string remoteAddress
}

/* INV */
enum InvType {
  TX = 1,
  BLOCK = 2
}

struct Inventory {
  1:InvType type,
  2:binary hash
}

struct Peer {
  1:string host,
  2:i32 port,
  3:i32 time
}

service BlockStoreService
{

  /* block related methods */
  Block getBlock(1:Network network, 2:binary blockhash) throws (1:NotFound notfound);
  Block getTipBlock(1:Network network) throws (1:NotFound notfound);

  /* Get the lattest n blocks, n <= 10 */
  list<Block> getTailBlockList(1:Network network, 2:i32 n);

  Verification verifyBlock(1:Network network, 2:Block block);
  void addBlock(1:Network network, 2:Block block, 3:list<binary> txIds) throws (1:AppException e);
  void rewindTip(1:Network network, 2:i32 height) throws (1:AppException e);

  /* tx related methods */	
  Tx getTx(1:Network network, 2:binary txid) throws (1:NotFound notfound);
  list<Tx> getTxList(1:Network network, 2:list<binary> txids);
  list<binary> getMissingTxIdList(1:Network network, 2:list<binary> txids);
  Verification verifyTx(1:Network network, 2:Tx tx, 3:bool mempool);
  void addTxList(1:Network network, 2:list<Tx> txes, 3:bool mempool);
  void removeTx(1:Network network, 2:binary txid) throws (1:NotFound notfound);
  list<Tx> getTxListSince(1:Network network, 2:binary objId, 3:i32 n);
  list<Tx> getTailTxList(1:Network network, 2:i32 n);
  list<Tx> getRelatedTxList(1:Network network, 2:list<string> addresses);
  list<binary> getRelatedTxIdList(1:Network network, 2:list<string> addresses);

  /* sendtx related methods */
  list<SendTx> getSendingTxList(1:Network network);
  list<SendTx> getSendTxList(1:Network network, 2:list<binary> txids);
  void sendTx(1:Network network, 2:SendTx sendTx) throws (1:AppException e);

  /* utxo related methods */
  list<UTXO> getUnspent(1:Network network, 2:list<string> addresses);

  /* inv related methods */
  list<Inventory> getMissingInvList(1:Network network, 2:list<Inventory> invs);

  /* Misc methods */
  /* Get/Set Peers. depricated!
  list<string> getPeers(1:Network network);
  void setPeers(1:Network network, 2:list<string> peers);
  
  /* push some peers */
  void pushPeers(1:Network network, 2:list<Peer> peers);
  list<Peer> popPeers(1:Network network, 2:i32 n);
}
