-- sql/home_kpis.sql
-- Purpose: Return high-level KPIs for the Home Dashboard.
-- Input: @season NVARCHAR(50) (use 'All' for no filtering)
-- Output: Single row with KPI columns.

CREATE OR ALTER PROCEDURE dbo.sp_home_kpis
  @season NVARCHAR(50) = 'All'
AS
BEGIN
  SET NOCOUNT ON;

  SELECT
    COUNT(*) AS total_pitches,
    SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded_deals,
    SUM(ISNULL(invested_amount,0)) AS total_capital_invested,
    AVG(NULLIF(invested_amount,0)) AS avg_deal_size,
    AVG(equity_final) AS avg_equity_accepted,
    AVG(NULLIF(number_of_sharks_in_deal,0)) AS avg_sharks_per_deal,
    1.0 * SUM(CASE WHEN invested_amount < 10000000 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0) AS pct_deals_under_1cr
  FROM dbo.deals d
  WHERE (@season = 'All' OR d.season = @season);
END;
GO
