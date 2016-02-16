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


CREATE MATERIALIZED VIEW m_vout AS SELECT g.address, g.id AS addr_id, a.id AS txout_id, c.id AS txin_id, e.id AS txin_tx_id, b.id AS txout_tx_id, a.value, a.tx_idx AS out_idx, c.tx_idx AS in_idx, e.hash AS txin_tx_hash, b.hash AS txout_tx_hash FROM (((((txout a LEFT JOIN tx b ON ((b.id = a.tx_id and (b.in_count>100 or b.out_count>100)))) LEFT JOIN txin c ON (((c.prev_out = b.hash) AND (c.prev_out_index = a.tx_idx)))) LEFT JOIN tx e ON ((e.id = c.tx_id))) LEFT JOIN addr_txout f ON ((f.txout_id = a.id))) LEFT JOIN addr g ON ((g.id = f.addr_id)));


#cron run #must be 9.4
refresh materialized view CONCURRENTLY m_vout;

#spent txout table
CREATE TABLE stxo (                                                                                                           
    address text NOT NULL,                                                                                                    
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
 
CREATE TABLE addr_tag (                                                                                                           
    id integer,
    addr text, 
    name text, 
    url text); 
