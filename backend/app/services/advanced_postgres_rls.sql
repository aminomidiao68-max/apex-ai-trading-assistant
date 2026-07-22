# SQL Script to enable PostgreSQL Row-Level Security (RLS) for APEX AI Enterprise
# This enforces database-level tenant isolation, ensuring users can only read/write their own rows.

-- 1. Enable Row-Level Security on User Provider Secrets
ALTER TABLE user_provider_secrets ENABLE ROW LEVEL SECURITY;

-- Create policy for user_provider_secrets: Allow users to select/insert/update/delete only their own records
CREATE POLICY user_secrets_isolation_policy ON user_provider_secrets
    FOR ALL
    USING (user_id = CURRENT_SETTING('app.current_user_id', true)::INTEGER)
    WITH CHECK (user_id = CURRENT_SETTING('app.current_user_id', true)::INTEGER);


-- 2. Enable Row-Level Security on Paper Orders
ALTER TABLE paper_orders ENABLE ROW LEVEL SECURITY;

-- Create policy for paper_orders
CREATE POLICY user_orders_isolation_policy ON paper_orders
    FOR ALL
    USING (user_id = CURRENT_SETTING('app.current_user_id', true)::INTEGER)
    WITH CHECK (user_id = CURRENT_SETTING('app.current_user_id', true)::INTEGER);


-- 3. Enable Row-Level Security on Signal Shadow Observations
ALTER TABLE signal_shadow_observations ENABLE ROW LEVEL SECURITY;

-- Create policy for signal_shadow_observations (Allowing user_id=0 for system observations and user_id=current_user)
CREATE POLICY user_observations_isolation_policy ON signal_shadow_observations
    FOR ALL
    USING (
        user_id = 0 
        OR user_id = CURRENT_SETTING('app.current_user_id', true)::INTEGER
    )
    WITH CHECK (
        user_id = 0 
        OR user_id = CURRENT_SETTING('app.current_user_id', true)::INTEGER
    );


-- Note on Application Integration:
-- In your FastAPI database connection pool, after acquiring a connection for an authenticated request,
-- you must execute the following session-local command before running any query:
-- "SET LOCAL app.current_user_id = {authenticated_user_id};"
