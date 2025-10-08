-- sql/recent_deals.sql
-- Purpose: Return most recent N deals (by id or date) for the Home Dashboard.
-- Input: @season NVARCHAR(50) = 'All', @top INT = 8
-- Output: top N recent deals

CREATE OR ALTER PROCEDURE dbo.sp_recent_deals
  @season NVARCHAR(50) = 'All',
  @top INT = 8
AS
BEGIN
  SET NOCOUNT ON;

  SELECT TOP (@top)
    id, company, season, episode_number, asked_amount, invested_amount, equity_final
  FROM dbo.deals
  WHERE (@season = 'All' OR season = @season)
  ORDER BY id DESC; -- assumes id increases with recency; change to original_air_date if preferred
END;
GO
