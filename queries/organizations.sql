CREATE TABLE IF NOT EXISTS public.organizations
(
    id uuid NOT NULL DEFAULT uuid_generate_v4(),
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    deleted_at timestamp with time zone,
    name character varying(100) COLLATE pg_catalog."default",
    address character varying(100) COLLATE pg_catalog."default",
    cnpj character varying(18) COLLATE pg_catalog."default",
    ein character varying(18) COLLATE pg_catalog."default",
    CONSTRAINT organizations_pkey PRIMARY KEY (id),
    CONSTRAINT uni_organizations_cnpj UNIQUE (cnpj),
    CONSTRAINT uni_organizations_ein UNIQUE (ein)
)

TABLESPACE pg_default;

ALTER TABLE public.organizations
    OWNER to postgres;

-- Index: public.idx_organizations_deleted_at
CREATE INDEX IF NOT EXISTS idx_organizations_deleted_at
    ON public.organizations USING btree
    (deleted_at ASC NULLS LAST)
    TABLESPACE pg_default;x