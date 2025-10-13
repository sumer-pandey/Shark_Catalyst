-- Myth 1: Count deals & total invested by sector
SELECT TOP 20 COALESCE(sector,'Unknown') AS sector,
       COUNT(*) AS deals_count,
       SUM(invested_amount) AS total_invested,
       AVG(invested_amount) AS avg_invested
FROM dbo.deals
GROUP BY COALESCE(sector,'Unknown')
ORDER BY deals_count DESC;
