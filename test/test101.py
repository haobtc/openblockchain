import requests

r = requests.get("http://101.201.141.144:9005/queryapi/v1/block/bitcoin/tip")
print r.text

payload = {"addresses":"1NDnnWCUu926z4wxA3sNBGYWNQD3mKyes8"}
r = requests.post("http://211.155.92.74:9007/queryapi/v1/watch/bitcoin/testgg/addresses/", data=payload)
print r.text

payload = {"addresses":"1NDnnWCUu926z4wxA3sNBGYWNQD3mKyes8"}
r = requests.post("http://101.201.141.144:9005/queryapi/v1/watch/bitcoin/testgg/addresses/", data=payload)
print r.text

# payload_get ={'cursor':10, 'count':10}
r = requests.get("http://101.201.141.144:9005/queryapi/v1/watch/bitcoin/testgg/addresses/?cursor=0&count=10")
print r.text

payload = {"addresses":"1NDnnWCUu926z4wxA3sNBGYWNQD3mKyes8"}
r = requests.get("http://101.201.141.144:9005/queryapi/v1/watch/bitcoin/testgg/tx/list/", data=payload)
print r.text

r = requests.get("http://101.201.141.144:9005/queryapi/v2/tx/list/?cursor=0&count=10&addresses=1NDnnWCUu926z4wxA3sNBGYWNQD3mKyes8")
print r.text

payload = {"rawtx":"0100000002fd1f1dadeca0d9f6960e1c2abc3483827fc50d4fe43265d467f27864f56bffc0000000006946304302202a4dab754f06bf171fe63d8d588d9b361ac67ecb5e9a1d778e20d1ab9c9cbf94021f4f90f7d61ce9df5bcee8db817aeb160e3ee38616cb4b69936a87f888ab4a9201210211b6ad52cb91acc4cf20f3553f260006b40d62ed0339511ded9ebb38acba6ceeffffffffc7dfa0e4fa2608faf8fe8b707d2fa804a6e57e487fa00eca2d6619f683b61e38010000006b483045022100be45d96aa127d328ba36c3342261f9a308b8eaa8902143e27ba128ea158ee98902204625d814bb9f42d6116e29c1b45f21cc0af04a71c3364f1c5ee6e5e885f675240121028102b50350b7d8b866bc4a9ccba52a23dc377434b63d0eb0abd6f0c8e2bec261ffffffff023bf92646000000001976a9146be2df4562dbc9a2857c717694333ca4d3e79d4e88ac25c16206000000001976a91476488ed0a9fbb08dea7f35832797b9aa5c80b6f988ac00000000"}
r = requests.post("http://120.55.193.136:9005/queryapi/v1/sendtx/bitcoin", data=payload)
print r.text

r = requests.get("http://101.201.141.144:9005/queryapi/v1/tx/details?bitcoin=030e0bc14a2d04404f68bdad2d750e0a6f88f6613adeda30bfe2252ae8c9cf91")
print r.text

r = requests.get("http://120.55.193.136:9005/queryapi/v1/tx/details?bitcoin=030e0bc14a2d04404f68bdad2d750e0a6f88f6613adeda30bfe2252ae8c9cf91")
print r.text
http://120.55.193.136:9005/queryapi/v1/tx/details?bitcoin=715e039b1fb0f4f2fea061af6b519ae28f1d33a3b0047743b330cfd7c810b4a0