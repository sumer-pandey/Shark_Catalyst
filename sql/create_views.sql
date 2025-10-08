CREATE VIEW vw_deals_summary AS
SELECT id, staging_id, company, season, episode_number, pitch_number, sector,
       asked_amount, invested_amount, equity_asked, equity_final, deal_valuation,
       number_of_sharks_in_deal, namita_present, vineeta_present, anupam_present,
       aman_present, peyush_present, ritesh_present, amit_present, guest_present
FROM dbo.deals;
GO

CREATE VIEW vw_investor_deals AS
SELECT di.id AS investor_row_id, di.deal_id, di.investor, di.invested_amount, di.invested_equity, di.invested_debt,
       d.company, d.season, d.sector, d.invested_amount AS total_deal_amount
FROM dbo.deal_investors di
LEFT JOIN dbo.deals d ON di.deal_id = d.id;
GO
