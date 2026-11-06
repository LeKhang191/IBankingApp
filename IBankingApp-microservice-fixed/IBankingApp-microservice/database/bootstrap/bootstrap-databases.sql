-- =====================================================
-- iBanking Phase 2
-- Database Bootstrap
-- =====================================================

-- 1. Create AUTH database role
SELECT format(
    'CREATE ROLE %I LOGIN PASSWORD %L',
    :'auth_db_user',
    :'auth_db_password'
)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_roles
    WHERE rolname = :'auth_db_user'
)
\gexec

SELECT format(
    'ALTER ROLE %I WITH LOGIN PASSWORD %L',
    :'auth_db_user',
    :'auth_db_password'
)
\gexec


-- 2. Create TUITION database role
SELECT format(
    'CREATE ROLE %I LOGIN PASSWORD %L',
    :'tuition_db_user',
    :'tuition_db_password'
)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_roles
    WHERE rolname = :'tuition_db_user'
)
\gexec

SELECT format(
    'ALTER ROLE %I WITH LOGIN PASSWORD %L',
    :'tuition_db_user',
    :'tuition_db_password'
)
\gexec


-- 3. Create PAYMENT database role
SELECT format(
    'CREATE ROLE %I LOGIN PASSWORD %L',
    :'payment_db_user',
    :'payment_db_password'
)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_roles
    WHERE rolname = :'payment_db_user'
)
\gexec

SELECT format(
    'ALTER ROLE %I WITH LOGIN PASSWORD %L',
    :'payment_db_user',
    :'payment_db_password'
)
\gexec


-- 4. Create AUTH database
SELECT format(
    'CREATE DATABASE %I OWNER %I',
    :'auth_db_name',
    :'auth_db_user'
)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_database
    WHERE datname = :'auth_db_name'
)
\gexec

SELECT format(
    'ALTER DATABASE %I OWNER TO %I',
    :'auth_db_name',
    :'auth_db_user'
)
\gexec


-- 5. Create TUITION database
SELECT format(
    'CREATE DATABASE %I OWNER %I',
    :'tuition_db_name',
    :'tuition_db_user'
)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_database
    WHERE datname = :'tuition_db_name'
)
\gexec

SELECT format(
    'ALTER DATABASE %I OWNER TO %I',
    :'tuition_db_name',
    :'tuition_db_user'
)
\gexec


-- 6. Create PAYMENT database
SELECT format(
    'CREATE DATABASE %I OWNER %I',
    :'payment_db_name',
    :'payment_db_user'
)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_database
    WHERE datname = :'payment_db_name'
)
\gexec

SELECT format(
    'ALTER DATABASE %I OWNER TO %I',
    :'payment_db_name',
    :'payment_db_user'
)
\gexec