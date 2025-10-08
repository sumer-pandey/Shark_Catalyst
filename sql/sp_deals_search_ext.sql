-- CREATE OR ALTER procedure: sp_deals_search_ext
-- Purpose: advanced server-side search for Deal Explorer with paging, filtering and safe sort mapping.
USE sharktank;
GO

CREATE OR ALTER PROCEDURE dbo.sp_deals_search_ext
  @season NVARCHAR(50) = 'All',
  @sector_csv NVARCHAR(MAX) = NULL,
  @investor_csv NVARCHAR(MAX) = NULL,
  @min_invested DECIMAL(18,2) = NULL,
  @max_invested DECIMAL(18,2) = NULL,
  @funded_flag INT = -1, -- -1 any, 1 funded, 0 not funded
  @city_type NVARCHAR(20) = 'All', -- 'All' / 'Metro' / 'Non-metro'
  @min_founder_count INT = NULL,
  @female_flag INT = -1, -- -1 any, 1 has female_presenter, 0 none
  @sort_by NVARCHAR(50) = 'invested_amount', -- allowed: invested_amount, asked_amount, deal_date, equity_final
  @sort_dir NVARCHAR(4) = 'DESC', -- ASC|DESC
  @limit INT = 50,
  @offset INT = 0
AS
BEGIN
  SET NOCOUNT ON;

  -- sanitize sort_dir
  SET @sort_dir = UPPER(ISNULL(@sort_dir,'DESC'));
  IF @sort_dir NOT IN ('ASC','DESC') SET @sort_dir = 'DESC';

  DECLARE @sql NVARCHAR(MAX) = N'
    SELECT
      d.id, d.company, d.sector, d.season, d.episode_number, d.pitchers_city,
      d.asked_amount, d.invested_amount, d.equity_asked, d.equity_final,
      d.founder_count, d.female_presenters, d.original_air_date
    FROM dbo.deals d
    LEFT JOIN dbo.dim_city dc ON LOWER(LTRIM(RTRIM(d.pitchers_city))) = dc.city_norm
    WHERE 1=1
  ';

  IF (@season IS NOT NULL AND @season <> 'All')
    SET @sql += N' AND d.season = @season';

  IF (@sector_csv IS NOT NULL)
    SET @sql += N' AND EXISTS (SELECT 1 FROM STRING_SPLIT(@sector_csv, @delim) s WHERE LTRIM(RTRIM(s.value)) = d.sector)';

  IF (@investor_csv IS NOT NULL)
    SET @sql += N' AND EXISTS (
      SELECT 1 FROM dbo.deal_investors di_check
      WHERE di_check.deal_id = d.id
        AND EXISTS (SELECT 1 FROM STRING_SPLIT(@investor_csv, @delim) s2 WHERE LTRIM(RTRIM(s2.value)) = di_check.investor)
    )';

  IF (@min_invested IS NOT NULL)
    SET @sql += N' AND d.invested_amount >= @min_invested';

  IF (@max_invested IS NOT NULL)
    SET @sql += N' AND d.invested_amount <= @max_invested';

  IF (@funded_flag = 1)
    SET @sql += N' AND d.invested_amount IS NOT NULL';
  ELSE IF (@funded_flag = 0)
    SET @sql += N' AND d.invested_amount IS NULL';

  IF (@city_type = 'Metro')
    SET @sql += N' AND dc.is_metro = 1';
  ELSE IF (@city_type = 'Non-metro')
    SET @sql += N' AND ISNULL(dc.is_metro, 0) = 0';

  IF (@min_founder_count IS NOT NULL)
    SET @sql += N' AND ISNULL(d.founder_count,0) >= @min_founder_count';

  IF (@female_flag = 1)
    SET @sql += N' AND ISNULL(d.female_presenters,0) > 0';
  ELSE IF (@female_flag = 0)
    SET @sql += N' AND ISNULL(d.female_presenters,0) = 0';

  -- map sort_by to safe column expressions
  DECLARE @order_by NVARCHAR(200) = N'ISNULL(d.invested_amount,0)';  -- default
  IF (@sort_by = 'asked_amount')   SET @order_by = N'ISNULL(d.asked_amount,0)';
  ELSE IF (@sort_by = 'deal_date') SET @order_by = N'd.original_air_date';
  ELSE IF (@sort_by = 'equity_final') SET @order_by = N'ISNULL(d.equity_final,0)';
  ELSE SET @order_by = N'ISNULL(d.invested_amount,0)';

  -- append ORDER BY and pagination (OFFSET / FETCH)
  SET @sql += N' ORDER BY ' + @order_by + N' ' + @sort_dir + N' OFFSET @offset ROWS FETCH NEXT @limit ROWS ONLY;';

  -- Execute with parameter binding (include a delimiter param for STRING_SPLIT)
  EXEC sp_executesql
    @sql,
    N'@season nvarchar(50), @sector_csv nvarchar(max), @investor_csv nvarchar(max),
      @min_invested decimal(18,2), @max_invested decimal(18,2),
      @min_founder_count int, @female_flag int, @funded_flag int,
      @offset int, @limit int, @delim nvarchar(1)',
    @season = @season,
    @sector_csv = @sector_csv,
    @investor_csv = @investor_csv,
    @min_invested = @min_invested,
    @max_invested = @max_invested,
    @min_founder_count = @min_founder_count,
    @female_flag = @female_flag,
    @funded_flag = @funded_flag,
    @offset = @offset,
    @limit = @limit,
    @delim = N',';

END;
GO
