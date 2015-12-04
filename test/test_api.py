import requests

r = requests.get("http://127.0.0.1:9005/queryapi/v1/block/bitcoin/tip")
print r.text

payload = {"addresses":"16RxwkxrWPvpzs88w1jvWXyp4VxMbZbMo"}
r = requests.post("http://211.155.92.74:9007/queryapi/v1/watch/bitcoin/testgg/addresses/", data=payload)
print r.text

payload = {"addresses":"1NDnnWCUu926z4wxA3sNBGYWNQD3mKyes8"}
r = requests.post("http://127.0.0.1:9005/queryapi/v1/watch/bitcoin/testgg/addresses/", data=payload)
print r.text

# payload_get ={'cursor':10, 'count':10}
r = requests.get("http://127.0.0.1:9005/queryapi/v1/watch/bitcoin/testgg/addresses/?cursor=0&count=10")
print r.text

payload = {"addresses":"1NDnnWCUu926z4wxA3sNBGYWNQD3mKyes8"}
r = requests.get("http://127.0.0.1:9005/queryapi/v1/watch/bitcoin/testgg/tx/list/", data=payload)
print r.text

r = requests.get("http://127.0.0.1:9005/queryapi/v2/tx/list/?cursor=0&count=10&addresses=1NDnnWCUu926z4wxA3sNBGYWNQD3mKyes8")
print r.text

payload = {"rawtx":"0100000002fd1f1dadeca0d9f6960e1c2abc3483827fc50d4fe43265d467f27864f56bffc0000000006946304302202a4dab754f06bf171fe63d8d588d9b361ac67ecb5e9a1d778e20d1ab9c9cbf94021f4f90f7d61ce9df5bcee8db817aeb160e3ee38616cb4b69936a87f888ab4a9201210211b6ad52cb91acc4cf20f3553f260006b40d62ed0339511ded9ebb38acba6ceeffffffffc7dfa0e4fa2608faf8fe8b707d2fa804a6e57e487fa00eca2d6619f683b61e38010000006b483045022100be45d96aa127d328ba36c3342261f9a308b8eaa8902143e27ba128ea158ee98902204625d814bb9f42d6116e29c1b45f21cc0af04a71c3364f1c5ee6e5e885f675240121028102b50350b7d8b866bc4a9ccba52a23dc377434b63d0eb0abd6f0c8e2bec261ffffffff023bf92646000000001976a9146be2df4562dbc9a2857c717694333ca4d3e79d4e88ac25c16206000000001976a91476488ed0a9fbb08dea7f35832797b9aa5c80b6f988ac00000000"}
r = requests.post("http://120.55.193.136:9005/queryapi/v1/sendtx/bitcoin", data=payload)
print r.text

r = requests.get("http://127.0.0.1:9005/queryapi/v1/tx/details?bitcoin=030e0bc14a2d04404f68bdad2d750e0a6f88f6613adeda30bfe2252ae8c9cf91")
print r.text

r = requests.get("http://120.55.193.136:9005/queryapi/v1/tx/details?bitcoin=030e0bc14a2d04404f68bdad2d750e0a6f88f6613adeda30bfe2252ae8c9cf91")
print r.text
http://120.55.193.136:9005/queryapi/v1/tx/details?bitcoin=715e039b1fb0f4f2fea061af6b519ae28f1d33a3b0047743b330cfd7c810b4a0

payload = {"rawtx":"010000000167c6a09363f0bc0781bba209146b8aa6f423185e4540a1b5622e9d4c70e7aae201000000fd430100493046022100d366e93b293ac96c16b004cbb66e0a44470b0a036e11468802b98de4c6b87d66022100e1c6f33fa326a3424d65783fdb45c9eb7dd0d65f5d0b384f620637ef4f7e7ec101483045022036423aeab4cee21312b97ac212f9c282362f5ec46f61f69ad9997290576cbc27022100883a71abaf680d9968e45d9609fb21aaa9f91306081f18dd55a30255c21256d4014cad5221021513efa1a86e209b3baea3552636da93b3d45d6ea9b9c8714fd6a23a965d3bdd21021a8a5ea376b57bbecb87100301f21839b4716de53c5aff3ced36f6a3dbae87cf210243f94c89e856f5f4332e91246282fcb8691ab6e360413edba03cff92d48d474e210331f1655177781ebe1e63ff7271c518f6a71eb1ff53aac3c8a85596df9cd3d2302103d2c91897c7edb37b7b1480295a30dd1d9e5cdb7e36e4d01169806cec6675d4e355aeffffffff0280185477000000001976a9148d0f3e6e1de5dfbcc2e33ebc8e1b23cbf2db38ac88ac703d36e30100000017a914d995061b596b70e74d3bef8d2a651e2111bdcf6e8700000000"}
r = requests.post("http://101.201.141.144:9005/queryapi/v1/sendtx/bitcoin", data=payload)
print r.text