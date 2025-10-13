-- sql/sector_season_counts.sql
-- Purpose: Sector x Season counts for Trends & Insights.
-- Input: none (optionally filter in the app)
-- Output: sector, season, deals_count

CREATE OR ALTER PROCEDURE dbo.sp_sector_season_counts
AS
BEGIN
  SET NOCOUNT ON;

  SELECT COALESCE(sector,'Unknown') AS sector, season, COUNT(*) AS deals_count
  FROM dbo.deals
  GROUP BY COALESCE(sector,'Unknown'), season
  ORDER BY sector, season;
END;
GO
