-- listings table (one row per property)
-- Adjust engine/charset if using MySQL (e.g., ENGINE=InnoDB DEFAULT CHARSET=utf8mb4)

CREATE TABLE listings (
  listing_id BIGINT PRIMARY KEY,                     -- id
  name TEXT,
  host_id BIGINT,
  host_identity_verified TEXT,                       -- 'verified'/'unknown' etc.
  host_name TEXT,
  neighbourhood_group TEXT,                          -- e.g., Manhattan
  neighbourhood TEXT,                                -- e.g., Harlem
  lat DOUBLE,
  long DOUBLE,
  room_type TEXT,                                    -- Entire home/Private/Shared/Hotel
  construction_year INT,

  price DECIMAL(12,2),
  service_fee DECIMAL(12,2),

  minimum_nights INT,
  number_of_reviews INT,
  last_review DATE,
  reviews_per_month DECIMAL(6,2),
  review_rate_number DECIMAL(6,2),
  calculated_host_listings_count INT,
  availability_365 INT,

  country TEXT,
  country_code TEXT,
  instant_bookable TEXT,                             -- 't'/'f' or 'yes'/'no'
  cancellation_policy TEXT,
  house_rules TEXT,
  license TEXT
);

-- Helpful indexes for your common queries
CREATE INDEX idx_listings_neigh_group ON listings (neighbourhood_group);
CREATE INDEX idx_listings_room_type   ON listings (room_type);
CREATE INDEX idx_listings_host        ON listings (host_id);
CREATE INDEX idx_listings_price       ON listings (price);
CREATE INDEX idx_listings_avail       ON listings (availability_365);
CREATE INDEX idx_listings_lastrev     ON listings (last_review);

-- (Optional) Narrow, de-duplicated host dimension if you later want star-schema
-- CREATE TABLE hosts AS
-- SELECT DISTINCT host_id, host_name, host_identity_verified
-- FROM listings WHERE host_id IS NOT NULL;
-- ALTER TABLE hosts ADD PRIMARY KEY (host_id);
