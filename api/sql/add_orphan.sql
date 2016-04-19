ALTER TABLE blk ADD COLUMN orphan bool default false;
ALTER TABLE tx ADD COLUMN removed bool default false; 
CREATE TABLE rtx ( id integer NOT NULL UNIQUE);
drop TABLE rtx;

drop view addr_tx_confirmed;
create view addr_tx_confirmed as SELECT a.tx_id, a.addr_id FROM addr_tx a JOIN blk_tx b ON b.tx_id = a.tx_id left join blk c on (c.id=b.blk_id and c.orphan!=true);

drop view utxo;
create view utxo as SELECT g.address, g.id AS addr_id, a.id AS txout_id, c.id AS txin_id, e.id AS txin_tx_id, b.id AS txout_tx_id, b.hash AS txout_txhash, a.value, a.tx_idx, blk.height, blk.time, a.pk_script FROM txout a JOIN tx b ON b.id = a.tx_id LEFT JOIN txin c ON c.prev_out = b.hash AND c.prev_out_index = a.tx_idx JOIN tx e ON e.id = c.tx_id LEFT JOIN addr_txout f ON f.txout_id = a.id LEFT JOIN addr g ON g.id = f.addr_id JOIN blk_tx ON blk_tx.tx_id = a.tx_id JOIN blk ON blk.id = blk_tx.blk_id and blk.orphan!=true WHERE c.id IS NULL;


drop view balance;
drop view vout;
create view vout as SELECT g.address, g.id AS addr_id, a.id AS txout_id, c.id AS txin_id, e.id AS txin_tx_id, b.id AS txout_tx_id, a.value, a.tx_idx AS out_idx, c.tx_idx AS in_idx, e.hash AS txin_tx_hash, b.hash AS txout_tx_hash FROM txout a JOIN tx b ON (b.id = a.tx_id and b.removed!=true) LEFT JOIN txin c ON c.prev_out = b.hash AND c.prev_out_index = a.tx_idx LEFT JOIN tx e ON (e.id = c.tx_id and e.removed!=true) LEFT JOIN addr_txout f ON f.txout_id = a.id LEFT JOIN addr g ON g.id = f.addr_id;
create view balance as SELECT vout.addr_id, sum(vout.value) AS value FROM vout WHERE vout.txin_id IS NULL GROUP BY vout.addr_id;

DROP VIEW v_blk;
CREATE VIEW v_blk AS SELECT a.id, a.hash, a.height, a.version, a.prev_hash, a.mrkl_root, a."time", a.bits, a.nonce, a.blk_size, a.work, a.total_in_count, a.total_in_value, a.fees, a.total_out_count, a.total_out_value, a.tx_count, a.pool_id, a.recv_time, a.pool_bip, a.orphan, b.name AS pool_name, b.link AS pool_link, c.name AS bip_name, c.link AS bip_link FROM ((blk a LEFT JOIN pool b ON ((a.pool_id = b.id))) LEFT JOIN bip c ON ((a.pool_bip = c.id))) ORDER BY a.height DESC; 

DROP VIEW vtx; 
CREATE VIEW v_tx AS SELECT a.id, a.hash, a.version, a.lock_time, a.coinbase, a.tx_size, a.in_count, a.in_value, a.out_count, a.out_value, a.fee, a.recv_time, a.ip,a.removed, b.idx, c.height, c."time" FROM ((tx a LEFT JOIN blk_tx b ON ((b.tx_id = a.id))) LEFT JOIN blk c ON ((c.id = b.blk_id))); 

drop FUNCTION add_tx_statics(txid integer, inc integer, outc integer, inv bigint, outv bigint);
CREATE FUNCTION add_tx_statics(txid integer, inc integer, outc integer, inv bigint, outv bigint) RETURNS void
    LANGUAGE plpgsql
    AS $_$
BEGIN
    IF (inv = 0) THEN
        update tx set in_count=$2, out_count=$3, in_value=$4, out_value=$5, fee=0 where id=$1;
    else
        update tx set in_count=$2, out_count=$3, in_value=$4, out_value=$5, fee=($4-$5) where id=$1;
    END IF;
    perform update_addr_balance($1);
END
$_$;

