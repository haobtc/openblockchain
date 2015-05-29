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

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: addr; Type: TABLE; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE TABLE addr (
    id integer NOT NULL,
    hash160 text NOT NULL,
    type integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.addr OWNER TO bitcoin;

--
-- Name: addr_id_seq; Type: SEQUENCE; Schema: public; Owner: bitcoin
--

CREATE SEQUENCE addr_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.addr_id_seq OWNER TO bitcoin;

--
-- Name: addr_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: bitcoin
--

ALTER SEQUENCE addr_id_seq OWNED BY addr.id;


--
-- Name: addr_txout; Type: TABLE; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE TABLE addr_txout (
    addr_id integer NOT NULL,
    txout_id integer NOT NULL
);


ALTER TABLE public.addr_txout OWNER TO bitcoin;

--
-- Name: blk; Type: TABLE; Schema: public; Owner: bitcoin; Tablespace: 
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
    work bytea
);


ALTER TABLE public.blk OWNER TO bitcoin;

--
-- Name: blk_id_seq; Type: SEQUENCE; Schema: public; Owner: bitcoin
--

CREATE SEQUENCE blk_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.blk_id_seq OWNER TO bitcoin;

--
-- Name: blk_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: bitcoin
--

ALTER SEQUENCE blk_id_seq OWNED BY blk.id;


--
-- Name: blk_tx; Type: TABLE; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE TABLE blk_tx (
    blk_id integer NOT NULL,
    tx_id integer NOT NULL,
    idx integer NOT NULL
);


ALTER TABLE public.blk_tx OWNER TO bitcoin;

--
-- Name: names; Type: TABLE; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE TABLE names (
    txout_id integer NOT NULL,
    hash bytea,
    name bytea,
    value bytea
);


ALTER TABLE public.names OWNER TO bitcoin;

--
-- Name: schema_info; Type: TABLE; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE TABLE schema_info (
    version integer DEFAULT 0 NOT NULL,
    magic character varying(255),
    backend character varying(255)
);


ALTER TABLE public.schema_info OWNER TO bitcoin;

--
-- Name: tx; Type: TABLE; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE TABLE tx (
    id integer NOT NULL,
    hash bytea NOT NULL,
    version bigint NOT NULL,
    lock_time bigint NOT NULL,
    coinbase boolean NOT NULL,
    tx_size integer NOT NULL,
    nhash bytea
);


ALTER TABLE public.tx OWNER TO bitcoin;

--
-- Name: tx_id_seq; Type: SEQUENCE; Schema: public; Owner: bitcoin
--

CREATE SEQUENCE tx_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tx_id_seq OWNER TO bitcoin;

--
-- Name: tx_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: bitcoin
--

ALTER SEQUENCE tx_id_seq OWNED BY tx.id;


--
-- Name: txin; Type: TABLE; Schema: public; Owner: bitcoin; Tablespace: 
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


ALTER TABLE public.txin OWNER TO bitcoin;

--
-- Name: txin_id_seq; Type: SEQUENCE; Schema: public; Owner: bitcoin
--

CREATE SEQUENCE txin_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.txin_id_seq OWNER TO bitcoin;

--
-- Name: txin_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: bitcoin
--

ALTER SEQUENCE txin_id_seq OWNED BY txin.id;


--
-- Name: txout; Type: TABLE; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE TABLE txout (
    id integer NOT NULL,
    tx_id integer NOT NULL,
    tx_idx integer NOT NULL,
    pk_script bytea NOT NULL,
    value bigint,
    type integer NOT NULL
);


ALTER TABLE public.txout OWNER TO bitcoin;

--
-- Name: txout_id_seq; Type: SEQUENCE; Schema: public; Owner: bitcoin
--

CREATE SEQUENCE txout_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.txout_id_seq OWNER TO bitcoin;

--
-- Name: txout_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: bitcoin
--

ALTER SEQUENCE txout_id_seq OWNED BY txout.id;


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: bitcoin
--

