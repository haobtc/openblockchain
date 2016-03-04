CREATE TABLE blk_stat (                                                                                                           
    id serial primary key,
    timestamp timestamp default current_timestamp,
    max_height integer, 
    total_tx_count integer, 
    max_blk_id integer, 
    max_tx_id integer,
    sum_blk_size bigint, 
    sum_tx_size bigint
    ); 

insert into blk_stat (max_height, total_tx_count, max_blk_id, max_tx_id, sum_blk_size, sum_tx_size) values(0,0,0,0,0,0);

DROP FUNCTION update_stat();
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
    newHeight = (select (max(height)-6) from blk);
    if (newHeight = const_stat.max_height) then
       return;
    end if;
    txCount = (select coalesce(sum(tx_count),0) from blk where height<=newHeight and height>const_stat.max_height);
    maxBlkId = (select id from blk where height=newHeight);
    maxTxId = (select max(tx_id) from blk_tx a join blk b on (a.blk_id=b.id) where b.height<=newHeight and height>const_stat.max_height);
    maxTxId = (select GREATEST(maxTxId, const_stat.max_tx_id));
    blkSize = (select coalesce(sum(blk_size),0) from blk where height<=newHeight and height>const_stat.max_height);
    txSize = (select coalesce(sum(tx_size),0) from tx a join blk_tx b on (b.tx_id=a.id) join blk c on (c.id=b.blk_id) where c.height<=newHeight and c.height>const_stat.max_height);
    insert into blk_stat (max_height, total_tx_count, max_blk_id, max_tx_id, sum_blk_size, sum_tx_size) 
    values(newHeight, (txCount + const_stat.total_tx_count), maxBlkId, maxTxId, (blkSize + const_stat.sum_blk_size), (txSize + const_stat.sum_tx_size));
END;
$$;

DROP FUNCTION check_blk_count();
CREATE FUNCTION check_blk_count() RETURNS boolean
    LANGUAGE plpgsql
    AS $$
    DECLARE blk_count1 integer;
    DECLARE blk_count2 integer;
    DECLARE const_stat RECORD;
BEGIN
    select * into const_stat from blk_stat order by id desc limit 1;
    blk_count1 = (select count(1) from blk where height>const_stat.max_height) + const_stat.max_height;
    blk_count2 = (select max(height) from blk where height>const_stat.max_height);
    if blk_count1 != blk_count2 then return false; end if;
    return true;
END;
$$;

DROP FUNCTION check_tx_count();
CREATE FUNCTION check_tx_count() RETURNS boolean
    LANGUAGE plpgsql
    AS $$
    DECLARE tx_count1 integer;
    DECLARE tx_count2 integer;
    DECLARE tx_count3 integer;
    DECLARE max_id record;
    DECLARE const_stat RECORD;
BEGIN
    select * into const_stat from blk_stat order by id desc limit 1;
    for max_id in (select blk_id,tx_id from blk_tx order by tx_id desc limit 1) loop
    tx_count1 = (select coalesce(sum(tx_count),0) from blk where id<=max_id.blk_id and id>const_stat.max_blk_id);
    tx_count2 = (select coalesce(count(1),0) from tx a join blk_tx b on (a.id=b.tx_id) where b.blk_id<=max_id.blk_id and b.blk_id>const_stat.max_blk_id);
    tx_count3 = (select coalesce(count(tx_id),0) from blk_tx  where blk_id<=max_id.blk_id  and blk_id>const_stat.max_blk_id);
    if tx_count1 != tx_count2 then return false; end if;
    if tx_count3 != tx_count2 then return false; end if;
    end loop;
    return true;  
END;
$$;
 

DROP FUNCTION check_all_tx_count();
CREATE FUNCTION check_all_tx_count() RETURNS boolean
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


DROP FUNCTION check_all_blk_count();
CREATE FUNCTION check_all_blk_count() RETURNS boolean
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
 