DROP FUNCTION update_addr_balance(txid integer);
CREATE FUNCTION update_addr_balance(txid integer) RETURNS void
    LANGUAGE plpgsql
    AS $$                                                                                                                     
    DECLARE o RECORD;                                                                                                         
BEGIN                                                                                                                         
    FOR o IN select addr_id, value from vout where txin_tx_id=$1 and addr_id is not NULL LOOP                               
       update addr set balance=(balance - o.value), spent_value=(spent_value+o.value) where id=o.addr_id;                     
    END LOOP;                                                                                                                 
                                                                                                                              
    FOR o IN select addr_id, value from vout where txout_tx_id=$1 and addr_id is not NULL LOOP                              
       update addr set balance=(balance + o.value), recv_value=(recv_value+o.value)  where id=o.addr_id;                      
    END LOOP;                                                                                                                 
                                                                                                                              
                                                                                                                              
    FOR o IN select distinct addr_id from vout where txin_tx_id=$1 and addr_id is not NULL LOOP                             
       update addr set spent_count=(spent_count+1) where id=o.addr_id;                                                        
       insert into addr_tx (addr_id,tx_id) values(o.addr_id, $1);                                                           
    END LOOP;                                                                                                                 
                                                                                                                              
    FOR o IN select distinct addr_id from vout where txout_tx_id=$1 and addr_id is not NULL LOOP                            
       update addr set recv_count=(recv_count+1) where id=o.addr_id;                                                          
    END LOOP;                                                                                                                 

END;                                                                                                                          
$$;


drop  FUNCTION add_blk_statics(blkid integer);
CREATE FUNCTION add_blk_statics(blkid integer) RETURNS void
    LANGUAGE plpgsql
    AS $_$                                                                                                                     
BEGIN
    update blk set total_in_count=t.a, total_out_count=t.b, total_in_value=t.c, total_out_value=t.d, fees=t.e from (select sum(in_count) as a,sum(out_count) as b, sum(in_value) as c, sum(out_value) as d, sum(fee) as e from tx where id in (select tx_id from blk_tx where blk_id=$1)) as t where blk.id=$1;

    delete from utx where id in (select tx_id from blk_tx where blk_id=$1);
    update tx set removed=false where id in (select tx_id from blk_tx where blk_id=$1);
END;
$_$;

drop FUNCTION check_blk_count();
CREATE FUNCTION check_blk_count() RETURNS boolean
    LANGUAGE plpgsql
    AS $$
    DECLARE blk_count1 integer;
    DECLARE blk_count2 integer;
    DECLARE const_stat RECORD;
BEGIN
    select * into const_stat from blk_stat order by id desc limit 1;
    blk_count1 = (select count(1) from blk where height>const_stat.max_height and orphan!=true) + const_stat.max_height;
    blk_count2 = (select max(height) from blk where height>const_stat.max_height and orphan!=true);
    if blk_count1 != blk_count2 then return false; end if;
    return true;
END;
$$;

drop FUNCTION delete_tx(txid integer);
CREATE FUNCTION delete_tx(txid integer) RETURNS void
    LANGUAGE plpgsql
    AS $_$
    DECLARE ntx RECORD;
BEGIN
     FOR ntx IN select txin_tx_id from vout where txout_tx_id=$1 and txin_tx_id is not NULL LOOP
         perform delete_tx(ntx.txin_tx_id);
     END LOOP;
     perform  rollback_addr_balance($1);
     delete from utx where id=$1;
     update tx set removed=true where id=$1;
END;
$_$;

drop FUNCTION delete_blk(blkhash bytea);
CREATE FUNCTION delete_blk(blkhash bytea) RETURNS void
    LANGUAGE plpgsql
    AS $$
    declare blkid integer;
    declare txid integer;
    BEGIN
    blkid=(select id from blk where hash=blkhash);
    txid=(select tx_id from blk_tx where blk_id=blkid and idx=0);
    insert into utx select tx_id from blk_tx where blk_id=blkid and tx_id!=txid;
    update blk set orphan=true where id=blkid; 
    perform delete_tx(txid);
    END
$$;

drop FUNCTION get_confirm(txid integer);
CREATE FUNCTION get_confirm(txid integer) RETURNS integer
    LANGUAGE plpgsql
    AS $_$
    DECLARE tx_height integer;
    DECLARE max_height integer;
