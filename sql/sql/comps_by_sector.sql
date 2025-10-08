-- sql/comps_by_sector.sql
-- Purpose: Return comparable deals by sector with optional season filter.
-- Inputs: @sector NVARCHAR(255), @target_amount DECIMAL(18,2), @season NVARCHAR(50) = 'All', @limit INT = 5

CREATE OR ALTER PROCEDURE dbo.sp_comps_by_sector
  @sector NVARCHAR(255),
  @target_amount DECIMAL(18,2),
  @season NVARCHAR(50) = 'All',
  @limit INT = 5
AS
BEGIN
  SET NOCOUNT ON;

  SELECT TOP (@limit)
    id, company, season, invested_amount, equity_final, 
    ABS(ISNULL(invested_amount,0) - @target_amount) AS amt_diff
  FROM dbo.deals
  WHERE sector = @sector
    AND (@season = 'All' OR season = @season)
    AND invested_amount IS NOT NULL
  ORDER BY amt_diff ASC;
END;
GO
