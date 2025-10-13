-- sql/investor_equity_stats.sql
-- Purpose: Return quartile equity stats (Q1, median, Q3) for an investor's invested_equity values.
-- Input: @investor NVARCHAR(200)
-- Output: investor, q1, median, q3

CREATE OR ALTER PROCEDURE dbo.sp_investor_equity_stats
  @investor NVARCHAR(200)
AS
BEGIN
  SET NOCOUNT ON;

  SELECT DISTINCT
    investor,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY invested_equity) OVER (PARTITION BY investor) AS q1,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY invested_equity) OVER (PARTITION BY investor) AS median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY invested_equity) OVER (PARTITION BY investor) AS q3
  FROM dbo.deal_investors
  WHERE investor = @investor AND invested_equity IS NOT NULL;
END;
GO
