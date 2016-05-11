CREATE TABLE addr_send (addr_id integer NOT NULL, tx_id integer NOT NULL, group_id integer, constraint addr_send_constrainte unique (addr_id, tx_id));
CREATE RULE "addr_send_on_duplicate_ignore" AS ON INSERT TO "addr_send"  WHERE EXISTS(SELECT 1 FROM addr_send  WHERE (addr_id, tx_id)=(NEW.addr_id, NEW.tx_id))  DO INSTEAD NOTHING;
CREATE MATERIALIZED VIEW vvout as SELECT g.id as addr_id, e.id AS txin_tx_id FROM txout a LEFT JOIN tx b ON b.id = a.tx_id left join txin c on (c.prev_out=b.hash and c.prev_out_index=a.tx_idx) left JOIN tx e ON e.id = c.tx_id left JOIN addr_txout f on f.txout_id=a.id left JOIN addr g on g.id=f.addr_id where e.id is not NULL and g.id is not NULL;
CREATE INDEX vvout_address on vvout USING btree (addr_id);
insert into addr_send select distinct addr_id,txin_tx_id as tx_id from vvout;

CREATE OR REPLACE FUNCTION group_addr(txid integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE res RECORD;
BEGIN
     FOR res IN select addr_id from vout where txin_tx_id=$1 LOOP
       select all_group_id from addr_send where addr_id in (res);
       if len(group_id)>0:
          gid=all_group_id[0]
       for group_id in all_group_id:
          update addr_send set group_id=gid where group_id=group_id;
     END LOOP;
END
$$;

select count(1) as n, tx_id from addr_send group by tx_id limit 10;

##more
CREATE MATERIALIZED VIEW vvout1 as SELECT g.id as addr_id, e.id AS txin_tx_id FROM txout a LEFT JOIN tx b ON b.id = a.tx_id left join txin c on (c.prev_out=b.hash and c.prev_out_index=a.tx_idx) left JOIN tx e ON e.id = c.tx_id left JOIN addr_txout f on f.txout_id=a.id left JOIN addr g on g.id=f.addr_id where e.id is not NULL and g.id is not NULL and b.id>97524947;
insert into addr_send select distinct addr_id,txin_tx_id as tx_id from vvout1;


CREATE TABLE addr_group (addr_id integer NOT NULL, tx_id integer NOT NULL, group_id integer);
CREATE RULE "addr_group_on_duplicate_ignore" AS ON INSERT TO "addr_group"  WHERE EXISTS(SELECT 1 FROM addr_group  WHERE (addr_id, tx_id)=(NEW.addr_id, NEW.tx_id))  DO INSTEAD NOTHING;
CREATE INDEX addr_addr_send_index ON addr_send USING btree (addr_id);
CREATE INDEX tx_addr_send_index ON addr_send USING btree (tx_id);
CREATE INDEX group_addr_send_index ON addr_send USING btree (group_id);


CREATE INDEX addr_addr_group_tmp_index ON addr_group_tmp USING btree (addr_id);
CREATE INDEX tx_addr_group_tmp_index ON addr_group_tmp USING btree (tx_id);

CREATE UNIQUE INDEX addr_group_index ON addr_group(addr_id, tx_id);


    insert into addr_group (select addr_id, tx_id from addr_send where group_id is NULL limit 1);
    
    do
    update addr_send set group_id=2 where addr_id in (select distinct addr_id from addr_group);
    insert into addr_group (select addr_id, tx_id from addr_send where group_id is NULL and addr_id in (select distinct addr_id from addr_group));
    count2 = (select count(distinct addr_id) from addr_group)
    insert into addr_group (select addr_id, tx_id from addr_send where group_id is NULL and tx_id in (select distinct tx_id from addr_group));
    count3 = (select count(distinct tx_id) from addr_group)
    if count2==0 and count3==0
        break
    LOOP
    
    truncate table addr_group_tmp;



            count1=session.execute('insert into addr_group_tmp (select addr_id, tx_id from addr_send where group_id is NULL and addr_id in (select distinct addr_id from addr_group_tmp));').rowcount


 select addr_id, tx_id from addr_send where group_id is NULL and addr_id in (select distinct addr_id from addr_group_tmp);
 select a.addr_id, a.tx_id from addr_send a join addr_group_tmp b on (b.addr_id=a.addr_id) where a.group_id is NULL;
 select count(1) from addr_send a join addr_group_tmp b on (b.addr_id=a.addr_id) where a.group_id is NULL;


 select count(1) from addr_send a join addr_group_tmp b on (b.addr_id=a.addr_id and a.group_id is NULL);


 select count(1) from addr_group_tmp a join addr_send b on ((a.addr_id=b.addr_id or a.tx_id=b.tx_id) and b.group_id is NULL);

 count1=session.execute('insert into addr_group_tmp ( select b.addr_id,b.tx_id from addr_group_tmp a join addr_send b on ((a.addr_id=b.addr_id or a.tx_id=b.tx_id) and b.group_id is NULL););').rowcount
 select b.addr_id,b.tx_id from addr_group_tmp a join addr_send b on ((a.addr_id=b.addr_id or a.tx_id=b.tx_id) and b.group_id is NULL);


CREATE INDEX addr_addr_group_tmp_index ON addr_group_tmp USING btree (addr_id);
CREATE INDEX tx_addr_group_tmp_index ON addr_group_tmp USING btree (tx_id);

update addr_send set group_id=NULL where group_id=9;
update addr_send set group_id=9 where addr_id=560864;


select count(1) from addr_send a join (select addr_id,tx_id from addr_send where group_id=9) b on(a.addr_id=b.addr_id or a.tx_id=b.tx_id and a.group_id is NULL);

select a.* from addr_send a join (select distinct addr_id,tx_id from addr_send where group_id=6) b on(a.addr_id=b.addr_id or a.tx_id=b.tx_id) where a.group_id is NULL;


update addr_send set group_id=10 where group_id is NULL limit 1;


update addr_send s set group_id=10 from (select * from addr_send where group_id is NULL limit 1) sub where s.addr_id=sub.addr_id and s.tx_id=sub.tx_id;

update addr_send s set group_id=10 from (select a.* from addr_send a join (select distinct addr_id,tx_id from addr_send where group_id=10) b on(a.addr_id=b.addr_id or a.tx_id=b.tx_id) where a.group_id is NULL) sub where s.addr_id=sub.addr_id and s.tx_id=sub.tx_id;

select a.* from addr_send a join (select addr_id, tx_id from addr_send where group_id is NULL limit 1) b on(a.addr_id=b.addr_id or a.tx_id=b.tx_id) where a.group_id is NULL;




CREATE FUNCTION update_addr_balance(txid integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE o RECORD;
BEGIN
 
FOR o IN select distinct addr_id from vout where txin_tx_id=txid and addr_id is not NULL LOOP
    select 
END LOOP;

END;
$$;

max_tx_id= 98729281;


CREATE INDEX addr_addr_group_index ON addr_group USING btree (addr_id);
CREATE INDEX group_addr_group_index ON addr_group USING btree (group_id);

select max(tx_id) from addr_group;
truncate table addr_send;

CREATE MATERIALIZED VIEW vvout1 as SELECT g.id as addr_id, e.id AS txin_tx_id FROM txout a LEFT JOIN tx b ON b.id = a.tx_id left join txin c on (c.prev_out=b.hash and c.prev_out_index=a.tx_idx) left JOIN tx e ON e.id = c.tx_id left JOIN addr_txout f on f.txout_id=a.id left JOIN addr g on g.id=f.addr_id where e.id is not NULL and g.id is not NULL and b.id>98729281;
insert into addr_send select distinct addr_id,txin_tx_id as tx_id from vvout1;

ALTER TABLE addr ADD group_id integer;

CREATE MATERIALIZED VIEW ag as  select distinct addr_id,group_id from addr_group;
update addr set group_id=ag.group_id from ag where addr_id=ag.addr_id;

alter table addr_group rename to addr_group_old;

CREATE TABLE addr_new_group (addr_id integer NOT NULL, tx_id integer NOT NULL, group_id integer);
CREATE RULE "addr_new_group_on_duplicate_ignore" AS ON INSERT TO "addr_new_group"  WHERE EXISTS(SELECT 1 FROM addr_new_group  WHERE (addr_id, tx_id)=(NEW.addr_id, NEW.tx_id))  DO INSTEAD NOTHING;


select addr_id from addr_group where group_id=38864238;
select distinct addr_id from addr_group where group_id=38864238;                                                       
select count(distinct addr_id) from addr_group where group_id=38864238;                                                
select (distinct addr_id) from addr_group where group_id=38864238;  
select distinct group_id from addr where id in (select distinct addr_id from addr_group where group_id=38864238) and group_id is not NULL;
select * from addr_tag where id=234561;

CREATE TABLE addr_group1 AS SELECT * FROM addr_group;
CREATE TABLE addr_group_id_bak AS SELECT id,group_id FROM addr;

100848900
120215091
CREATE or REPLACE FUNCTION create_group_table(maxTxId integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN               
delete from addr_group_tmp;
delete from addr_send;
CREATE MATERIALIZED VIEW group_vout as SELECT g.id as addr_id, e.id AS txin_tx_id FROM txout a LEFT JOIN tx b ON b.id = a.tx_id left join txin c on (c.prev_out=b.hash and c.prev_out_index=a.tx_idx) left JOIN tx e ON e.id = c.tx_id left JOIN addr_txout f on f.txout_id=a.id left JOIN addr g on g.id=f.addr_id where e.id is not NULL and g.id is not NULL and b.id>maxTxId;
insert into addr_send select distinct addr_id,txin_tx_id as tx_id from group_vout;
end;
 
CREATE or REPLACE FUNCTION create_group_table(maxTxId integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE max_blk_height integer;
BEGIN
    max_blk_height = (select max(height)-10 from blk);
    delete from addr_group_tmp;
    delete from addr_send;
    CREATE MATERIALIZED VIEW group_vout as SELECT g.id as addr_id, e.id AS txin_tx_id FROM txout a LEFT JOIN tx b ON b.id = a.tx_id left join txin c on (c.prev_out=b.hash and c.prev_out_index=a.tx_idx) left JOIN tx e ON e.id = c.tx_id left JOIN addr_txout f on f.txout_id=a.id left JOIN addr g on g.id=f.addr_id where e.id is not NULL and g.id is not NULL and b.id>maxTxId;
    insert into addr_send select distinct addr_id,txin_tx_id as tx_id from group_vout;
end;
 


CREATE INDEX addr_balance_index ON addr USING btree (balance);