ALTER TABLE ONLY addr ALTER COLUMN id SET DEFAULT nextval('addr_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: bitcoin
--

ALTER TABLE ONLY blk ALTER COLUMN id SET DEFAULT nextval('blk_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: bitcoin
--

ALTER TABLE ONLY tx ALTER COLUMN id SET DEFAULT nextval('tx_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: bitcoin
--

ALTER TABLE ONLY txin ALTER COLUMN id SET DEFAULT nextval('txin_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: bitcoin
--

ALTER TABLE ONLY txout ALTER COLUMN id SET DEFAULT nextval('txout_id_seq'::regclass);


--
-- Name: addr_hash160_index; Type: INDEX; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE INDEX addr_hash160_index ON addr USING btree (hash160);


--
-- Name: addr_hash160_type_index; Type: INDEX; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE INDEX addr_hash160_type_index ON addr USING btree (hash160, type);


--
-- Name: addr_txout_addr_id_index; Type: INDEX; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE INDEX addr_txout_addr_id_index ON addr_txout USING btree (addr_id);


--
-- Name: addr_txout_txout_id_index; Type: INDEX; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE INDEX addr_txout_txout_id_index ON addr_txout USING btree (txout_id);


--
-- Name: blk_height_index; Type: INDEX; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE INDEX blk_height_index ON blk USING btree (height);


--
-- Name: blk_hash_index; Type: INDEX; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE INDEX blk_hash_index ON blk USING btree (hash);


--
-- Name: blk_prev_hash_index; Type: INDEX; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE INDEX blk_prev_hash_index ON blk USING btree (prev_hash);


--
-- Name: blk_tx_blk_id_index; Type: INDEX; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE INDEX blk_tx_blk_id_index ON blk_tx USING btree (blk_id);


--
-- Name: blk_tx_tx_id_index; Type: INDEX; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE INDEX blk_tx_tx_id_index ON blk_tx USING btree (tx_id);


--
-- Name: names_hash_index; Type: INDEX; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE INDEX names_hash_index ON names USING btree (hash);


--
-- Name: names_name_index; Type: INDEX; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE INDEX names_name_index ON names USING btree (name);


--
-- Name: names_txout_id_index; Type: INDEX; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE INDEX names_txout_id_index ON names USING btree (txout_id);


--
-- Name: tx_hash_index; Type: INDEX; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE INDEX tx_hash_index ON tx USING btree (hash);


--
-- Name: txin_id_p2sh_type_index; Type: INDEX; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE INDEX txin_id_p2sh_type_index ON txin USING btree (id, p2sh_type);


--mempool create start


--
-- Name: uaddr; Type: TABLE; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE TABLE uaddr (
    id integer NOT NULL,
    hash160 text NOT NULL,
    type integer DEFAULT 0 NOT NULL
);

ALTER TABLE public.uaddr OWNER TO bitcoin;

--
-- Name: uaddr_id_seq; Type: SEQUENCE; Schema: public; Owner: bitcoin
--

CREATE SEQUENCE uaddr_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.uaddr_id_seq OWNER TO bitcoin;

--
-- Name: uaddr_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: bitcoin
--

ALTER SEQUENCE uaddr_id_seq OWNED BY uaddr.id;

--
-- Name: uaddr_txout; Type: TABLE; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE TABLE uaddr_txout (
    addr_id integer NOT NULL,
    txout_id integer NOT NULL
);


ALTER TABLE public.uaddr_txout OWNER TO bitcoin;


--
-- Name: utx; Type: TABLE; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE TABLE utx (
    id integer NOT NULL,
    hash bytea NOT NULL,
    version bigint NOT NULL,
    lock_time bigint NOT NULL,
    coinbase boolean NOT NULL,
    tx_size integer NOT NULL,
    nhash bytea
);


ALTER TABLE public.utx OWNER TO bitcoin;

--
-- Name: utx_id_seq; Type: SEQUENCE; Schema: public; Owner: bitcoin
--

CREATE SEQUENCE utx_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.utx_id_seq OWNER TO bitcoin;

--
-- Name: utx_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: bitcoin
--

ALTER SEQUENCE utx_id_seq OWNED BY utx.id;


--
-- Name: utxin; Type: TABLE; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE TABLE utxin (
    id integer NOT NULL,
    tx_id integer NOT NULL,
    tx_idx integer NOT NULL,
    prev_out_index bigint NOT NULL,
    sequence bigint NOT NULL,
    script_sig bytea,
    prev_out bytea,
    p2sh_type integer
);


ALTER TABLE public.utxin OWNER TO bitcoin;

--
-- Name: utxin_id_seq; Type: SEQUENCE; Schema: public; Owner: bitcoin
--

CREATE SEQUENCE utxin_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.utxin_id_seq OWNER TO bitcoin;

--
-- Name: utxin_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: bitcoin
--

ALTER SEQUENCE utxin_id_seq OWNED BY utxin.id;


--
-- Name: utxout; Type: TABLE; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE TABLE utxout (
    id integer NOT NULL,
    tx_id integer NOT NULL,
    tx_idx integer NOT NULL,
    pk_script bytea NOT NULL,
    value bigint,
    type integer NOT NULL
);


ALTER TABLE public.utxout OWNER TO bitcoin;

--
-- Name: utxout_id_seq; Type: SEQUENCE; Schema: public; Owner: bitcoin
--

CREATE SEQUENCE utxout_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.utxout_id_seq OWNER TO bitcoin;

--
-- Name: utxout_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: bitcoin
--

ALTER SEQUENCE utxout_id_seq OWNED BY utxout.id;


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: bitcoin
--

ALTER TABLE ONLY uaddr ALTER COLUMN id SET DEFAULT nextval('uaddr_id_seq'::regclass);

--
-- Name: id; Type: DEFAULT; Schema: public; Owner: bitcoin
--

ALTER TABLE ONLY utx ALTER COLUMN id SET DEFAULT nextval('utx_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: bitcoin
--

ALTER TABLE ONLY utxin ALTER COLUMN id SET DEFAULT nextval('utxin_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: bitcoin
--

ALTER TABLE ONLY utxout ALTER COLUMN id SET DEFAULT nextval('utxout_id_seq'::regclass);


--
-- Name: uaddr_hash160_index; Type: INDEX; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE INDEX uaddr_hash160_index ON uaddr USING btree (hash160);


--
-- Name: uaddr_hash160_type_index; Type: INDEX; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE INDEX uaddr_hash160_type_index ON uaddr USING btree (hash160, type);


--
-- Name: uaddr_txout_addr_id_index; Type: INDEX; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE INDEX uaddr_txout_addr_id_index ON uaddr_txout USING btree (addr_id);


--
-- Name: uaddr_txout_txout_id_index; Type: INDEX; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE INDEX uaddr_txout_txout_id_index ON uaddr_txout USING btree (txout_id);


--
-- Name: utx_hash_index; Type: INDEX; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE INDEX utx_hash_index ON utx USING btree (hash);


--
-- Name: utxin_id_p2sh_type_index; Type: INDEX; Schema: public; Owner: bitcoin; Tablespace: 
--

CREATE INDEX utxin_id_p2sh_type_index ON utxin USING btree (id, p2sh_type);
 

--mempool create end

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

