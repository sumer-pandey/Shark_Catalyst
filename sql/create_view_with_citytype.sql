CREATE OR ALTER VIEW dbo.vw_deals_with_citytype
AS
SELECT
  d.*,
  -- normalize pitchers_city by trimming & lowercasing for join
  LTRIM(RTRIM(d.pitchers_city)) AS pitchers_city_raw,
  LOWER(LTRIM(RTRIM(d.pitchers_city))) AS pitchers_city_norm,
  dc.city AS matched_city,
  ISNULL(dc.is_metro, 0) AS is_metro,
  CASE WHEN ISNULL(dc.is_metro, 0) = 1 THEN 'Metro' ELSE 'Non-metro' END AS city_type
FROM dbo.deals d
LEFT JOIN dbo.dim_city dc
  ON LOWER(LTRIM(RTRIM(d.pitchers_city))) = dc.city_norm;
GO
