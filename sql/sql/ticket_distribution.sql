-- sql/ticket_distribution.sql
-- Purpose: Bucket ticket sizes for histograms / boxplot pre-aggregation.
-- Output: bucket_label, deals, total_invested, pct
-- Buckets (INR): <1 Lakh, 1L-10L, 10L-1Cr, 1Cr-5Cr, >5Cr

CREATE OR ALTER PROCEDURE dbo.sp_ticket_distribution
AS
BEGIN
  SET NOCOUNT ON;

  WITH bucketed AS (
    SELECT
      CASE
        WHEN invested_amount IS NULL THEN 'Unknown'
        WHEN invested_amount < 100000 THEN '<1L'
        WHEN invested_amount < 1000000 THEN '1L-10L'
        WHEN invested_amount < 10000000 THEN '10L-1Cr'
        WHEN invested_amount < 50000000 THEN '1Cr-5Cr'
        ELSE '>5Cr'
      END AS bucket_label,
      invested_amount
    FROM dbo.deals
  ), agg AS (
    SELECT bucket_label, COUNT(*) AS deals, SUM(ISNULL(invested_amount,0)) AS total_invested
    FROM bucketed
    GROUP BY bucket_label
  ), total AS (SELECT SUM(deals) AS total_deals FROM agg)
  SELECT
    a.bucket_label, a.deals, a.total_invested,
    1.0 * a.deals / t.total_deals AS pct
  FROM agg a CROSS JOIN total t
  ORDER BY
    CASE a.bucket_label
      WHEN 'Unknown' THEN 0 WHEN '<1L' THEN 1 WHEN '1L-10L' THEN 2 WHEN '10L-1Cr' THEN 3 WHEN '1Cr-5Cr' THEN 4 WHEN '>5Cr' THEN 5 ELSE 99 END;
END;
GO
