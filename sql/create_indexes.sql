CREATE INDEX IX_deals_season ON dbo.deals(season);
CREATE INDEX IX_deals_sector ON dbo.deals(sector);
CREATE INDEX IX_deals_invested_amount ON dbo.deals(invested_amount);
CREATE INDEX IX_deal_investors_investor ON dbo.deal_investors(investor);
CREATE INDEX IX_deal_investors_deal_id ON dbo.deal_investors(deal_id);
