blockstore
==========
block storage using postgres database which provides thrift interface

install
==========

```
% . setup-env.sh
% project-install
```

run blockstored
==========
```
% . setup-env.sh
% bin/blockstored.py
```

Optional: generate thrift libraries
==========
```
% thrift -r --gen py -out lib etc/blockstore.thrift 
% thrift -r --gen js:node -o bsquery/lib etc/blockstore.thrift 

```


Optional: Install daemontools Services
===========
```
cd <path/to/blockstore>
mkdir -p service/logs
if [ ! -f /usr/local/bin/watch-service ]; then
   sudo ln -s $PWD/service/bin/watch-service /usr/local/bin/watch-service
fi

if [ ! -f /usr/local/bin/run-service ]; then
   sudo ln -s $PWD/service/bin/run-service /usr/local/bin/run-service
fi

sudo ln -s $PWD/service/blockstore.tserver /etc/service/blockstore.tserver

```

Optional: Install supervisor services
===========
```
% cd <path/to/blockstore>
% cd etc/supervisor
% cp blockstore.example.conf blockstore.conf  

edit blockstore.conf to fit your settings
% cd ../..
% sudo ln -s $PWD/etc/supervisor/blockstore.conf /etc/supervisor/conf.d/blockstore.conf

```
