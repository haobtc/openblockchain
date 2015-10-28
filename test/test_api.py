import requests

payload = {"addresses":"1CttCji7WNynVWxR8ie5aaJBH9rLd4BcSZ,1D2exNDjzuMidy1R6VaxBD8kxbEdzWqs8T"}
r = requests.post("http://211.155.92.74:9007/queryapi/v1/watch/bitcoin/testmmm/addresses/", data=payload)
print r.text

r = requests.post("http://127.0.0.1:5000/queryapi/v1/watch/bitcoin/testgg/addresses/", data=payload)
print r.text