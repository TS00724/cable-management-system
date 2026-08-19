-- Development role bootstrap. Production passwords belong in a secret manager.
CREATE ROLE sim_app LOGIN PASSWORD 'sim_app';
CREATE ROLE sim_platform LOGIN PASSWORD 'sim_platform' BYPASSRLS;
GRANT CONNECT ON DATABASE sim TO sim_app, sim_platform;
GRANT USAGE ON SCHEMA public TO sim_app;
GRANT USAGE, CREATE ON SCHEMA public TO sim_platform;
ALTER DEFAULT PRIVILEGES FOR ROLE sim_platform IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO sim_app;
ALTER DEFAULT PRIVILEGES FOR ROLE sim_platform IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO sim_app;
