--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

--
-- Name: add_blk_statics(integer); Type: FUNCTION; Schema: public; Owner: dbuser
--

CREATE FUNCTION add_blk_statics(blkid integer) RETURNS void
    LANGUAGE plpgsql
    AS $_$                                                                                                                     
BEGIN                                                                                                                         
    update blk set total_in_count=t.a, total_out_count=t.b, total_in_value=t.c, total_out_value=t.d, fees=t.e from (select sum(in_count) as a,sum(out_count) as b, sum(in_value) as c, sum(out_value) as d, sum(fee) as e from tx where id in (select tx_id from blk_tx where blk_id=$1)) as t where blk.id=$1;                                                                      
                                                                                                                              
    delete from utx where id in (select tx_id from blk_tx where blk_id=$1);                                                   
END;                                                                                                                          
$_$;


ALTER FUNCTION public.add_blk_statics(blkid integer) OWNER TO dbuser;

--
-- Name: add_tx_statics(integer, integer, integer, bigint, bigint); Type: FUNCTION; Schema: public; Owner: dbuser
--

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


ALTER FUNCTION public.add_tx_statics(txid integer, inc integer, outc integer, inv bigint, outv bigint) OWNER TO dbuser;

--
-- Name: check_all_blk_count(); Type: FUNCTION; Schema: public; Owner: postgres
--

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


ALTER FUNCTION public.check_all_blk_count() OWNER TO postgres;

--
-- Name: check_all_tx_count(); Type: FUNCTION; Schema: public; Owner: dbuser
--

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


ALTER FUNCTION public.check_all_tx_count() OWNER TO dbuser;

--
-- Name: check_blk(); Type: FUNCTION; Schema: public; Owner: dbuser
--

CREATE FUNCTION check_blk() RETURNS boolean
    LANGUAGE plpgsql
    AS $$
    DECLARE blk_height bigint;        
    DECLARE blk_count bigint;   
    DECLARE blk_id_count bigint;   

    BEGIN
        blk_height = (select max(height) from blk);
        blk_count = (select count(1) from blk);
        blk_id_count = (select count(distinct(blk_id)) from blk_tx);
        IF blk_count != blk_id_count THEN
            RAISE LOG 'blk_count != blk_id_count ';
            return FALSE;
        END IF;

        IF blk_count != blk_height + 1
        THEN
            RAISE LOG 'blk_count != blk_height + 1';
            return FALSE;
        END IF;

        RAISE LOG 'pass blk check';
        return TRUE;
    END;
$$;


ALTER FUNCTION public.check_blk() OWNER TO dbuser;

--
-- Name: check_blk_count(); Type: FUNCTION; Schema: public; Owner: postgres
--

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


ALTER FUNCTION public.check_blk_count() OWNER TO postgres;

--
-- Name: check_db(); Type: FUNCTION; Schema: public; Owner: dbuser
--

CREATE FUNCTION check_db() RETURNS boolean
    LANGUAGE plpgsql
    AS $$
    DECLARE blk_ok BOOL; 
    DECLARE tx_ok BOOL; 
    BEGIN
        blk_ok = (select check_blk());
        IF NOT blk_ok THEN
            return FALSE;
        END IF;

        tx_ok = (select check_tx());
        IF NOT tx_ok THEN
            return FALSE;
        END IF;

        return TRUE;
    END;
$$;


ALTER FUNCTION public.check_db() OWNER TO dbuser;

