CREATE TABLE IF NOT EXISTS public.users
(
    id uuid NOT NULL,
    organization_id uuid,
    name text COLLATE pg_catalog."default",
    email text COLLATE pg_catalog."default",
    password text COLLATE pg_catalog."default",
    role text COLLATE pg_catalog."default",
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    deleted_at timestamp with time zone,
    CONSTRAINT users_pkey PRIMARY KEY (id),
    CONSTRAINT fk_users_organization FOREIGN KEY (organization_id)
        REFERENCES public.organizations (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT fk_users_organizations FOREIGN KEY (organization_id)
        REFERENCES public.organizations (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE RESTRICT
)

TABLESPACE pg_default;

ALTER TABLE public.users
    OWNER to postgres;

-- Index: public.idx_users_created_at
CREATE INDEX IF NOT EXISTS idx_users_created_at
    ON public.users USING btree
    (created_at ASC NULLS LAST)
    TABLESPACE pg_default
    WHERE deleted_at IS NULL;
-- Index: public.idx_users_deleted_at
CREATE INDEX IF NOT EXISTS idx_users_deleted_at
    ON public.users USING btree
    (deleted_at ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: public.idx_users_email
CREATE INDEX IF NOT EXISTS idx_users_email
    ON public.users USING btree
    (email COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default
    WHERE deleted_at IS NULL;
-- Index: public.idx_users_email_org
CREATE INDEX IF NOT EXISTS idx_users_email_org
    ON public.users USING btree
    (email COLLATE pg_catalog."default" ASC NULLS LAST, organization_id ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: public.idx_users_email_password_check
CREATE INDEX IF NOT EXISTS idx_users_email_password_check
    ON public.users USING btree
    (email COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default
    WHERE deleted_at IS NULL;
-- Index: public.idx_users_email_unique
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique
    ON public.users USING btree
    (email COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default
    WHERE deleted_at IS NULL;
-- Index: public.idx_users_org_id
CREATE INDEX IF NOT EXISTS idx_users_org_id
    ON public.users USING btree
    (organization_id ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: public.idx_users_organization_id
CREATE INDEX IF NOT EXISTS idx_users_organization_id
    ON public.users USING btree
    (organization_id ASC NULLS LAST)
    TABLESPACE pg_default
    WHERE deleted_at IS NULL;
-- Index: public.idx_users_role
CREATE INDEX IF NOT EXISTS idx_users_role
    ON public.users USING btree
    (role COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default
    WHERE deleted_at IS NULL;
-- Index: public.idx_users_updated_at
CREATE INDEX IF NOT EXISTS idx_users_updated_at
    ON public.users USING btree
    (updated_at ASC NULLS LAST)
    TABLESPACE pg_default
    WHERE deleted_at IS NULL;
-- Trigger: trigger_update_users_updated_at
CREATE OR REPLACE TRIGGER trigger_update_users_updated_at
    BEFORE UPDATE 
    ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

COMMENT ON TRIGGER trigger_update_users_updated_at ON public.users
    IS Automatically updates updated_at timestamp on user updates;