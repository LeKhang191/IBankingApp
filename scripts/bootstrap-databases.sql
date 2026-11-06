-- Idempotent bootstrap for the three data-owning microservices.
-- Values are passed safely by psql variables from bootstrap-databases.sh.

SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'auth_db_user', :'auth_db_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'auth_db_user')
\gexec
SELECT format('ALTER ROLE %I WITH LOGIN PASSWORD %L', :'auth_db_user', :'auth_db_password')
\gexec
SELECT format('CREATE DATABASE %I OWNER %I', :'auth_db_name', :'auth_db_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'auth_db_name')
\gexec
SELECT format('ALTER DATABASE %I OWNER TO %I', :'auth_db_name', :'auth_db_user')
\gexec
SELECT format('REVOKE CONNECT ON DATABASE %I FROM PUBLIC', :'auth_db_name')
\gexec
SELECT format('GRANT CONNECT, TEMP ON DATABASE %I TO %I', :'auth_db_name', :'auth_db_user')
\gexec

SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'tuition_db_user', :'tuition_db_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'tuition_db_user')
\gexec
SELECT format('ALTER ROLE %I WITH LOGIN PASSWORD %L', :'tuition_db_user', :'tuition_db_password')
\gexec
SELECT format('CREATE DATABASE %I OWNER %I', :'tuition_db_name', :'tuition_db_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'tuition_db_name')
\gexec
SELECT format('ALTER DATABASE %I OWNER TO %I', :'tuition_db_name', :'tuition_db_user')
\gexec
SELECT format('REVOKE CONNECT ON DATABASE %I FROM PUBLIC', :'tuition_db_name')
\gexec
SELECT format('GRANT CONNECT, TEMP ON DATABASE %I TO %I', :'tuition_db_name', :'tuition_db_user')
\gexec

SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'payment_db_user', :'payment_db_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'payment_db_user')
\gexec
SELECT format('ALTER ROLE %I WITH LOGIN PASSWORD %L', :'payment_db_user', :'payment_db_password')
\gexec
SELECT format('CREATE DATABASE %I OWNER %I', :'payment_db_name', :'payment_db_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'payment_db_name')
\gexec
SELECT format('ALTER DATABASE %I OWNER TO %I', :'payment_db_name', :'payment_db_user')
\gexec
SELECT format('REVOKE CONNECT ON DATABASE %I FROM PUBLIC', :'payment_db_name')
\gexec
SELECT format('GRANT CONNECT, TEMP ON DATABASE %I TO %I', :'payment_db_name', :'payment_db_user')
\gexec
