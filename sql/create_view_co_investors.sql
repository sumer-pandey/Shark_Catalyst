CREATE OR ALTER VIEW dbo.vw_co_invest_pairs
AS
WITH inv AS (
  SELECT deal_id, investor
  FROM dbo.deal_investors
  WHERE investor IS NOT NULL AND LTRIM(RTRIM(investor)) <> ''
)
SELECT
  a.investor AS investor_a,
  b.investor AS investor_b,
  COUNT(*) AS together_count
FROM inv a
JOIN inv b
  ON a.deal_id = b.deal_id
  AND a.investor < b.investor  -- canonical ordering to avoid duplicates
GROUP BY a.investor, b.investor;
GO
