USE sharktank;
GO

CREATE OR ALTER VIEW dbo.vw_investor_summary
AS
WITH investor_agg AS (
    SELECT
        di.investor,
        COUNT(DISTINCT di.deal_id) AS deals_count,
        SUM(d.invested_amount) AS total_invested,
        AVG(d.invested_amount) AS avg_ticket
    FROM dbo.deal_investors di
    LEFT JOIN dbo.deals d ON di.deal_id = d.id
    GROUP BY di.investor
),
median_table AS (
    -- compute median invested_equity per investor using window function,
    -- then reduce to one row per investor
    SELECT DISTINCT
        investor,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY invested_equity) 
            OVER (PARTITION BY investor) AS median_invested_equity
    FROM dbo.deal_investors
    WHERE invested_equity IS NOT NULL
),
top_sector AS (
    -- compute count per investor-sector, then pick the top sector per investor
    SELECT investor, sector AS top_sector
    FROM (
        SELECT
            grouped.investor,
            grouped.sector,
            grouped.cnt,
            ROW_NUMBER() OVER (PARTITION BY grouped.investor ORDER BY grouped.cnt DESC) AS rn
        FROM (
            SELECT di.investor, d.sector, COUNT(*) AS cnt
            FROM dbo.deal_investors di
            JOIN dbo.deals d ON di.deal_id = d.id
            GROUP BY di.investor, d.sector
        ) grouped
    ) numbered
    WHERE rn = 1
)
SELECT
    ia.investor,
    ia.deals_count,
    ia.total_invested,
    ia.avg_ticket,
    mt.median_invested_equity,
    ts.top_sector
FROM investor_agg ia
LEFT JOIN median_table mt ON mt.investor = ia.investor
LEFT JOIN top_sector ts ON ts.investor = ia.investor;
GO
