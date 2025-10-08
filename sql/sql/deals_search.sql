-- sql/deals_search.sql
-- Purpose: Parameterized search for the Deal Explorer. Supports CSV lists for sectors/investors via STRING_SPLIT.
-- Inputs:
--  @season NVARCHAR(50) = 'All'
--  @sector_csv NVARCHAR(MAX) = NULL  -- comma-separated sectors, exact match expected
--  @investor_csv NVARCHAR(MAX) = NULL -- comma-separated investor names, exact match expected
--  @min_invested DECIMAL(18,2) = NULL
--  @max_invested DECIMAL(18,2) = NULL
--  @funded_flag INT = -1 -- -1 any, 1 funded (invested_amount NOT NULL), 0 not funded
--  @limit INT = 500, @offset INT = 0
-- Output: paginated result set for the explorer.

CREATE OR ALTER PROCEDURE dbo.sp_deals_search
  @season NVARCHAR(50) = 'All',
  @sector_csv NVARCHAR(MAX) = NULL,
  @investor_csv NVARCHAR(MAX) = NULL,
  @min_invested DECIMAL(18,2) = NULL,
  @max_invested DECIMAL(18,2) = NULL,
  @funded_flag INT = -1,
  @limit INT = 500,
  @offset INT = 0
AS
BEGIN
  SET NOCOUNT ON;

  SELECT
    d.id, d.company, d.season, d.sector, d.episode_number, d.asked_amount, d.invested_amount, d.equity_asked, d.equity_final,
    d.pitchers_city,
    -- aggregated investor list (comma-separated)
    STUFF((
      SELECT ',' + di2.investor
      FROM dbo.deal_investors di2
      WHERE di2.deal_id = d.id
      FOR XML PATH(''), TYPE
    ).value('.', 'NVARCHAR(MAX)'),1,1,'') AS investors
  FROM dbo.deals d
  WHERE (@season = 'All' OR d.season = @season)
    AND (@min_invested IS NULL OR d.invested_amount >= @min_invested)
    AND (@max_invested IS NULL OR d.invested_amount <= @max_invested)
    AND (
      @funded_flag = -1
      OR (@funded_flag = 1 AND d.invested_amount IS NOT NULL)
      OR (@funded_flag = 0 AND d.invested_amount IS NULL)
    )
    AND (
      @sector_csv IS NULL
      OR EXISTS (
        SELECT 1 FROM STRING_SPLIT(@sector_csv,',') s
        WHERE LTRIM(RTRIM(s.value)) = d.sector
      )
    )
    AND (
      @investor_csv IS NULL
      OR EXISTS (
        SELECT 1 FROM dbo.deal_investors di
        WHERE di.deal_id = d.id
          AND EXISTS (SELECT 1 FROM STRING_SPLIT(@investor_csv,',') s2 WHERE LTRIM(RTRIM(s2.value)) = di.investor)
      )
    )
  ORDER BY d.invested_amount DESC
  OFFSET @offset ROWS FETCH NEXT @limit ROWS ONLY;
END;
GO
