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
-- Name: delete_tx(integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION delete_tx(txid integer) RETURNS void
    LANGUAGE sql
    AS $$
     delete from addr_txout where txout_id in (select id from txout where tx_id=txid);

     delete from txin where tx_id=txid;

     delete from txout where tx_id=txid; 

     delete from tx where id=txid; 

$$;


ALTER FUNCTION public.delete_tx(txid integer) OWNER TO postgres;

--
-- Name: update_blk(integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_blk(h integer) RETURNS void
    LANGUAGE sql
    AS $$
  update blk set tx_num=blk_in.tx_num, txin_num=blk_in.txin_num, txin_value=blk_in.txin_value from blk_in where blk_in.height=h;

  update blk set txin_num=blk_out.txout_num, txout_value=blk_out.txout_value from blk_out where blk_out.height=h;

$$;


ALTER FUNCTION public.update_blk(h integer) OWNER TO postgres;

--
-- Name: update_tx(integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_tx(txid integer) RETURNS void
    LANGUAGE sql
    AS $$
  update tx set txin_num=tx_inv.txin_num, txin_value=tx_inv.txin_value from tx_inv where tx_inv.id=txid;

  update tx set txout_num=tx_outv.txout_num, txout_value=tx_outv.txout_value from tx_outv where tx_outv.id=txid;

$$;


ALTER FUNCTION public.update_tx(txid integer) OWNER TO postgres;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: addr; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE addr (
    id integer NOT NULL,
    hash160 text NOT NULL,
    type integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.addr OWNER TO postgres;

--
-- Name: addr_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE addr_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.addr_id_seq OWNER TO postgres;

--
-- Name: addr_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE addr_id_seq OWNED BY addr.id;


--
-- Name: addr_txout; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE addr_txout (
    addr_id integer NOT NULL,
    txout_id integer NOT NULL
);


ALTER TABLE public.addr_txout OWNER TO postgres;

--
-- Name: tx; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE tx (
    id integer NOT NULL,
    hash bytea NOT NULL,
    version bigint NOT NULL,
    lock_time bigint NOT NULL,
    coinbase boolean NOT NULL,
    tx_size integer NOT NULL,
    nhash bytea,
    txin_num integer,
    txin_value bigint,
    txout_num integer,
    txout_value bigint
);


ALTER TABLE public.tx OWNER TO postgres;

--
-- Name: txin; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE txin (
    id integer NOT NULL,
    tx_id integer NOT NULL,
    tx_idx integer NOT NULL,
    prev_out_index bigint NOT NULL,
    sequence bigint NOT NULL,
    script_sig bytea,
    prev_out bytea,
    p2sh_type integer
);


ALTER TABLE public.txin OWNER TO postgres;

--
-- Name: txout; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE txout (
    id integer NOT NULL,
    tx_id integer NOT NULL,
    tx_idx integer NOT NULL,
    pk_script bytea NOT NULL,
    value bigint,
    type integer NOT NULL
);


ALTER TABLE public.txout OWNER TO postgres;

--
-- Name: vout; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW vout AS
 SELECT addr.hash160,
    addr_txout.addr_id,
    b.id AS txout_id,
    txin.id AS txin_id,
    tx.id AS tx_id,
    b.value
   FROM ((((txin
     JOIN tx ON ((tx.hash = txin.prev_out)))
     RIGHT JOIN txout b ON (((b.tx_id = tx.id) AND (b.tx_idx = txin.prev_out_index))))
     JOIN addr_txout ON ((addr_txout.txout_id = b.id)))
     JOIN addr ON ((addr.id = addr_txout.addr_id)));


ALTER TABLE public.vout OWNER TO postgres;

--
-- Name: b; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW b AS
 SELECT vout.hash160,
    sum(vout.value) AS balance
   FROM vout
  WHERE (vout.txin_id IS NULL)
  GROUP BY vout.hash160;


ALTER TABLE public.b OWNER TO postgres;

--
-- Name: vvout; Type: MATERIALIZED VIEW; Schema: public; Owner: postgres; Tablespace: 
--

CREATE MATERIALIZED VIEW vvout AS
 SELECT addr.hash160,
    addr_txout.addr_id,
    b.id AS txout_id,
    txin.id AS txin_id,
    tx.id AS tx_id,
    b.value
   FROM ((((txin
     JOIN tx ON ((tx.hash = txin.prev_out)))
     RIGHT JOIN txout b ON (((b.tx_id = tx.id) AND (b.tx_idx = txin.prev_out_index))))
     JOIN addr_txout ON ((addr_txout.txout_id = b.id)))
     JOIN addr ON ((addr.id = addr_txout.addr_id)))
  WITH NO DATA;


ALTER TABLE public.vvout OWNER TO postgres;

--
-- Name: balance; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW balance AS
 SELECT vvout.hash160,
    sum(vvout.value) AS balance
   FROM vvout
  WHERE (vvout.txin_id IS NULL)
  GROUP BY vvout.hash160;


ALTER TABLE public.balance OWNER TO postgres;

--
-- Name: blk; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
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
    chain integer NOT NULL,
    work bytea,
    txin_num integer,
    txin_value bigint,
    txout_num integer,
    txout_value bigint,
    tx_num integer,
    blk_fee bigint
);


ALTER TABLE public.blk OWNER TO postgres;

--
-- Name: blk_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE blk_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.blk_id_seq OWNER TO postgres;

--
-- Name: blk_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE blk_id_seq OWNED BY blk.id;


--
-- Name: blk_in; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE blk_in (
    height integer,
    tx_num bigint,
    txin_num bigint,
    txin_value numeric
);


ALTER TABLE public.blk_in OWNER TO postgres;

--
-- Name: blk_out; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE blk_out (
    height integer,
    tx_num bigint,
    txout_num bigint,
    txout_value numeric
);


ALTER TABLE public.blk_out OWNER TO postgres;

--
-- Name: blk_tx; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE blk_tx (
    blk_id integer NOT NULL,
    tx_id integer NOT NULL,
    idx integer NOT NULL
);


ALTER TABLE public.blk_tx OWNER TO postgres;

--
-- Name: inout; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW "inout" AS
 SELECT txin.id AS txin_id,
    tx.id AS tx_id,
    b.id AS txout_id
   FROM ((txin
     JOIN tx ON ((tx.hash = txin.prev_out)))
     JOIN txout b ON (((b.tx_id = tx.id) AND (b.tx_idx = txin.prev_out_index))));


ALTER TABLE public."inout" OWNER TO postgres;

--
-- Name: orphan; Type: MATERIALIZED VIEW; Schema: public; Owner: postgres; Tablespace: 
--

CREATE MATERIALIZED VIEW orphan AS
 SELECT l.blk_id,
    l.tx_id
   FROM blk_tx l
  WHERE (NOT (EXISTS ( SELECT 1
           FROM blk i
          WHERE (l.blk_id = i.id))))
  WITH NO DATA;


ALTER TABLE public.orphan OWNER TO postgres;

--
-- Name: tx_inv; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE tx_inv (
    id integer,
    hash bytea,
    txin_num bigint,
    txin_value numeric
);


ALTER TABLE public.tx_inv OWNER TO postgres;

--
-- Name: tx_outv; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE tx_outv (
    id integer,
    hash bytea,
    txout_num bigint,
    txout_value numeric
);


ALTER TABLE public.tx_outv OWNER TO postgres;

--
-- Name: tx_fee; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW tx_fee AS
 SELECT tx_inv.id,
    (tx_inv.txin_value - tx_outv.txout_value) AS fee
   FROM (tx_inv
     JOIN tx_outv ON ((tx_outv.id = tx_inv.id)));


ALTER TABLE public.tx_fee OWNER TO postgres;

--
-- Name: tx_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE tx_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tx_id_seq OWNER TO postgres;

--
-- Name: tx_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE tx_id_seq OWNED BY tx.id;


--
-- Name: txin_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE txin_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.txin_id_seq OWNER TO postgres;

--
-- Name: txin_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE txin_id_seq OWNED BY txin.id;


--
-- Name: txout_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE txout_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.txout_id_seq OWNER TO postgres;

--
-- Name: txout_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE txout_id_seq OWNED BY txout.id;


--
-- Name: utx; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW utx AS
 SELECT l.id
   FROM tx l
  WHERE (NOT (EXISTS ( SELECT 1
           FROM blk_tx i
          WHERE (l.id = i.tx_id))));


ALTER TABLE public.utx OWNER TO postgres;

--
-- Name: id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY addr ALTER COLUMN id SET DEFAULT nextval('addr_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY blk ALTER COLUMN id SET DEFAULT nextval('blk_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY tx ALTER COLUMN id SET DEFAULT nextval('tx_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY txin ALTER COLUMN id SET DEFAULT nextval('txin_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY txout ALTER COLUMN id SET DEFAULT nextval('txout_id_seq'::regclass);


--
-- Name: addr_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY addr
    ADD CONSTRAINT addr_pkey PRIMARY KEY (id);


--
-- Name: blk_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY blk
    ADD CONSTRAINT blk_pkey PRIMARY KEY (id);


--
-- Name: tx_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY tx
    ADD CONSTRAINT tx_pkey PRIMARY KEY (id);


--
-- Name: txin_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY txin
    ADD CONSTRAINT txin_pkey PRIMARY KEY (id);


--
-- Name: txout_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY txout
    ADD CONSTRAINT txout_pkey PRIMARY KEY (id);


--
-- Name: addr_hash160_index; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX addr_hash160_index ON addr USING btree (hash160);


--
-- Name: addr_txout_addr_id_index; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX addr_txout_addr_id_index ON addr_txout USING btree (addr_id);


--
-- Name: addr_txout_txout_id_index; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX addr_txout_txout_id_index ON addr_txout USING btree (txout_id);


--
-- Name: blk_hash_index; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX blk_hash_index ON blk USING btree (hash);


--
-- Name: blk_height_index; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX blk_height_index ON blk USING btree (height);


--
-- Name: blk_prev_hash_index; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX blk_prev_hash_index ON blk USING btree (prev_hash);


--
-- Name: blk_tx_blk_id_index; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX blk_tx_blk_id_index ON blk_tx USING btree (blk_id);


--
-- Name: blk_tx_tx_id_index; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX blk_tx_tx_id_index ON blk_tx USING btree (tx_id);


--
-- Name: tx_hash_index; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX tx_hash_index ON tx USING btree (hash);


--
-- Name: txin_prev_out_index; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX txin_prev_out_index ON txin USING btree (prev_out);


--
-- Name: txin_txid_index; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX txin_txid_index ON txin USING btree (tx_id);


--
-- Name: txout_txid_idx_index; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX txout_txid_idx_index ON txout USING btree (tx_id, tx_idx);


--
-- Name: txout_txid_index; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX txout_txid_index ON txout USING btree (tx_id);


--
-- Name: vvout_hash160; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX vvout_hash160 ON vvout USING btree (hash160);


--
-- Name: _RETURN; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE "_RETURN" AS
    ON SELECT TO blk_out DO INSTEAD  SELECT blk.height,
    count(DISTINCT blk_tx.tx_id) AS tx_num,
    count(txout.id) AS txout_num,
    sum(txout.value) AS txout_value
   FROM ((blk
     JOIN blk_tx ON ((blk_tx.blk_id = blk.id)))
     LEFT JOIN txout ON ((txout.tx_id = blk_tx.tx_id)))
  GROUP BY blk.id;


--
-- Name: _RETURN; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE "_RETURN" AS
    ON SELECT TO blk_in DO INSTEAD  SELECT blk.height,
    count(DISTINCT blk_tx.tx_id) AS tx_num,
    count(txin.id) AS txin_num,
    sum(txout.value) AS txin_value
   FROM ((((blk
     JOIN blk_tx ON ((blk_tx.blk_id = blk.id)))
     JOIN txin ON ((txin.tx_id = blk_tx.tx_id)))
     JOIN tx ON ((tx.hash = txin.prev_out)))
     JOIN txout ON (((txout.tx_id = tx.id) AND (txout.tx_idx = txin.prev_out_index))))
  GROUP BY blk.id;


--
-- Name: _RETURN; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE "_RETURN" AS
    ON SELECT TO tx_inv DO INSTEAD  SELECT a.id,
    a.hash,
    count(txin.id) AS txin_num,
    sum(txout.value) AS txin_value
   FROM (((tx a
     JOIN txin ON ((txin.tx_id = a.id)))
     JOIN tx b ON ((b.hash = txin.prev_out)))
     JOIN txout ON (((txout.tx_id = b.id) AND (txout.tx_idx = txin.prev_out_index))))
  GROUP BY a.id;


--
-- Name: _RETURN; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE "_RETURN" AS
    ON SELECT TO tx_outv DO INSTEAD  SELECT tx.id,
    tx.hash,
    count(txout.id) AS txout_num,
    sum(txout.value) AS txout_value
   FROM (tx
     JOIN txout ON ((txout.tx_id = tx.id)))
  GROUP BY tx.id;


--
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

