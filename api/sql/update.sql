drop view balance;
drop view vout;

create view vout as
SELECT g.address,
    g.id AS addr_id,
    a.id AS txout_id,
    c.id AS txin_id,
    e.id AS txin_tx_id,
    b.id AS txout_tx_id,
    a.value,
    a.tx_idx as out_idx,
    c.tx_idx as in_idx
   FROM txout a
     LEFT JOIN tx b ON b.id = a.tx_id
     LEFT JOIN txin c ON c.prev_out = b.hash AND c.prev_out_index = a.tx_idx
     LEFT JOIN tx e ON e.id = c.tx_id
     LEFT JOIN addr_txout f ON f.txout_id = a.id
     LEFT JOIN addr g ON g.id = f.addr_id;

create view balance as SELECT vout.addr_id, sum(vout.value) AS value FROM vout WHERE vout.txin_id IS NULL GROUP BY vout.addr_id;

Drop view vtx;
ALTER TABLE tx DROP COLUMN ip;
ALTER TABLE tx ADD COLUMN ip text;

create view vtx as select a.*,b.idx,c.height,c.time from tx a left join blk_tx b on(b.tx_id=a.id) left join blk c on (c.id=b.blk_id);


drop view addr_tx_confirmed;
drop view addr_tx_unconfirmed;
drop table addr_tx;


CREATE TABLE addr_tx (addr_id integer NOT NULL, tx_id integer NOT NULL, constraint u_constrainte unique (addr_id, tx_id));

CREATE RULE "addr_tx_on_duplicate_ignore" AS ON INSERT TO "addr_tx"  WHERE EXISTS(SELECT 1 FROM addr_tx  WHERE (addr_id, tx_id)=(NEW.addr_id, NEW.tx_id))  DO INSTEAD NOTHING;

