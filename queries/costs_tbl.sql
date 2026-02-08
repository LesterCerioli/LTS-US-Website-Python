CREATE TABLE IF NOT EXISTS accounting.costs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    due_date DATE NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    payment_nature VARCHAR(100) NOT NULL,
    cost_nature_code VARCHAR(50) NOT NULL,
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    converted_amount_brl DECIMAL(15,2),
    exchange_rate_month VARCHAR(7),
    exchange_rate_value DECIMAL(10,4),
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL
);

CREATE INDEX IF NOT EXISTS idx_costs_organization_id ON accounting.costs(organization_id);
CREATE INDEX IF NOT EXISTS idx_costs_due_date ON accounting.costs(due_date);
CREATE INDEX IF NOT EXISTS idx_costs_status ON accounting.costs(status);
CREATE INDEX IF NOT EXISTS idx_costs_cost_nature ON accounting.costs(cost_nature_code);
CREATE INDEX IF NOT EXISTS idx_costs_exchange_rate_month ON accounting.costs(exchange_rate_month);