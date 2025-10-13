UPDATE di
SET di.deal_id = d.id
FROM dbo.deal_investors di
JOIN dbo.deals d ON di.staging_id = d.staging_id;
