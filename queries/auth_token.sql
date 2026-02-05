CREATE TABLE IF NOT EXISTS public.auth_tokens
(
    id uuid NOT NULL DEFAULT uuid_generate_v4(),
    client_id character varying(255) COLLATE pg_catalog."default",
    jwt_token character varying(2048) COLLATE pg_catalog."default",
    expires_at timestamp with time zone,
    created_at timestamp with time zone,
    updated_at timestamp with time zone
)

TABLESPACE pg_default;

ALTER TABLE public.auth_tokens
    OWNER to postgres;

-- Trigger: update_auth_tokens_updated_at
CREATE OR REPLACE TRIGGER update_auth_tokens_updated_at
    BEFORE UPDATE 
    ON public.auth_tokens
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();