--
-- Name: check_lost_from_height(integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION check_lost_from_height(blkheight integer) RETURNS integer
    LANGUAGE plpgsql
    AS $$
    DECLARE blkhash bytea;
    DECLARE max_height integer;
    DECLARE curheight integer;
    DECLARE count integer;
    BEGIN
        max_height = (select max(height) from blk);
        LOOP
            IF blkheight <= max_height THEN
                curheight=max_height;
                count = (select count(1) from blk where height=curheight);
                IF count = 0 THEN
                    RAISE LOG 'lost height:%s', curheight;

                    return curheight;
                END IF;
                
                max_height = max_height - 1;
            ELSE
                return TRUE;
            END IF;   
        END LOOP;                                                                                                     
    END;                                                                                                                  
$$;


ALTER FUNCTION public.check_lost_from_height(blkheight integer) OWNER TO postgres;

--
-- Name: check_special_tx(); Type: FUNCTION; Schema: public; Owner: dbuser
--

CREATE FUNCTION check_special_tx() RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE blk_id integer;         

    BEGIN
        FOR blk_id IN select sum(blk.tx_count) as xx from blk where NOT EXISTS(select count(distinct(tx_id)) from blk_tx where blk_tx.blk_id = blk.id)
        LOOP
            RAISE LOG 'blk_id(%)', blk_id;
        END LOOP;
    END;
$$;


ALTER FUNCTION public.check_special_tx() OWNER TO dbuser;

--
-- Name: check_tx(); Type: FUNCTION; Schema: public; Owner: dbuser
--

CREATE FUNCTION check_tx() RETURNS boolean
    LANGUAGE plpgsql
    AS $$
    DECLARE tx_count bigint;        
    DECLARE utx_count bigint;   
    DECLARE blk_tx_count bigint;   
    DECLARE blk_tx_id_count bigint;   

    BEGIN
        blk_tx_count = (select sum(blk.tx_count) from blk);
        blk_tx_id_count = (select count(distinct(tx_id)) from blk_tx);
        IF blk_tx_count != blk_tx_id_count+2 THEN
            RAISE LOG 'blk_tx_count(%) != blk_tx_id_count(%) ', blk_tx_count, blk_tx_id_count;
            return FALSE;
        END IF;

        tx_count = (select count(1) from tx);
        utx_count = (select count(1) from utx);
        IF tx_count + 2 != utx_count + blk_tx_count
        THEN
            RAISE LOG 'tx_count(%) + 2 != utx_count(%) + blk_tx_count(%)', tx_count, utx_count, blk_tx_count;
            return FALSE;
        END IF;

        RAISE LOG 'pass tx check % % %', blk_tx_count, tx_count, utx_count;
        return TRUE;
    END;
$$;


ALTER FUNCTION public.check_tx() OWNER TO dbuser;

--
-- Name: check_tx_count(); Type: FUNCTION; Schema: public; Owner: postgres
--

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


ALTER FUNCTION public.check_tx_count() OWNER TO postgres;

--
-- Name: delete_all_utx(); Type: FUNCTION; Schema: public; Owner: dbuser
--

CREATE FUNCTION delete_all_utx() RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE txid integer;
BEGIN
     FOR txid IN select id from utx LOOP
         perform delete_tx(txid);
     END LOOP;
END;
$$;


ALTER FUNCTION public.delete_all_utx() OWNER TO dbuser;

--
-- Name: delete_blk(bytea); Type: FUNCTION; Schema: public; Owner: dbuser
--

CREATE FUNCTION delete_blk(blkhash bytea) RETURNS void
    LANGUAGE plpgsql
    AS $$                                                                                                                     
    declare blkid integer;                                                                                                    
    declare txid integer;                                                                                                     
    BEGIN                                                                                                                     
    blkid=(select id from blk where hash=blkhash);                                                                            
    txid=(select tx_id from blk_tx where blk_id=blkid and idx=0);                                                             
    insert into utx select tx_id from blk_tx where blk_id=blkid;                                                              
    delete from blk_tx where blk_id=blkid;                                                                                    
    delete from blk where id=blkid;                                                                                           
    perform delete_tx(txid);                                                                                                  
    END                                                                                                                       
$$;


ALTER FUNCTION public.delete_blk(blkhash bytea) OWNER TO dbuser;

--
-- Name: delete_height(integer); Type: FUNCTION; Schema: public; Owner: dbuser
--

CREATE FUNCTION delete_height(blkheight integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
    declare blkhash bytea;
    BEGIN
    blkhash = (select hash from blk where height=blkheight);
    perform delete_blk(blkhash);
    END
$$;


ALTER FUNCTION public.delete_height(blkheight integer) OWNER TO dbuser;

--
-- Name: delete_height_from(integer); Type: FUNCTION; Schema: public; Owner: dbuser
--

CREATE FUNCTION delete_height_from(blkheight integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE blkhash bytea;
    DECLARE max_height integer;
    DECLARE curheight integer;
    BEGIN
        max_height = (select max(height) from blk);
        LOOP
            IF blkheight <= max_height THEN
                curheight=max_height;
                blkhash = (select hash from blk where height=curheight);
                perform delete_blk(blkhash);
                max_height = max_height - 1;
            ELSE
                return;
            END IF;   
        END LOOP;                                                                                                     
    END;                                                                                                                  
$$;


ALTER FUNCTION public.delete_height_from(blkheight integer) OWNER TO dbuser;

--
-- Name: delete_some_utx(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION delete_some_utx() RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE txid integer;
BEGIN
     FOR txid IN select id from utx order by id desc limit 100 LOOP
         perform delete_tx(txid);
     END LOOP;
END;
$$;


ALTER FUNCTION public.delete_some_utx() OWNER TO postgres;

--
-- Name: delete_tx(integer); Type: FUNCTION; Schema: public; Owner: dbuser
--

CREATE FUNCTION delete_tx(txid integer) RETURNS void
    LANGUAGE plpgsql
    AS $_$
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
$_$;


ALTER FUNCTION public.delete_tx(txid integer) OWNER TO dbuser;

--
-- Name: get_confirm(integer); Type: FUNCTION; Schema: public; Owner: dbuser
--

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


ALTER FUNCTION public.get_confirm(txid integer) OWNER TO dbuser;

--
-- Name: insert_addr(text, text); Type: FUNCTION; Schema: public; Owner: dbuser
--

CREATE FUNCTION insert_addr(a text, h text) RETURNS integer
    LANGUAGE plpgsql
    AS $$                                                                                                                     
    declare addrid integer;                                                                                                   
BEGIN                                                                                                                         
    addrid = (select id from addr where address = a);                                                                         
    IF addrid is NULL THEN                                                                                                    
        insert into addr (address, hash160) values(a, h) RETURNING id into addrid;                                            
    END IF;                                                                                                                   
    return addrid;                                                                                                            
END                                                                                                                           
$$;


ALTER FUNCTION public.insert_addr(a text, h text) OWNER TO dbuser;

--
-- Name: rollback_addr_balance(integer); Type: FUNCTION; Schema: public; Owner: dbuser
--

CREATE FUNCTION rollback_addr_balance(txid integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE o RECORD;
BEGIN
    FOR o IN select addr_id, value from vout where txin_tx_id=txid and addr_id is not NULL LOOP
       update addr set balance=(balance + o.value), spent_value=(spent_value-o.value) where id=o.addr_id;
    END LOOP;

    FOR o IN select addr_id, value from vout where txout_tx_id=txid and addr_id is not NULL LOOP
       update addr set balance=(balance - o.value), recv_value=(recv_value-o.value)  where id=o.addr_id;    END LOOP;

    FOR o IN select distinct addr_id from vout where txin_tx_id=txid and addr_id is not NULL LOOP       update addr set spent_count=(spent_count-1) where id=o.addr_id;
       delete from addr_tx where addr_id=o.addr_id and tx_id=txid;
    END LOOP;

    FOR o IN select distinct addr_id from vout where txout_tx_id=txid and addr_id is not NULL LOOP
       update addr set recv_count=(recv_count-1) where id=o.addr_id;
       delete from addr_tx where addr_id=o.addr_id and tx_id=txid;
    END LOOP;
END;
$$;


ALTER FUNCTION public.rollback_addr_balance(txid integer) OWNER TO dbuser;

--
-- Name: tru_utx(); Type: FUNCTION; Schema: public; Owner: dbuser
--

CREATE FUNCTION tru_utx() RETURNS void
    LANGUAGE plpgsql
    AS $$
    declare did integer;
BEGIN
    FOR did IN select id from utx LOOP
      perform delete_tx(did);
    END LOOP;
    truncate table utx;
END;
$$;


ALTER FUNCTION public.tru_utx() OWNER TO dbuser;

--
-- Name: update_addr_balance(integer); Type: FUNCTION; Schema: public; Owner: dbuser
--

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


ALTER FUNCTION public.update_addr_balance(txid integer) OWNER TO dbuser;

--
-- Name: update_stat(); Type: FUNCTION; Schema: public; Owner: postgres
--

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


ALTER FUNCTION public.update_stat() OWNER TO postgres;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: addr; Type: TABLE; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE TABLE addr (
    id integer NOT NULL,
    address text NOT NULL,
    hash160 text NOT NULL,
    balance bigint DEFAULT 0,
    recv_value bigint DEFAULT 0,
    recv_count integer DEFAULT 0,
    spent_value bigint DEFAULT 0,
    spent_count integer DEFAULT 0,
    group_id integer
);


ALTER TABLE addr OWNER TO dbuser;

--
-- Name: addr_id_seq; Type: SEQUENCE; Schema: public; Owner: dbuser
--

CREATE SEQUENCE addr_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE addr_id_seq OWNER TO dbuser;

--
-- Name: addr_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dbuser
--

ALTER SEQUENCE addr_id_seq OWNED BY addr.id;


--
-- Name: addr_tag; Type: TABLE; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE TABLE addr_tag (
    id integer NOT NULL,
    addr text,
    name text,
    link text
);


ALTER TABLE addr_tag OWNER TO dbuser;

--
-- Name: addr_tag_id_seq; Type: SEQUENCE; Schema: public; Owner: dbuser
--

CREATE SEQUENCE addr_tag_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE addr_tag_id_seq OWNER TO dbuser;

--
-- Name: addr_tag_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dbuser
--

ALTER SEQUENCE addr_tag_id_seq OWNED BY addr_tag.id;


--
-- Name: addr_tx; Type: TABLE; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE TABLE addr_tx (
    addr_id integer NOT NULL,
    tx_id integer NOT NULL
);


ALTER TABLE addr_tx OWNER TO dbuser;

--
-- Name: blk_tx; Type: TABLE; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE TABLE blk_tx (
    blk_id integer NOT NULL,
    tx_id integer NOT NULL,
    idx integer NOT NULL
);


ALTER TABLE blk_tx OWNER TO dbuser;

--
-- Name: addr_tx_confirmed; Type: VIEW; Schema: public; Owner: dbuser
--

CREATE VIEW addr_tx_confirmed AS
 SELECT a.tx_id,
    a.addr_id
   FROM (addr_tx a
     JOIN blk_tx b ON ((b.tx_id = a.tx_id)));


ALTER TABLE addr_tx_confirmed OWNER TO dbuser;

--
-- Name: utx; Type: TABLE; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE TABLE utx (
    id integer NOT NULL
);


ALTER TABLE utx OWNER TO dbuser;

--
-- Name: addr_tx_unconfirmed; Type: VIEW; Schema: public; Owner: dbuser
--

CREATE VIEW addr_tx_unconfirmed AS
 SELECT a.tx_id,
    a.addr_id
   FROM (addr_tx a
     JOIN utx b ON ((b.id = a.tx_id)));


ALTER TABLE addr_tx_unconfirmed OWNER TO dbuser;

--
-- Name: addr_txout; Type: TABLE; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE TABLE addr_txout (
    addr_id integer NOT NULL,
    txout_id integer NOT NULL
);


ALTER TABLE addr_txout OWNER TO dbuser;

--
-- Name: tx; Type: TABLE; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE TABLE tx (
    id integer NOT NULL,
    hash bytea NOT NULL,
    version bigint NOT NULL,
    lock_time bigint NOT NULL,
    coinbase boolean NOT NULL,
    tx_size integer NOT NULL,
    in_count integer,
    in_value bigint,
    out_count integer,
    out_value bigint,
    fee bigint,
    recv_time bigint,
    ip text
);


ALTER TABLE tx OWNER TO dbuser;

--
-- Name: txin; Type: TABLE; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE TABLE txin (
    id integer NOT NULL,
    tx_id integer NOT NULL,
    tx_idx integer NOT NULL,
    prev_out_index bigint NOT NULL,
    sequence bigint NOT NULL,
    script_sig bytea,
    prev_out bytea
);


ALTER TABLE txin OWNER TO dbuser;

--
-- Name: txout; Type: TABLE; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE TABLE txout (
    id integer NOT NULL,
    tx_id integer NOT NULL,
    tx_idx integer NOT NULL,
    pk_script bytea NOT NULL,
    value bigint,
    type integer NOT NULL
);


ALTER TABLE txout OWNER TO dbuser;

--
-- Name: vout; Type: VIEW; Schema: public; Owner: dbuser
--

CREATE VIEW vout AS
 SELECT g.address,
    g.id AS addr_id,
    a.id AS txout_id,
    c.id AS txin_id,
    e.id AS txin_tx_id,
    b.id AS txout_tx_id,
    a.value,
    a.tx_idx AS out_idx,
    c.tx_idx AS in_idx,
    e.hash AS txin_tx_hash,
    b.hash AS txout_tx_hash
   FROM (((((txout a
     LEFT JOIN tx b ON ((b.id = a.tx_id)))
     LEFT JOIN txin c ON (((c.prev_out = b.hash) AND (c.prev_out_index = a.tx_idx))))
     LEFT JOIN tx e ON ((e.id = c.tx_id)))
     LEFT JOIN addr_txout f ON ((f.txout_id = a.id)))
     LEFT JOIN addr g ON ((g.id = f.addr_id)));


ALTER TABLE vout OWNER TO dbuser;

--
-- Name: balance; Type: VIEW; Schema: public; Owner: dbuser
--

CREATE VIEW balance AS
 SELECT vout.addr_id,
    sum(vout.value) AS value
   FROM vout
  WHERE (vout.txin_id IS NULL)
  GROUP BY vout.addr_id;


ALTER TABLE balance OWNER TO dbuser;

--
-- Name: bip; Type: TABLE; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE TABLE bip (
    id integer NOT NULL,
    name text NOT NULL,
    link text
);


ALTER TABLE bip OWNER TO dbuser;

--
-- Name: bip_id_seq; Type: SEQUENCE; Schema: public; Owner: dbuser
--

CREATE SEQUENCE bip_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE bip_id_seq OWNER TO dbuser;

--
-- Name: bip_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dbuser
--

ALTER SEQUENCE bip_id_seq OWNED BY bip.id;


--
-- Name: blk; Type: TABLE; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE TABLE blk (
    id integer NOT NULL,
    hash bytea NOT NULL,
    height integer NOT NULL,
    version bigint NOT NULL,
    prev_hash bytea NOT NULL,
    mrkl_root bytea NOT NULL,
    "time" bigint NOT NULL,
    bits bigint NOT NULL,
    nonce bigint NOT NULL,
    blk_size integer NOT NULL,
    work bytea,
    total_in_count integer,
    total_in_value bigint,
    fees bigint,
    total_out_count integer,
    total_out_value bigint,
    tx_count integer,
    pool_id integer,
    recv_time bigint,
    pool_bip integer
);


ALTER TABLE blk OWNER TO dbuser;

--
-- Name: blk_id_seq; Type: SEQUENCE; Schema: public; Owner: dbuser
--

CREATE SEQUENCE blk_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE blk_id_seq OWNER TO dbuser;

--
-- Name: blk_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dbuser
--

ALTER SEQUENCE blk_id_seq OWNED BY blk.id;


--
-- Name: blk_stat; Type: TABLE; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE TABLE blk_stat (
    id integer NOT NULL,
    "timestamp" timestamp without time zone DEFAULT now(),
    max_height integer,
    total_tx_count integer,
    max_blk_id integer,
    max_tx_id integer,
    sum_blk_size bigint,
    sum_tx_size bigint
);


ALTER TABLE blk_stat OWNER TO dbuser;

--
-- Name: blk_stat_id_seq; Type: SEQUENCE; Schema: public; Owner: dbuser
--

CREATE SEQUENCE blk_stat_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE blk_stat_id_seq OWNER TO dbuser;

--
-- Name: blk_stat_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dbuser
--

ALTER SEQUENCE blk_stat_id_seq OWNED BY blk_stat.id;


--
-- Name: m_vout; Type: VIEW; Schema: public; Owner: dbuser
--

CREATE VIEW m_vout AS
 SELECT g.address,
    g.id AS addr_id,
    a.id AS txout_id,
    c.id AS txin_id,
    e.id AS txin_tx_id,
    b.id AS txout_tx_id,
    a.value,
    a.tx_idx AS out_idx,
    c.tx_idx AS in_idx,
    e.hash AS txin_tx_hash,
    b.hash AS txout_tx_hash
   FROM (((((txout a
     LEFT JOIN tx b ON (((b.id = a.tx_id) AND ((b.in_count > 100) OR (b.out_count > 100)))))
     LEFT JOIN txin c ON (((c.prev_out = b.hash) AND (c.prev_out_index = a.tx_idx))))
     LEFT JOIN tx e ON ((e.id = c.tx_id)))
     LEFT JOIN addr_txout f ON ((f.txout_id = a.id)))
     LEFT JOIN addr g ON ((g.id = f.addr_id)));


ALTER TABLE m_vout OWNER TO dbuser;

--
-- Name: pool; Type: TABLE; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE TABLE pool (
    id integer NOT NULL,
    name text NOT NULL,
    link text
);


ALTER TABLE pool OWNER TO dbuser;

--
-- Name: pool_id_seq; Type: SEQUENCE; Schema: public; Owner: dbuser
--

CREATE SEQUENCE pool_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE pool_id_seq OWNER TO dbuser;

--
-- Name: pool_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dbuser
--

ALTER SEQUENCE pool_id_seq OWNED BY pool.id;


--
-- Name: system_cursor; Type: TABLE; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE TABLE system_cursor (
    id integer NOT NULL,
    cursor_name text NOT NULL,
    cursor_id integer NOT NULL
);


ALTER TABLE system_cursor OWNER TO dbuser;

--
-- Name: system_cursor_id_seq; Type: SEQUENCE; Schema: public; Owner: dbuser
--

CREATE SEQUENCE system_cursor_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE system_cursor_id_seq OWNER TO dbuser;

--
-- Name: system_cursor_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dbuser
--

ALTER SEQUENCE system_cursor_id_seq OWNED BY system_cursor.id;


--
-- Name: tx_id_seq; Type: SEQUENCE; Schema: public; Owner: dbuser
--

CREATE SEQUENCE tx_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE tx_id_seq OWNER TO dbuser;

--
-- Name: tx_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dbuser
--

ALTER SEQUENCE tx_id_seq OWNED BY tx.id;


--
-- Name: txin_id_seq; Type: SEQUENCE; Schema: public; Owner: dbuser
--

CREATE SEQUENCE txin_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE txin_id_seq OWNER TO dbuser;

--
-- Name: txin_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dbuser
--

ALTER SEQUENCE txin_id_seq OWNED BY txin.id;


--
-- Name: txout_id_seq; Type: SEQUENCE; Schema: public; Owner: dbuser
--

CREATE SEQUENCE txout_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE txout_id_seq OWNER TO dbuser;

--
-- Name: txout_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dbuser
--

ALTER SEQUENCE txout_id_seq OWNED BY txout.id;


--
-- Name: utxo; Type: VIEW; Schema: public; Owner: dbuser
--

CREATE VIEW utxo AS
 SELECT g.address,
    g.id AS addr_id,
    a.id AS txout_id,
    c.id AS txin_id,
    e.id AS txin_tx_id,
    b.id AS txout_tx_id,
    b.hash AS txout_txhash,
    a.value,
    a.tx_idx,
    blk.height,
    blk."time",
    a.pk_script
   FROM (((((((txout a
     LEFT JOIN tx b ON ((b.id = a.tx_id)))
     LEFT JOIN txin c ON (((c.prev_out = b.hash) AND (c.prev_out_index = a.tx_idx))))
     LEFT JOIN tx e ON ((e.id = c.tx_id)))
     LEFT JOIN addr_txout f ON ((f.txout_id = a.id)))
     LEFT JOIN addr g ON ((g.id = f.addr_id)))
     JOIN blk_tx ON ((blk_tx.tx_id = a.tx_id)))
     JOIN blk ON ((blk.id = blk_tx.blk_id)))
  WHERE (c.id IS NULL);


ALTER TABLE utxo OWNER TO dbuser;

--
-- Name: v_blk; Type: VIEW; Schema: public; Owner: dbuser
--

CREATE VIEW v_blk AS
 SELECT a.id,
    a.hash,
    a.height,
    a.version,
    a.prev_hash,
    a.mrkl_root,
    a."time",
    a.bits,
    a.nonce,
    a.blk_size,
    a.work,
    a.total_in_count,
    a.total_in_value,
    a.fees,
    a.total_out_count,
    a.total_out_value,
    a.tx_count,
    a.pool_id,
    a.recv_time,
    a.pool_bip,
    b.name AS pool_name,
    b.link AS pool_link,
    c.name AS bip_name,
    c.link AS bip_link
   FROM ((blk a
     LEFT JOIN pool b ON ((a.pool_id = b.id)))
     LEFT JOIN bip c ON ((a.pool_bip = c.id)))
  ORDER BY a.height DESC;


ALTER TABLE v_blk OWNER TO dbuser;

--
-- Name: vtx; Type: VIEW; Schema: public; Owner: dbuser
--

CREATE VIEW vtx AS
 SELECT a.id,
    a.hash,
    a.version,
    a.lock_time,
    a.coinbase,
    a.tx_size,
    a.in_count,
    a.in_value,
    a.out_count,
    a.out_value,
    a.fee,
    a.recv_time,
    a.ip,
    b.idx,
    c.height,
    c."time"
   FROM ((tx a
     LEFT JOIN blk_tx b ON ((b.tx_id = a.id)))
     LEFT JOIN blk c ON ((c.id = b.blk_id)));


ALTER TABLE vtx OWNER TO dbuser;

--
-- Name: watched_addr_group; Type: TABLE; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE TABLE watched_addr_group (
    id integer NOT NULL,
    address text NOT NULL,
    groupname text NOT NULL
);


ALTER TABLE watched_addr_group OWNER TO dbuser;

--
-- Name: watched_addr_group_id_seq; Type: SEQUENCE; Schema: public; Owner: dbuser
--

CREATE SEQUENCE watched_addr_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE watched_addr_group_id_seq OWNER TO dbuser;

--
-- Name: watched_addr_group_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dbuser
--

ALTER SEQUENCE watched_addr_group_id_seq OWNED BY watched_addr_group.id;


--
-- Name: watched_addr_tx; Type: TABLE; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE TABLE watched_addr_tx (
    id integer NOT NULL,
    address text NOT NULL,
    tx text NOT NULL
);


ALTER TABLE watched_addr_tx OWNER TO dbuser;

--
-- Name: watched_addr_tx_id_seq; Type: SEQUENCE; Schema: public; Owner: dbuser
--

CREATE SEQUENCE watched_addr_tx_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE watched_addr_tx_id_seq OWNER TO dbuser;

--
-- Name: watched_addr_tx_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: dbuser
--

ALTER SEQUENCE watched_addr_tx_id_seq OWNED BY watched_addr_tx.id;


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: dbuser
--

ALTER TABLE ONLY addr ALTER COLUMN id SET DEFAULT nextval('addr_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: dbuser
--

ALTER TABLE ONLY addr_tag ALTER COLUMN id SET DEFAULT nextval('addr_tag_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: dbuser
--

ALTER TABLE ONLY bip ALTER COLUMN id SET DEFAULT nextval('bip_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: dbuser
--

ALTER TABLE ONLY blk ALTER COLUMN id SET DEFAULT nextval('blk_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: dbuser
--

ALTER TABLE ONLY blk_stat ALTER COLUMN id SET DEFAULT nextval('blk_stat_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: dbuser
--

ALTER TABLE ONLY pool ALTER COLUMN id SET DEFAULT nextval('pool_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: dbuser
--

ALTER TABLE ONLY system_cursor ALTER COLUMN id SET DEFAULT nextval('system_cursor_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: dbuser
--

ALTER TABLE ONLY tx ALTER COLUMN id SET DEFAULT nextval('tx_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: dbuser
--

ALTER TABLE ONLY txin ALTER COLUMN id SET DEFAULT nextval('txin_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: dbuser
--

ALTER TABLE ONLY txout ALTER COLUMN id SET DEFAULT nextval('txout_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: dbuser
--

ALTER TABLE ONLY watched_addr_group ALTER COLUMN id SET DEFAULT nextval('watched_addr_group_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: dbuser
--

ALTER TABLE ONLY watched_addr_tx ALTER COLUMN id SET DEFAULT nextval('watched_addr_tx_id_seq'::regclass);


--
-- Name: addr_tag_pkey; Type: CONSTRAINT; Schema: public; Owner: dbuser; Tablespace: 
--

ALTER TABLE ONLY addr_tag
    ADD CONSTRAINT addr_tag_pkey PRIMARY KEY (id);


--
-- Name: blk_pkey; Type: CONSTRAINT; Schema: public; Owner: dbuser; Tablespace: 
--

ALTER TABLE ONLY blk
    ADD CONSTRAINT blk_pkey PRIMARY KEY (id);


--
-- Name: blk_stat_pkey; Type: CONSTRAINT; Schema: public; Owner: dbuser; Tablespace: 
--

ALTER TABLE ONLY blk_stat
    ADD CONSTRAINT blk_stat_pkey PRIMARY KEY (id);


--
-- Name: id; Type: CONSTRAINT; Schema: public; Owner: dbuser; Tablespace: 
--

ALTER TABLE ONLY utx
    ADD CONSTRAINT id UNIQUE (id);


--
-- Name: naddr_pkey; Type: CONSTRAINT; Schema: public; Owner: dbuser; Tablespace: 
--

ALTER TABLE ONLY addr
    ADD CONSTRAINT naddr_pkey PRIMARY KEY (id);


--
-- Name: system_cursor_cursor_name_cursor_id_key; Type: CONSTRAINT; Schema: public; Owner: dbuser; Tablespace: 
--

ALTER TABLE ONLY system_cursor
    ADD CONSTRAINT system_cursor_cursor_name_cursor_id_key UNIQUE (cursor_name, cursor_id);


--
-- Name: tx_pkey; Type: CONSTRAINT; Schema: public; Owner: dbuser; Tablespace: 
--

ALTER TABLE ONLY tx
    ADD CONSTRAINT tx_pkey PRIMARY KEY (id);


--
-- Name: txin_pkey; Type: CONSTRAINT; Schema: public; Owner: dbuser; Tablespace: 
--

ALTER TABLE ONLY txin
    ADD CONSTRAINT txin_pkey PRIMARY KEY (id);


--
-- Name: txout_pkey; Type: CONSTRAINT; Schema: public; Owner: dbuser; Tablespace: 
--

ALTER TABLE ONLY txout
    ADD CONSTRAINT txout_pkey PRIMARY KEY (id);


--
-- Name: u_constrainte; Type: CONSTRAINT; Schema: public; Owner: dbuser; Tablespace: 
--

ALTER TABLE ONLY addr_tx
    ADD CONSTRAINT u_constrainte UNIQUE (addr_id, tx_id);


--
-- Name: uniq_addr_address; Type: CONSTRAINT; Schema: public; Owner: dbuser; Tablespace: 
--

ALTER TABLE ONLY addr
    ADD CONSTRAINT uniq_addr_address UNIQUE (address);


--
-- Name: uniq_blk_hash; Type: CONSTRAINT; Schema: public; Owner: dbuser; Tablespace: 
--

ALTER TABLE ONLY blk
    ADD CONSTRAINT uniq_blk_hash UNIQUE (hash);


--
-- Name: uniq_tx_hash; Type: CONSTRAINT; Schema: public; Owner: dbuser; Tablespace: 
--

ALTER TABLE ONLY tx
    ADD CONSTRAINT uniq_tx_hash UNIQUE (hash);


--
-- Name: watched_addr_group_address_groupname_key; Type: CONSTRAINT; Schema: public; Owner: dbuser; Tablespace: 
--

ALTER TABLE ONLY watched_addr_group
    ADD CONSTRAINT watched_addr_group_address_groupname_key UNIQUE (address, groupname);


--
-- Name: watched_addr_tx_address_tx_key; Type: CONSTRAINT; Schema: public; Owner: dbuser; Tablespace: 
--

ALTER TABLE ONLY watched_addr_tx
    ADD CONSTRAINT watched_addr_tx_address_tx_key UNIQUE (address, tx);


--
-- Name: addr_txout_index; Type: INDEX; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE UNIQUE INDEX addr_txout_index ON addr_txout USING btree (addr_id, txout_id);


--
-- Name: blk_hash_index; Type: INDEX; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE INDEX blk_hash_index ON blk USING btree (hash);


--
-- Name: blk_height_index; Type: INDEX; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE INDEX blk_height_index ON blk USING btree (height);


--
-- Name: blk_prev_hash_index; Type: INDEX; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE INDEX blk_prev_hash_index ON blk USING btree (prev_hash);


--
-- Name: blk_tx_blk_id_index; Type: INDEX; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE INDEX blk_tx_blk_id_index ON blk_tx USING btree (blk_id);


--
-- Name: blk_tx_tx_id_index; Type: INDEX; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE INDEX blk_tx_tx_id_index ON blk_tx USING btree (tx_id);


--
-- Name: inaddr_txout_index; Type: INDEX; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE INDEX inaddr_txout_index ON addr_txout USING btree (txout_id);


--
-- Name: txin_prev_out_index; Type: INDEX; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE INDEX txin_prev_out_index ON txin USING btree (prev_out);


--
-- Name: txin_txid_index; Type: INDEX; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE INDEX txin_txid_index ON txin USING btree (tx_id);


--
-- Name: txout_txid_idx_index; Type: INDEX; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE INDEX txout_txid_idx_index ON txout USING btree (tx_id, tx_idx);


--
-- Name: txout_txid_index; Type: INDEX; Schema: public; Owner: dbuser; Tablespace: 
--

CREATE INDEX txout_txid_index ON txout USING btree (tx_id);


--
-- Name: addr_tx_on_duplicate_ignore; Type: RULE; Schema: public; Owner: dbuser
--

CREATE RULE addr_tx_on_duplicate_ignore AS
    ON INSERT TO addr_tx
   WHERE (EXISTS ( SELECT 1
           FROM addr_tx
          WHERE ((addr_tx.addr_id = new.addr_id) AND (addr_tx.tx_id = new.tx_id)))) DO INSTEAD NOTHING;


--
-- Name: addr_txout_on_duplicate_ignore; Type: RULE; Schema: public; Owner: dbuser
--

CREATE RULE addr_txout_on_duplicate_ignore AS
    ON INSERT TO addr_txout
   WHERE (EXISTS ( SELECT 1
           FROM addr_txout
          WHERE ((addr_txout.addr_id = new.addr_id) AND (addr_txout.txout_id = new.txout_id)))) DO INSTEAD NOTHING;


--
-- Name: utx_on_duplicate_ignore; Type: RULE; Schema: public; Owner: dbuser
--

CREATE RULE utx_on_duplicate_ignore AS
    ON INSERT TO utx
   WHERE (EXISTS ( SELECT 1
           FROM utx
          WHERE (utx.id = new.id))) DO INSTEAD NOTHING;


--
-- Name: public; Type: ACL; Schema: -; Owner: dbuser
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM dbuser;
GRANT ALL ON SCHEMA public TO dbuser;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

