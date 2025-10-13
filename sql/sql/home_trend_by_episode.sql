-- sql/home_trend_by_episode.sql
-- Purpose: Episode-level totals and a rolling 3-episode moving average of invested amount.
-- Input: @season NVARCHAR(50) = 'All'
-- Output: season, episode_number, deals_count, total_invested, rolling_3_episode_avg

CREATE OR ALTER PROCEDURE dbo.sp_home_trend_by_episode
  @season NVARCHAR(50) = 'All'
AS
BEGIN
  SET NOCOUNT ON;

  ;WITH episode_agg AS (
    SELECT
      season,
      episode_number,
      COUNT(*) AS deals_count,
      SUM(ISNULL(invested_amount,0)) AS total_invested
    FROM dbo.deals
    WHERE (@season = 'All' OR season = @season)
    GROUP BY season, episode_number
  )
  SELECT
    season,
    episode_number,
    deals_count,
    total_invested,
    AVG(total_invested) OVER (
      PARTITION BY season
      ORDER BY episode_number
      ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS rolling_3_episode_avg
  FROM episode_agg
  ORDER BY season, episode_number;
END;
GO
