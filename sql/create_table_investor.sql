CREATE TABLE dbo.deal_investors (
    id INT IDENTITY(1,1) PRIMARY KEY,
    deal_id INT NULL, -- will set after join
    staging_id INT,
    investor NVARCHAR(200),
    invested_amount DECIMAL(18,2),
    invested_equity DECIMAL(5,2),
    invested_debt DECIMAL(18,2)
);
GO
