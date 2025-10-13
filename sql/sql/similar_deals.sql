-- sql/similar_deals.sql
-- Purpose: Return the N most similar deals by invested amount within the same sector.
-- Inputs: @sector NVARCHAR(255), @target_amount DECIMAL(18,2), @limit INT = 5
-- Output: top N similar deals sorted by absolute difference in invested amount.

CREATE OR ALTER PROCEDURE dbo.sp_similar_deals
  @sector NVARCHAR(255),
  @target_amount DECIMAL(18,2),
  @limit INT = 5
AS
BEGIN
  SET NOCOUNT ON;

  SELECT TOP (@limit)
    id, company, season, invested_amount, equity_final,
    ABS(ISNULL(invested_amount,0) - @target_amount) AS amt_diff
  FROM dbo.deals
  WHERE sector = @sector AND invested_amount IS NOT NULL
  ORDER BY amt_diff ASC;
END;
GO