BEGIN
    tx_height=(select c.height from tx a join blk_tx b on(b.tx_id=a.id) join blk c on (c.id=b.blk_id and c.orphan!=true) where a.id=$1 order by c.height asc limit 1);
    max_height=(select max(height) from blk where orphan!=true);
    return (max_height-tx_height+1);
END;
$_$;

drop FUNCTION rollback_addr_balance(txid integer);
CREATE FUNCTION rollback_addr_balance(txid integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE o RECORD;
    DECLARE spentv integer;
BEGIN
    FOR o IN select addr_id, value from vout where txin_tx_id=txid and addr_id is not NULL LOOP
       update addr set balance=(balance + o.value), spent_value=(spent_value-o.value) where id=o.addr_id;
    END LOOP;

    FOR o IN select addr_id, value from vout where txout_tx_id=txid and addr_id is not NULL LOOP
       spentv= (select (recv_value-o.value) from addr where id=o.addr_id);
       update addr set balance=(balance - o.value), recv_value=(recv_value-o.value)  where id=o.addr_id;    
    END LOOP;

    FOR o IN select distinct addr_id from vout where txin_tx_id=txid and addr_id is not NULL LOOP
       update addr set spent_count=(spent_count-1) where id=o.addr_id;
    END LOOP;

    FOR o IN select distinct addr_id from vout where txout_tx_id=txid and addr_id is not NULL LOOP
       update addr set recv_count=(recv_count-1) where id=o.addr_id;
    END LOOP;
END;
$$;

drop FUNCTION update_stat();
CREATE FUNCTION update_stat() RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE newHeight  integer;
    DECLARE txCount    integer;
    DECLARE maxBlkId   integer;
    DECLARE maxTxId    integer;
    DECLARE blkSize    bigint;
    DECLARE txSize     bigint;
    DECLARE const_stat RECORD;
BEGIN
    select * into const_stat from blk_stat order by id desc limit 1;
    newHeight = (select (max(height)-6) from blk where orphan!=true);
    if (newHeight = const_stat.max_height) then
       return;
    end if;
    txCount = (select coalesce(sum(tx_count),0) from blk where height<=newHeight and height>const_stat.max_height and orphan!=true);
    maxBlkId = (select id from blk where height=newHeight and orphan!=true);
    maxTxId = (select max(tx_id) from blk_tx a join blk b on (a.blk_id=b.id and b.orphan!=true) where b.height<=newHeight and height>const_stat.max_height);
    maxTxId = (select GREATEST(maxTxId, const_stat.max_tx_id));
    blkSize = (select coalesce(sum(blk_size),0) from blk where height<=newHeight and orphan!=true and height>const_stat.max_height);
    txSize = (select coalesce(sum(tx_size),0) from tx a join blk_tx b on (b.tx_id=a.id) join blk c on (c.id=b.blk_id and orphan!=true ) where c.height<=newHeight and c.height>const_stat.max_height);
    insert into blk_stat (max_height, total_tx_count, max_blk_id, max_tx_id, sum_blk_size, sum_tx_size)
    values(newHeight, (txCount + const_stat.total_tx_count), maxBlkId, maxTxId, (blkSize + const_stat.sum_blk_size), (txSize + const_stat.sum_tx_size));
END;
$$;

drop FUNCTION update_stxo();
CREATE FUNCTION update_stxo() RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE max_blk_height integer;
    DECLARE max_saved_height integer;
BEGIN
    max_blk_height = (select max(height) from blk where orphan!=true);
    max_saved_height = (select max(height) from stxo);
    insert into stxo SELECT * from v_stxo where height<=(max_blk_height - 10) and height>max_saved_height;
END;
$$;

#dropdb -U postgres -p5433 orp&& createdb -U postgres -p5433 orp&& psql -U postgres -p 5433 orp <s.sql  && psql -U postgres -p 5433 orp <sql/add_orphan.sql

drop FUNCTION test(txid integer);
CREATE FUNCTION test(txid integer) RETURNS void
    LANGUAGE plpgsql
    AS $_$
    DECLARE ntx RECORD;
BEGIN
     FOR ntx IN select txin_tx_id from vout where txout_tx_id=$1 and txin_tx_id is not NULL LOOP
         perform  test(ntx.txin_tx_id );
     END LOOP;
END;
$_$;


