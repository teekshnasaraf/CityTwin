-- =============================================================================
-- CITYTWIN - Core Database Schema
-- Target: PostgreSQL 18 with PostGIS 3.6+
-- =============================================================================

-- Enable PostGIS spatial extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- -----------------------------------------------------------------------------
-- 1. BASE CITY MODEL TABLES
-- -----------------------------------------------------------------------------

-- Table: cities
-- Stores metadata and geographic boundaries for supported urban areas.
CREATE TABLE IF NOT EXISTS cities (
    city_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    boundary GEOMETRY(MultiPolygon, 4326),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Table: intersections
-- Stores road intersections / graph nodes extracted from street network data.
CREATE TABLE IF NOT EXISTS intersections (
    intersection_id BIGSERIAL PRIMARY KEY,
    city_id INTEGER NOT NULL REFERENCES cities(city_id) ON DELETE CASCADE,
    osm_id BIGINT,
    geometry GEOMETRY(Point, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Table: roads
-- Stores street network segments / graph edges with physical and operational attributes.
CREATE TABLE IF NOT EXISTS roads (
    road_id BIGSERIAL PRIMARY KEY,
    city_id INTEGER NOT NULL REFERENCES cities(city_id) ON DELETE CASCADE,
    osm_id BIGINT,
    name VARCHAR(255),
    road_type VARCHAR(50),
    length_m DOUBLE PRECISION,
    speed_limit DOUBLE PRECISION,
    lanes INTEGER,
    capacity DOUBLE PRECISION,
    geometry GEOMETRY(Geometry, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Table: places
-- Stores points of interest (POIs), critical infrastructure, and facilities.
CREATE TABLE IF NOT EXISTS places (
    place_id BIGSERIAL PRIMARY KEY,
    city_id INTEGER NOT NULL REFERENCES cities(city_id) ON DELETE CASCADE,
    osm_id BIGINT,
    name VARCHAR(255),
    place_type VARCHAR(100) NOT NULL,
    geometry GEOMETRY(Geometry, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 2. DYNAMIC CITY STATE TABLES
-- -----------------------------------------------------------------------------

-- Table: traffic_state
-- Stores time-series traffic observations and dynamic edge state.
CREATE TABLE IF NOT EXISTS traffic_state (
    traffic_id BIGSERIAL PRIMARY KEY,
    road_id BIGINT NOT NULL REFERENCES roads(road_id) ON DELETE CASCADE,
    vehicle_count INTEGER,
    average_speed DOUBLE PRECISION,
    congestion_level DOUBLE PRECISION,
    source VARCHAR(100),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Table: weather_state
-- Stores time-series meteorological observations across city areas.
CREATE TABLE IF NOT EXISTS weather_state (
    weather_id BIGSERIAL PRIMARY KEY,
    city_id INTEGER NOT NULL REFERENCES cities(city_id) ON DELETE CASCADE,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    rainfall DOUBLE PRECISION,
    wind_speed DOUBLE PRECISION,
    source VARCHAR(100),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 3. INGESTION & DATA QUALITY LOGS
-- -----------------------------------------------------------------------------

-- Table: data_sources
-- Catalogs registered external data feeds and update policies.
CREATE TABLE IF NOT EXISTS data_sources (
    source_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    url VARCHAR(500),
    refresh_interval_seconds INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Table: ingestion_logs
-- Tracks external data pipeline runs, throughput, and status.
CREATE TABLE IF NOT EXISTS ingestion_logs (
    log_id BIGSERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES data_sources(source_id) ON DELETE SET NULL,
    city_id INTEGER REFERENCES cities(city_id) ON DELETE SET NULL,
    dataset_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ
);

-- Table: data_quality_logs
-- Records validation rules, anomaly detection, and data integrity checks.
CREATE TABLE IF NOT EXISTS data_quality_logs (
    quality_id BIGSERIAL PRIMARY KEY,
    log_id BIGINT REFERENCES ingestion_logs(log_id) ON DELETE SET NULL,
    dataset_type VARCHAR(50) NOT NULL,
    check_name VARCHAR(100) NOT NULL,
    passed BOOLEAN NOT NULL,
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
