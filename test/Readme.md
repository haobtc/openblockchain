
#test.py

 基于blockchain数据,需要建立txindex索引(bitcoin.conf里加txindex=1),运行前关闭bitcoind

#test_rpc.py

 基于rpc接口,运行前修改RPC_URL 为你自己的bitcoind server


#测试函数

'''

 verifyBlk('000000000000000007b66b3ca329af38380bfd6bed9df8f3fa14d74ddee8d3dc')


 verifyTx('aeca55bbeb9495e50500fefcd1e80d4c4aa592f5c277a2a859494ae4b06818a4',False)
 False表示是否为coinbase tx

 verifyAddr('1AytLgGSigqiMGYyy4ces7rSHm7hgCJTv2'); 
 地址数据是和blockchain对比的

'''
