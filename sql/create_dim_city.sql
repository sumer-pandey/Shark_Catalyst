CREATE TABLE dbo.dim_city (
    city NVARCHAR(200) PRIMARY KEY,
    city_norm NVARCHAR(200),
    is_metro BIT
);

-- Populate with a starter metro list (you can extend this later)
-- This INSERT uses a few canonical city names. Add more rows as you refine.
INSERT INTO dbo.dim_city (city, city_norm, is_metro) VALUES
  ('Mumbai', 'mumbai', 1),
  ('Delhi', 'delhi', 1),
  ('Bangalore', 'bangalore', 1),
  ('Bengaluru', 'bangalore', 1),
  ('Hyderabad', 'hyderabad', 1),
  ('Chennai', 'chennai', 1),
  ('Kolkata', 'kolkata', 1),
  ('Pune', 'pune', 1),
  ('Ahmedabad', 'ahmedabad', 0),
  ('Jaipur', 'jaipur', 0),
  ('Lucknow', 'lucknow', 0),
  ('Gurgaon', 'gurgaon', 1),
  ('Noida', 'noida', 1),
  ('Faridabad', 'faridabad', 0),
  ('Surat', 'surat', 0);

-- If you run this multiple times during testing, avoid duplicate inserts:
-- DELETE FROM dbo.dim_city WHERE city IN (...); before re-inserting.
