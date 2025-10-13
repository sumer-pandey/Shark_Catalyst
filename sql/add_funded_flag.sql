USE sharktank;
GO

-- Add a computed (read-only) funded_flag column if it does not exist.
IF NOT EXISTS (
  SELECT 1 FROM sys.columns
  WHERE [object_id] = OBJECT_ID('dbo.deals') AND [name] = 'funded_flag'
)
BEGIN
  ALTER TABLE dbo.deals
  ADD funded_flag AS (CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END) PERSISTED;
  PRINT 'funded_flag computed column added to dbo.deals';
END
ELSE
BEGIN
  PRINT 'funded_flag column already exists in dbo.deals — skipping add.';
END
GO