DROP FUNCTION update_addr_balance(txid integer);
CREATE FUNCTION update_addr_balance(txid integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE o RECORD;
BEGIN

    FOR o IN select addr_id, value from vout where txin_tx_id=txid and addr_id is not NULL LOOP
       update addr set balance=(balance - o.value), spent_value=(spent_value+o.value) where id=o.addr_id;
    END LOOP;

    FOR o IN select addr_id, value from vout where txout_tx_id=txid and addr_id is not NULL LOOP
       update addr set balance=(balance + o.value), recv_value=(recv_value+o.value)  where id=o.addr_id;
    END LOOP;


    FOR o IN select distinct addr_id from vout where txin_tx_id=txid and addr_id is not NULL LOOP
       update addr set spent_count=(spent_count+1) where id=o.addr_id;
       insert into addr_tx (addr_id,tx_id) values(o.addr_id, txid);
    END LOOP;

    FOR o IN select distinct addr_id from vout where txout_tx_id=txid and addr_id is not NULL LOOP
       update addr set recv_count=(recv_count+1) where id=o.addr_id;
       insert into addr_tx (addr_id,tx_id) values(o.addr_id, txid);
    END LOOP;
END;
$$;

drop FUNCTION rollback_addr_balance(txid integer);
CREATE FUNCTION rollback_addr_balance(txid integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE o RECORD;
BEGIN
    FOR o IN select addr_id, value from vout where txin_tx_id=txid and addr_id is not NULL LOOP
       update addr set balance=(balance + o.value), spent_value=(spent_value-o.value) where id=o.addr_id;
    END LOOP;

    FOR o IN select addr_id, value from vout where txout_tx_id=txid and addr_id is not NULL LOOP
       update addr set balance=(balance - o.value), recv_value=(recv_value-o.value)  where id=o.addr_id;
    END LOOP;


    FOR o IN select distinct addr_id from vout where txin_tx_id=txid and addr_id is not NULL LOOP
       update addr set spent_count=(spent_count-1) where id=o.addr_id;
       delete from addr_tx where addr_id=o.addr_id and tx_id=txid;
    END LOOP;

    FOR o IN select distinct addr_id from vout where txout_tx_id=txid and addr_id is not NULL LOOP
       update addr set recv_count=(recv_count-1) where id=o.addr_id;
       delete from addr_tx where addr_id=o.addr_id and tx_id=txid;
    END LOOP;
END;
$$;

ALTER TABLE addr DROP COLUMN recv_value ;
ALTER TABLE addr DROP COLUMN recv_count ;
ALTER TABLE addr DROP COLUMN spent_value;
ALTER TABLE addr DROP COLUMN spent_count;

ALTER TABLE addr ADD COLUMN recv_value bigint    default 0;
ALTER TABLE addr ADD COLUMN recv_count integer   default 0;
ALTER TABLE addr ADD COLUMN spent_value bigint   default 0;
ALTER TABLE addr ADD COLUMN spent_count integer  default 0;

CREATE MATERIALIZED VIEW vvout as SELECT g.address, g.id as addr_id, a.id AS txout_id, c.id AS txin_id, e.id AS txin_tx_id, b.id AS txout_tx_id, a.value FROM txout a LEFT JOIN tx b ON b.id = a.tx_id left join txin c on (c.prev_out=b.hash and c.prev_out_index=a.tx_idx) left JOIN tx e ON e.id = c.tx_id left JOIN addr_txout f on f.txout_id=a.id left JOIN addr g on g.id=f.addr_id;
CREATE INDEX vvout_address on vvout USING btree (addr_id);

insert into addr_tx select distinct addr_id,txout_tx_id as tx_id from vvout where addr_id is not NULL;
insert into addr_tx select distinct addr_id,txin_tx_id as tx_id from vvout where addr_id is not NULL and txin_tx_id is not NULL;

CREATE MATERIALIZED VIEW addr_recv as SELECT vvout.addr_id, sum(vvout.value) AS recv_value, count(distinct vvout.txout_tx_id) as txout_count, count(distinct txin_tx_id) as txin_count FROM vvout GROUP BY vvout.addr_id;
CREATE INDEX addr_recv_address on addr_recv USING btree (addr_id);
CREATE MATERIALIZED VIEW addr_spent as SELECT vvout.addr_id, sum(vvout.value) AS spent_value, count(distinct vvout.txout_tx_id) as spent_txout_count, count(distinct txin_tx_id) as spent_txin_count FROM vvout where vvout.txin_tx_id is not NULL GROUP BY vvout.addr_id;
CREATE INDEX addr_spent_address on addr_spent USING btree (addr_id);

update addr set recv_value=a.recv_value, recv_count=a.txout_count from addr_recv a where addr.id=a.addr_id;
update addr set spent_value=a.spent_value, spent_count=a.spent_txin_count from addr_spent a where addr.id=a.addr_id;
update addr set balance=recv_value-spent_value;

DROP MATERIALIZED VIEW addr_recv;
DROP MATERIALIZED VIEW addr_spent;
DROP MATERIALIZED VIEW vvout;

create view addr_tx_confirmed as select a.tx_id,a.addr_id from addr_tx a join blk_tx b on (b.tx_id=a.tx_id);
create view addr_tx_unconfirmed as select a.tx_id,a.addr_id from addr_tx a join utx b on (b.id=a.tx_id);


CREATE RULE "utx_on_duplicate_ignore" AS ON INSERT TO "utx"  WHERE EXISTS(SELECT 1 FROM utx WHERE (id)=(NEW.id))  DO INSTEAD NOTHING;

CREATE RULE "addr_txout_on_duplicate_ignore" AS ON INSERT TO "addr_txout"  WHERE EXISTS(SELECT 1 FROM addr_txout WHERE (addr_id,txout_id)=(NEW.addr_id, NEW.txout_id))  DO INSTEAD NOTHING;

DROP FUNCTION delete_tx(txid integer);
CREATE FUNCTION delete_tx(txid integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE ntx RECORD;
BEGIN
     FOR ntx IN select txin_tx_id from vout where txout_tx_id=$1 LOOP
         perform delete_tx(ntx.txin_tx_id);
     END LOOP;
     perform  rollback_addr_balance($1);
     delete from addr_txout where txout_id in (select id from txout where tx_id=$1);
     delete from txin where tx_id=$1;
     delete from txout where tx_id=$1;
     delete from tx where id=$1;
     delete from utx where id in ($1);
END;
$$;

update tx set recv_time=recv_time/1000000 where recv_time>1444784647 and recv_time is not NULL;

DROP FUNCTION get_confirm(txid integer);
CREATE FUNCTION get_confirm(txid integer) RETURNS integer
    LANGUAGE plpgsql
    AS $_$
    DECLARE tx_height integer;
    DECLARE max_height integer;
BEGIN
    tx_height=(select c.height from tx a join blk_tx b on(b.tx_id=a.id) join blk c on (c.id=b.blk_id) where a.id=$1 order by c.height asc limit 1);
    max_height=(select max(height) from blk);
    return (max_height-tx_height+1);
END;
$_$;

DROP FUNCTION check_tx_count();
CREATE FUNCTION check_tx_count() RETURNS boolean
    LANGUAGE plpgsql
    AS $$
    DECLARE tx_count1 integer;
    DECLARE tx_count2 integer;
    DECLARE tx_count3 integer;
    DECLARE max_id record;
BEGIN
    for max_id in (select blk_id,tx_id from blk_tx order by tx_id desc limit 1) loop
    tx_count1 = (select sum(tx_count) from blk where id<=max_id.blk_id);
    tx_count2 = (select count(1) from tx where id<=max_id.tx_id) -  (select count(1) from utx where id<=max_id.tx_id) + 2;
    tx_count3 = (select count(tx_id) from blk_tx  where blk_id<=max_id.blk_id);
    if tx_count1 != tx_count2 then return false; end if;
    if tx_count3 != tx_count2 then return false; end if;
    end loop;
    return true;
END;
$$;


DROP FUNCTION check_blk_count();
CREATE FUNCTION check_blk_count() RETURNS boolean
    LANGUAGE plpgsql
    AS $$
    DECLARE blk_count1 integer;
    DECLARE blk_count2 integer;
BEGIN
    blk_count1 = (select count(1) from blk);
    blk_count2 = (select max(height)+1 from blk);
    if blk_count1 != blk_count2 then return false; end if;
    return true;
END;
$$;


CREATE or REPLACE FUNCTION check_tx_count() RETURNS boolean
    LANGUAGE plpgsql
    AS $$
    DECLARE tx_count1 integer;
    DECLARE tx_count2 integer;
    DECLARE tx_count3 integer;
    DECLARE max_blk_id integer;
    DECLARE max_id record;
BEGIN
    max_blk_id = (select max(id) from blk);
    for max_id in (select blk_id,tx_id from blk_tx where blk_id<(max_blk_id-1) order by tx_id desc limit 1) loop
    tx_count1 = (select sum(tx_count) from blk where id<=max_id.blk_id);
    tx_count2 = (select count(1) from tx a join blk_tx b on (b.tx_id=a.id) left join utx c on(c.id=a.id) where c.id is NULL and a.id<=max_id.tx_id and b.blk_id<=max_id.blk_id);
    tx_count3 = (select count(tx_id) from blk_tx  where blk_id<=max_id.blk_id);
    if tx_count1 != tx_count2 then return false; end if;
    if tx_count3 != tx_count2 then return false; end if;
    end loop;
    return true;
END;
$$;

create or replace view vout as
SELECT g.address,
    g.id AS addr_id,
    a.id AS txout_id,
    c.id AS txin_id,
    e.id AS txin_tx_id,
    b.id AS txout_tx_id,
    a.value,
    a.tx_idx as out_idx,
    c.tx_idx as in_idx,
    e.hash AS txin_tx_hash,
    b.hash AS txout_tx_hash
    FROM txout a
     LEFT JOIN tx b ON b.id = a.tx_id
     LEFT JOIN txin c ON c.prev_out = b.hash AND c.prev_out_index = a.tx_idx
     LEFT JOIN tx e ON e.id = c.tx_id
     LEFT JOIN addr_txout f ON f.txout_id = a.id
     LEFT JOIN addr g ON g.id = f.addr_id;

CREATE or REPLACE FUNCTION delete_some_utx() RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE txid integer;
BEGIN
     FOR txid IN select id from utx limit 100 LOOP
         perform delete_tx(txid);
     END LOOP;
END;
$$;

ALTER TABLE blk ADD COLUMN recv_time BIGINT;


CREATE VIEW m_vout AS SELECT g.address, g.id AS addr_id, a.id AS txout_id, c.id AS txin_id, e.id AS txin_tx_id, b.id AS txout_tx_id, a.value, a.tx_idx AS out_idx, c.tx_idx AS in_idx, e.hash AS txin_tx_hash, b.hash AS txout_tx_hash FROM (((((txout a LEFT JOIN tx b ON ((b.id = a.tx_id and (b.in_count>100 or b.out_count>100)))) LEFT JOIN txin c ON (((c.prev_out = b.hash) AND (c.prev_out_index = a.tx_idx)))) LEFT JOIN tx e ON ((e.id = c.tx_id))) LEFT JOIN addr_txout f ON ((f.txout_id = a.id))) LEFT JOIN addr g ON ((g.id = f.addr_id)));
ALTER TABLE m_vout OWNER TO dbuser;

#cron run #must be 9.4
refresh materialized view CONCURRENTLY m_vout;

#spent txout table
drop table stxo;
CREATE TABLE stxo (                                                                                                           
    address text,                                                                                                    
    addr_id integer,
    txout_id      integer, 
    txin_id       integer, 
    txin_tx_id    integer, 
    txout_tx_id   integer, 
    value         bigint , 
    out_idx       integer, 
    in_idx        integer, 
    txout_tx_hash bytea, 
    txin_tx_hash  bytea, 
    height        integer, 
    time          bigint
);

CREATE INDEX stxo_txout_id_index on stxo USING btree (txout_id);

#spent txout view
CREATE or REPLACE VIEW v_stxo AS                                                                                                           
 SELECT g.address,                                                                                                            
    g.id AS addr_id,                                                                                                          
    a.id AS txout_id,                                                                                                         
    c.id AS txin_id,                                                                                                          
    e.id AS txin_tx_id,                                                                                                       
    b.id AS txout_tx_id,                                                                                                      
    a.value,                                                                                                                  
    a.tx_idx AS out_idx,
    c.tx_idx AS in_idx,
    b.hash AS txout_tx_hash,
    e.hash AS txin_tx_hash,
    blk.height,                                                                                                               
    blk.time
   FROM (((((((txout a                                                                                                        
     LEFT JOIN tx b ON ((b.id = a.tx_id)))                                                                                    
     LEFT JOIN txin c ON (((c.prev_out = b.hash) AND (c.prev_out_index = a.tx_idx))))                                         
     LEFT JOIN tx e ON ((e.id = c.tx_id)))                                                                                    
     LEFT JOIN addr_txout f ON ((f.txout_id = a.id)))                                                                         
     LEFT JOIN addr g ON ((g.id = f.addr_id)))                                                                                
     JOIN blk_tx ON ((blk_tx.tx_id = a.tx_id)))                                                                               
     JOIN blk ON ((blk.id = blk_tx.blk_id)))                                                                                  
  WHERE (c.id IS NOT NULL); 

CREATE INDEX stxo_height_index ON stxo USING BTREE (height);
CREATE INDEX stxo_txin_tx_id_index ON stxo USING BTREE (txin_tx_id);
CREATE INDEX stxo_txout_tx_id_index ON stxo USING BTREE (txout_tx_id);
CREATE INDEX stxo_txout_id_index ON stxo USING BTREE (txout_id);
 
#update spent txout table
CREATE or REPLACE FUNCTION update_stxo() RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE max_blk_height integer;
    DECLARE max_saved_height integer;
BEGIN
    max_blk_height = (select max(height) from blk);
    max_saved_height = (select max(height) from stxo);
    insert into stxo SELECT * from v_stxo where height<=(max_blk_height - 10) and height>max_saved_height;
END;
$$;

create or replace view utxo as
SELECT g.address,
    g.id AS addr_id,
    a.id AS txout_id,
    c.id AS txin_id,
    e.id AS txin_tx_id,
    b.id AS txout_tx_id,
    a.value,
    a.tx_idx as out_idx,
    c.tx_idx as in_idx,
    e.hash AS txin_tx_hash,
    b.hash AS txout_tx_hash
    FROM txout a
     LEFT JOIN tx b ON b.id = a.tx_id
     LEFT JOIN txin c ON c.prev_out = b.hash AND c.prev_out_index = a.tx_idx
     LEFT JOIN tx e ON e.id = c.tx_id
     LEFT JOIN addr_txout f ON f.txout_id = a.id
     LEFT JOIN addr g ON g.id = f.addr_id;
  WHERE (c.id IS NULL); 


#these vout not in stxo
create or replace view vtxo as
SELECT g.address,
    g.id AS addr_id,
    a.id AS txout_id,
    c.id AS txin_id,
    e.id AS txin_tx_id,
    b.id AS txout_tx_id,
    a.value,
    a.tx_idx as out_idx,
    c.tx_idx as in_idx,
    e.hash AS txin_tx_hash,
    b.hash AS txout_tx_hash,
    blk.height,                                                                                                               
    blk.time
    FROM txout a
     LEFT JOIN tx b ON b.id = a.tx_id
     LEFT JOIN txin c ON c.prev_out = b.hash AND c.prev_out_index = a.tx_idx
     LEFT JOIN tx e ON e.id = c.tx_id
     LEFT JOIN addr_txout f ON f.txout_id = a.id
     LEFT JOIN addr g ON g.id = f.addr_id
     JOIN blk_tx ON ((blk_tx.tx_id = a.tx_id))                                                                               
     JOIN blk ON ((blk.id = blk_tx.blk_id))                                                                                  
     LEFT JOIN stxo h ON h.txout_id=a.id
  WHERE (h.txout_id IS NULL); 

 

CREATE TABLE addr_tag (                                                                                                           
    id serial primary key,
    addr text, 
    name text, 
    link text); 
 
ALTER TABLE addr_tag OWNER TO dbuser;


CREATE or REPLACE FUNCTION delete_some_utx() RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE txid integer;
BEGIN
     FOR txid IN select id from utx order by id desc limit 100 LOOP
         perform delete_tx(txid);
     END LOOP;
END;
$$;

ALTER TABLE blk ADD COLUMN recv_time BIGINT;
ALTER TABLE blk ADD COLUMN pool_id int;
ALTER TABLE blk ADD COLUMN pool_bip int;

ALTER TABLE addr ADD group_id integer;

#add block view to support pool info and bip info
drop view v_blk;
create view v_blk as select a.*,b.name as pool_name,b.link as pool_link,c.name as bip_name,c.link as bip_link from blk a left join pool b on (a.pool_id=b.id) left join bip c on (a.pool_bip=c.id) order by height desc;
ALTER TABLE v_blk OWNER TO dbuser;


CREATE INDEX m_vout_txout_tx_id_index on m_vout USING btree (txout_tx_id);
CREATE INDEX m_vout_txin_tx_id_index on m_vout USING btree (txin_tx_id);

CREATE or REPLACE VIEW txo AS                                                                                                           
 SELECT g.address,                                                                                                            
    g.id AS addr_id,                                                                                                          
    a.id AS txout_id,                                                                                                         
    c.id AS txin_id,                                                                                                          
    e.id AS txin_tx_id,                                                                                                       
    b.id AS txout_tx_id,                                                                                                      
    a.value,                                                                                                                  
    a.tx_idx AS out_idx,
    c.tx_idx AS in_idx,
    b.hash AS txout_tx_hash,
    e.hash AS txin_tx_hash,
    blk.height,                                                                                                               
    blk.time,
    e.tx_size,
    c.script_sig
   FROM (((((((txout a                                                                                                        
     LEFT JOIN tx b ON ((b.id = a.tx_id)))                                                                                    
     LEFT JOIN txin c ON (((c.prev_out = b.hash) AND (c.prev_out_index = a.tx_idx))))                                         
     LEFT JOIN tx e ON ((e.id = c.tx_id)))                                                                                    
     LEFT JOIN addr_txout f ON ((f.txout_id = a.id)))                                                                         
     LEFT JOIN addr g ON ((g.id = f.addr_id)))                                                                                
     JOIN blk_tx ON ((blk_tx.tx_id = a.tx_id)))                                                                               
     JOIN blk ON ((blk.id = blk_tx.blk_id)))                                                                                  
  WHERE (c.id IS NOT NULL); 
 

CREATE or REPLACE FUNCTION delete_some_utx() RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE groupId integer;
    DECLARE o RECORD;
BEGIN
    groupId = (select group_id from addr_group limit 1);
    groupCount=(select count(distinct group_id) from addr where id in (select count(distinct addr_id) from addr_group where group_id=groupId) and group_id is not NULL;
    if groupCount == 0 then 
       update addr set balance=(balance - o.value), spent_value=(spent_value+o.value) where id=o.addr_id;
       delete from addr_group where group_id=groupId;
       return;
    end if;
    if groupCount == 1 then 
       groupId=(select distinct group_id from addr where id in (select count(distinct addr_id) from addr_group where group_id=groupId) and group_id is not NULL);
       update addr set balance=(balance - o.value), spent_value=(spent_value+o.value) where id=groupId;
       delete from addr_group where group_id=groupId;
       return;
    end if;

    for o in select distinct group_id from addr where id in (select count(distinct addr_id) from addr_group where group_id=groupId) and group_id is not NULL LOOP
        tagId=(select count(1)id from addr_tag where id=o.group_id);   
    END LOOP;

END;
$$;
 

CREATE TABLE addr_group_stat (tx_id integer NOT NULL, group_id integer NOT NULL);
create view vaddr as select a.*, b.name as tag_name, b.link as tag_link from addr a left join addr_tag b on (a.group_id=b.id);

CREATE OR REPLACE FUNCTION public.json_merge(data json, merge_data json)
RETURNS json
IMMUTABLE
LANGUAGE sql
AS $$
    SELECT ('{'||string_agg(to_json(key)||':'||value, ',')||'}')::json
    FROM (
        WITH to_merge AS (
            SELECT * FROM json_each(merge_data)
        )
        SELECT *
        FROM json_each(data)
        WHERE key NOT IN (SELECT key FROM to_merge)
        UNION ALL
        SELECT * FROM to_merge
    ) t;
$$;

CREATE or REPLACE FUNCTION tx_to_json(id integer) RETURNS json
    LANGUAGE plpgsql
    AS $$
    DECLARE txJson json;
    DECLARE jStr json;
BEGIN
    txJson = (select row_to_json (t) from (select * from vtx where vtx.id=$1) as t);

    jStr := (SELECT json_agg(sub) FROM  (select * from txin where tx_id=$1 order by tx_idx) as sub);
    txJson = json_merge(txJson, (select json_build_object('vin', jStr)));

    jStr := (SELECT json_agg(sub) FROM  (select * from txout where tx_id=$1 order by tx_idx) as sub);
    txJson = json_merge(txJson, (select json_build_object('vout', jStr)));

    jStr := (SELECT json_agg(sub) FROM  (select * from (select address, value, txin_tx_id, txout_tx_hash, in_idx from stxo where txin_tx_id=$1 union select address, value, txin_tx_id, txout_tx_hash, in_idx from vtxo where txin_tx_id=$1 ) as t order by in_idx) as sub);
    txJson = json_merge(txJson, (select json_build_object('in_addresses', jStr)));
 
    jStr := (SELECT json_agg(sub) FROM  (select * from (select address, value, txin_tx_id, txin_tx_hash, out_idx from stxo where txout_tx_id=$1 union select  address, value, txin_tx_id, txout_tx_hash, out_idx from vtxo where txout_tx_id=$1) as t order by out_idx) as sub);
    txJson = json_merge(txJson, (select json_build_object('out_addresses', jStr)));
 
    return txJson;
END;
$$;
 
CREATE or REPLACE FUNCTION save_bigtx_to_redis(itemCount integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE r record;
BEGIN
   for r in select id from tx where in_count>$1 or out_count>$1 LOOP
      BEGIN
      insert into redis_db0 (key,val) values((select hash from tx where tx.id=r.id), (select tx_to_json(r.id)));
      EXCEPTION WHEN OTHERS THEN
         -- keep looping
      END;
   END LOOP;
END;
$$;
 
CREATE or REPLACE FUNCTION blk_to_json(blkId integer, txCount integer) RETURNS json
    LANGUAGE plpgsql
    AS $$
    DECLARE blkJson json;
    DECLARE txJson json;
    DECLARE jStr json;
    DECLARE r record;
    DECLARE block record;
    DECLARE ar json[];
BEGIN
    select * from v_blk where v_blk.id=$1 into block;
    blkJson = (select row_to_json (block));
    jStr = (select row_to_json(t) from (select hash from blk where height=(block.height-1)) as t);
    if jStr is not NULL then
        blkJson = json_merge(blkJson, (select json_build_object('nextblockhash', txJson)));
    end if;

    FOR r in select tx_id from blk_tx where blk_id>$1 order by idx limit $2 LOOP
        txJson = (select row_to_json (t) from (select * from tx where tx.id=r.tx_id) as t);

        jStr := (SELECT json_agg(sub) FROM  (select * from (select address, value, txin_tx_id, txout_tx_hash, in_idx from stxo where txin_tx_id=$1 union select address, value, txin_tx_id, txout_tx_hash, in_idx from vtxo where txin_tx_id=$1 ) as t order by in_idx) as sub);
        txJson = json_merge(txJson, (select json_build_object('in_addresses', jStr)));
 
        jStr := (SELECT json_agg(sub) FROM  (select * from (select address, value, txin_tx_id, txin_tx_hash, out_idx from stxo where txout_tx_id=$1 union select  address, value, txin_tx_id, txout_tx_hash, out_idx from vtxo where txout_tx_id=$1) as t order by out_idx) as sub);
        txJson = json_merge(txJson, (select json_build_object('out_addresses', jStr)));
        ar=(select array_append(ar,txJson));
    END LOOP;

    txJson=(select array_to_json(ar));
    blkJson = json_merge(blkJson, (select json_build_object('txs', txJson)));
     
    return blkJson;
END;
$$;

CREATE or REPLACE FUNCTION save_blk_to_redis(startHeight integer, endHeight integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE r record;
BEGIN
   for r in select id from blk where height>=$1 and height<=$2 LOOP
      BEGIN
      insert into redis_db0 (key,val) values((select hash from blk where blk.id=r.id), (select blk_to_json(r.id, 10)));
      EXCEPTION WHEN OTHERS THEN
         -- keep looping
      END;
   END LOOP;
END;
$$;
 
