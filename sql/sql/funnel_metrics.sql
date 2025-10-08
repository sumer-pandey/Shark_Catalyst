-- sql/funnel_metrics.sql
-- Purpose: Compute funnel counts: pitched -> offers -> funded.
-- Note: This uses proxies: 'received_offer' not empty implies offer made; invested_amount not null implies funded.
-- Input: @season NVARCHAR(50) = 'All'
-- Output: pitched, offers, funded

CREATE OR ALTER PROCEDURE dbo.sp_funnel_metrics
  @season NVARCHAR(50) = 'All'
AS
BEGIN
  SET NOCOUNT ON;

  SELECT
    COUNT(*) AS pitched,
    SUM(CASE WHEN ISNULL(received_offer,'') <> '' THEN 1 ELSE 0 END) AS offers,
    SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded
  FROM dbo.deals
  WHERE (@season = 'All' OR season = @season);
END;
GO
