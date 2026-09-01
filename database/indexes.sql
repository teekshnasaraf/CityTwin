-- =============================================================================
-- CITYTWIN - Core Database Indexes
-- Spatial and performance indexes for PostgreSQL 18 + PostGIS 3.6
-- =============================================================================

-- Spatial GIST indexes
CREATE INDEX IF NOT EXISTS idx_cities_boundary ON cities USING GIST (boundary);
CREATE INDEX IF NOT EXISTS idx_intersections_geometry ON intersections USING GIST (geometry);
CREATE INDEX IF NOT EXISTS idx_roads_geometry ON roads USING GIST (geometry);
CREATE INDEX IF NOT EXISTS idx_places_geometry ON places USING GIST (geometry);

-- Relational foreign key and lookup indexes
CREATE INDEX IF NOT EXISTS idx_roads_city_id ON roads (city_id);
CREATE INDEX IF NOT EXISTS idx_roads_osm_id ON roads (osm_id);
CREATE INDEX IF NOT EXISTS idx_intersections_city_id ON intersections (city_id);
CREATE INDEX IF NOT EXISTS idx_places_city_id ON places (city_id);
CREATE INDEX IF NOT EXISTS idx_places_type ON places (place_type);

-- Time-series and monitoring indexes
CREATE INDEX IF NOT EXISTS idx_traffic_state_road_id ON traffic_state (road_id);
CREATE INDEX IF NOT EXISTS idx_traffic_state_recorded_at ON traffic_state (recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_weather_state_city_id ON weather_state (city_id);
CREATE INDEX IF NOT EXISTS idx_weather_state_recorded_at ON weather_state (recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_ingestion_logs_source ON ingestion_logs (source_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_logs_city ON ingestion_logs (city_id);
CREATE INDEX IF NOT EXISTS idx_data_quality_logs_log ON data_quality_logs (log_id);
