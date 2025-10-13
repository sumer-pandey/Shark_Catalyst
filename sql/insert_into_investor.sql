INSERT INTO dbo.deal_investors (staging_id, investor, invested_amount, invested_equity, invested_debt)
SELECT
  TRY_CAST(staging_id AS INT) AS staging_id,
  TRY_CAST(investor AS NVARCHAR(200)) AS investor,
  TRY_CONVERT(DECIMAL(18,2), invested_amount) AS invested_amount,
  TRY_CONVERT(DECIMAL(5,2), invested_equity) AS invested_equity,
  TRY_CONVERT(DECIMAL(18,2), invested_debt) AS invested_debt
FROM dbo.staging_deal_investors_clean;
