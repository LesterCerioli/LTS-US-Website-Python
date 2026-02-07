CREATE TABLE IF NOT EXISTS accounting.exchange_rates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    year_month VARCHAR(7) NOT NULL,  -- Formato: YYYY-MM
    base_currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    target_currency VARCHAR(3) NOT NULL DEFAULT 'BRL',
    rate DECIMAL(10,4) NOT NULL,
    source VARCHAR(50),
    valid_from DATE NOT NULL,
    valid_to DATE NOT NULL,
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Unique constraint
    UNIQUE(year_month, base_currency, target_currency, organization_id),
    -- Check constraints
    CONSTRAINT chk_exchange_rates_year_month_format 
        CHECK (year_month ~ '^\d{4}-\d{2}$'),
    CONSTRAINT chk_exchange_rates_valid_date_range 
        CHECK (valid_from <= valid_to),
    CONSTRAINT chk_exchange_rates_rate_positive 
        CHECK (rate > 0),
    CONSTRAINT chk_exchange_rates_different_currencies 
        CHECK (base_currency != target_currency)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_exchange_rates_organization_id 
    ON accounting.exchange_rates(organization_id);
CREATE INDEX IF NOT EXISTS idx_exchange_rates_year_month 
    ON accounting.exchange_rates(year_month);
CREATE INDEX IF NOT EXISTS idx_exchange_rates_valid_from 
    ON accounting.exchange_rates(valid_from);
CREATE INDEX IF NOT EXISTS idx_exchange_rates_valid_to 
    ON accounting.exchange_rates(valid_to);
CREATE INDEX IF NOT EXISTS idx_exchange_rates_base_currency 
    ON accounting.exchange_rates(base_currency);
CREATE INDEX IF NOT EXISTS idx_exchange_rates_target_currency 
    ON accounting.exchange_rates(target_currency);

-- O índice para costs table deve permanecer em accounting
-- (baseado no script anterior onde você criou a tabela costs no schema accounting)
CREATE INDEX IF NOT EXISTS idx_costs_organization_id ON accounting.costs(organization_id);