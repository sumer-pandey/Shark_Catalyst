USE [master]
GO

-- Drop the server login if it already exists.
IF EXISTS (SELECT * FROM sys.server_principals WHERE name = 'sharktank_admin')
BEGIN
    DROP LOGIN [sharktank_admin]
END
GO

-- Create a new SQL Server login named 'sharktank_admin' with a strong password.
-- The password must meet your server's password policy.
-- NOTE: Replace 'your_new_password' with your desired password.
CREATE LOGIN [sharktank_admin] WITH PASSWORD=N'admin@1d', DEFAULT_DATABASE=[sharktank], CHECK_EXPIRATION=OFF, CHECK_POLICY=ON
GO

USE [sharktank]
GO

-- Drop the user from the database if it already exists.
IF EXISTS (SELECT * FROM sys.database_principals WHERE name = 'sharktank_admin')
BEGIN
    DROP USER [sharktank_admin]
END
GO

-- Create a user in the 'sharktank' database for the new login.
CREATE USER [sharktank_admin] FOR LOGIN [sharktank_admin]
GO

-- Grant the user permission to execute stored procedures within the 'dbo' schema.
-- This is necessary for the application's functionality.
GRANT EXECUTE ON SCHEMA::dbo TO [sharktank_admin]
GO

-- Add the user to the 'db_datareader' and 'db_datawriter' roles.
-- This gives the user permissions to read from and write to all tables in the database.
ALTER ROLE [db_datareader] ADD MEMBER [sharktank_admin]
GO
ALTER ROLE [db_datawriter] ADD MEMBER [sharktank_admin]
GO
