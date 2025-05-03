CREATE TABLE users (
    id bigint NOT NULL,
    telegram_id bigint NOT NULL,
    username character varying(255),
    role character varying(50) DEFAULT 'user'::character varying NOT NULL
);

CREATE SEQUENCE users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE users_id_seq OWNER TO postgres;

ALTER SEQUENCE users_id_seq OWNED BY users.id;

ALTER TABLE ONLY users ALTER COLUMN id SET DEFAULT nextval('users_id_seq'::regclass);

ALTER TABLE ONLY users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);

ALTER TABLE ONLY users
    ADD CONSTRAINT users_telegram_id_key UNIQUE (telegram_id);

-- Table: polls

CREATE TABLE polls (
    id bigint NOT NULL,
    title text NOT NULL,
    creator_id bigint NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    end_time timestamp without time zone NOT NULL,
    is_active boolean DEFAULT true,
    is_private boolean DEFAULT false,
    allow_custom boolean DEFAULT false,
    vote_type character varying(20),
    data_type character varying(20)
);

ALTER TABLE polls OWNER TO postgres;

CREATE SEQUENCE polls_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE polls_id_seq OWNER TO postgres;

ALTER SEQUENCE polls_id_seq OWNED BY polls.id;

ALTER TABLE ONLY polls ALTER COLUMN id SET DEFAULT nextval('polls_id_seq'::regclass);

ALTER TABLE ONLY polls
    ADD CONSTRAINT polls_pkey PRIMARY KEY (id);

-- Table: poll_options

CREATE TABLE poll_options (
    id bigint NOT NULL,
    poll_id bigint NOT NULL,
    option_text text NOT NULL,
    is_custom boolean DEFAULT false
);

ALTER TABLE poll_options OWNER TO postgres;

CREATE SEQUENCE poll_options_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE poll_options_id_seq OWNER TO postgres;

ALTER SEQUENCE poll_options_id_seq OWNED BY poll_options.id;

ALTER TABLE ONLY poll_options ALTER COLUMN id SET DEFAULT nextval('poll_options_id_seq'::regclass);

ALTER TABLE ONLY poll_options
    ADD CONSTRAINT poll_options_pkey PRIMARY KEY (id);

-- Table: poll_settings

CREATE TABLE poll_settings (
    poll_id bigint NOT NULL,
    allow_custom boolean DEFAULT false
);

ALTER TABLE poll_settings OWNER TO postgres;

ALTER TABLE ONLY poll_settings
    ADD CONSTRAINT poll_settings_pkey PRIMARY KEY (poll_id);

-- Table: poll_participants

CREATE TABLE poll_participants (
    poll_id bigint NOT NULL,
    user_id bigint NOT NULL
);

ALTER TABLE poll_participants OWNER TO postgres;

ALTER TABLE ONLY poll_participants
    ADD CONSTRAINT poll_participants_pkey PRIMARY KEY (poll_id, user_id);

-- Table: votes

CREATE TABLE votes (
    id bigint NOT NULL,
    poll_id bigint NOT NULL,
    user_id bigint NOT NULL,
    option_id bigint NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE votes OWNER TO postgres;

CREATE SEQUENCE votes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE votes_id_seq OWNER TO postgres;

ALTER SEQUENCE votes_id_seq OWNED BY votes.id;

ALTER TABLE ONLY votes ALTER COLUMN id SET DEFAULT nextval('votes_id_seq'::regclass);

ALTER TABLE ONLY votes
    ADD CONSTRAINT votes_pkey PRIMARY KEY (id);

ALTER TABLE ONLY votes
    ADD CONSTRAINT votes_poll_id_user_id_key UNIQUE (poll_id, user_id);

-- Foreign keys

ALTER TABLE ONLY poll_options
    ADD CONSTRAINT poll_options_poll_id_fkey FOREIGN KEY (poll_id) REFERENCES polls(id) ON DELETE CASCADE;

ALTER TABLE ONLY poll_participants
    ADD CONSTRAINT poll_participants_poll_id_fkey FOREIGN KEY (poll_id) REFERENCES polls(id);

ALTER TABLE ONLY poll_settings
    ADD CONSTRAINT poll_settings_poll_id_fkey FOREIGN KEY (poll_id) REFERENCES polls(id);

ALTER TABLE ONLY polls
    ADD CONSTRAINT polls_creator_id_fkey FOREIGN KEY (creator_id) REFERENCES users(telegram_id) ON DELETE CASCADE;

ALTER TABLE ONLY votes
    ADD CONSTRAINT votes_option_id_fkey FOREIGN KEY (option_id) REFERENCES poll_options(id) ON DELETE CASCADE;

ALTER TABLE ONLY votes
    ADD CONSTRAINT votes_poll_id_fkey FOREIGN KEY (poll_id) REFERENCES polls(id) ON DELETE CASCADE;

ALTER TABLE ONLY votes
    ADD CONSTRAINT votes_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(telegram_id) ON DELETE CASCADE;