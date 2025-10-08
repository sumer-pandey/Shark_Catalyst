-- Row counts
SELECT 'staging_deals' AS name, COUNT(*) AS rows FROM dbo.staging_deals_clean
UNION ALL
SELECT 'deals' AS name, COUNT(*) AS rows FROM dbo.deals
UNION ALL
SELECT 'staging_investors' AS name, COUNT(*) AS rows FROM dbo.staging_deal_investors_clean
UNION ALL
SELECT 'deal_investors' AS name, COUNT(*) AS rows FROM dbo.deal_investors;

-- Top deals by invested amount
SELECT TOP 10 id, company, season, invested_amount, equity_final FROM dbo.deals ORDER BY invested_amount DESC;

-- Top investors by number of deals
SELECT investor, COUNT(*) AS deals_count, SUM(invested_amount) AS total_invested
FROM dbo.deal_investors
GROUP BY investor
ORDER BY deals_count DESC;

-- How many deals have null invested_amount?
SELECT COUNT(*) AS null_invested_count FROM dbo.deals WHERE invested_amount IS NULL;
