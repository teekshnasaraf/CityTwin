# CITYTWIN --- Project Architecture, Data Strategy & Implementation Plan

> **Experiment on a city before experimenting on the city.**\
> AI-Powered Urban Digital Twin for Scenario-Based Decision Intelligence

## 1. Project Overview

CITYTWIN is an AI-powered urban digital twin designed to let planners
and operators test interventions on a computational representation of a
city before applying them to the real city.

The core loop is:

**Observe → Build Digital Twin → Run Scenario → Simulate Cascading
Effects → Predict Impact → Compare & Recommend**

The project treats the city as an interconnected system rather than
isolated departments. A change such as a road closure can affect
traffic, public transport, emergency response, pollution and potentially
population exposure.

### Core question

Instead of only asking:

> **What is happening in the city?**

CITYTWIN asks:

> **What will happen if we act?**

------------------------------------------------------------------------

# 2. What We Are Building

The first version should focus on one strong end-to-end scenario:

### Road Closure Scenario

A user selects a road and specifies:

-   closure duration
-   traffic multiplier
-   rainfall/weather factor
-   optional event factor

CITYTWIN then:

1.  Changes the selected road's simulated state.
2.  Recalculates traffic routing.
3.  Redistributes traffic through the road network.
4.  Calculates congestion.
5.  Estimates public-transport delay.
6.  Calculates emergency-route/ETA impact.
7.  Estimates pollution impact.
8.  Compares alternative interventions.
9.  Recommends the lowest-impact option.

This becomes the project's MVP and demonstrates the central
cascading-impact idea.

------------------------------------------------------------------------

# 3. Important Design Principle: Real Data, Not Hardcoded City Data

CITYTWIN should **not** contain a manually hardcoded city database.

Instead:

``` text
External City Data
       ↓
Data Ingestion
       ↓
Validation + Normalization
       ↓
PostgreSQL + PostGIS
       ↓
Digital Twin State
       ↓
Simulation / AI / Optimization
       ↓
Dashboard
```

The database is persistent, but its contents are populated and refreshed
from real/open sources.

Not every source is truly real-time. Therefore every dataset gets a
source and freshness policy:

  ------------------------------------------------------------------------
  Data                    Source type             Update strategy
  ----------------------- ----------------------- ------------------------
  Roads/buildings/POIs    OpenStreetMap           Initial load + scheduled
                                                  refresh

  Public transit          GTFS                    Scheduled feed refresh
  schedules                                       

  Transit                 GTFS Realtime where     Frequent polling
  positions/delays        available               

  Weather                 Live/API or Copernicus  Periodic refresh
                          datasets                

  Air quality             OpenAQ / available      Periodic refresh
                          sensors                 

  Traffic                 Municipal/live feed     Frequent polling
                          where available         

  Traffic when no live    Modelled/synthetic      Simulation/calibration
  feed exists                                     

  Events/scenarios        User/system generated   On demand
  ------------------------------------------------------------------------

The original project concept explicitly separates real/open baseline
data from synthetic/modelled dynamic data and future scenarios.

------------------------------------------------------------------------

# 4. High-Level Architecture

``` text
                         REAL CITY / DATA SOURCES
                                  │
             ┌────────────────────┼────────────────────┐
             │                    │                    │
             ▼                    ▼                    ▼
        OpenStreetMap          GTFS/RT           Weather/Air
             │                    │                    │
             └────────────────────┼────────────────────┘
                                  ▼
                         DATA INGESTION LAYER
                                  │
                   ┌──────────────┼──────────────┐
                   ▼              ▼              ▼
              Fetchers       Validators      Normalizers
                   │              │              │
                   └──────────────┼──────────────┘
                                  ▼
                        POSTGRESQL + POSTGIS
                                  │
             ┌────────────────────┼────────────────────┐
             ▼                    ▼                    ▼
        CITY BASE MODEL       LIVE STATE           HISTORY
             │                    │                    │
             └────────────────────┼────────────────────┘
                                  ▼
                         DIGITAL TWIN CORE
                                  │
                 ┌────────────────┼────────────────┐
                 ▼                ▼                ▼
             Simulation          AI/ML         Optimization
                 │                │                │
                 └────────────────┼────────────────┘
                                  ▼
                            FASTAPI BACKEND
                                  │
                                  ▼
                         REACT WEB APPLICATION
                                  │
                 ┌────────────────┼────────────────┐
                 ▼                ▼                ▼
               Map           Scenario Builder    Results
```

### Deployment Architecture

``` text
                                                 DEVELOPMENT

                                 Docker / Local Environment
                                                            ↓
                                        PostgreSQL + PostGIS
                                                            ↓
                                                     FastAPI
                                                            ↓
                                                 React/Next.js


                                                    PRODUCTION

                                        React / Next.js Frontend
                                                            ↓
                                                        Vercel
                                                            ↓
                                             FastAPI Backend
                                                            ↓
                                                        Render
                                                            ↓
                                         PostgreSQL + PostGIS
```

------------------------------------------------------------------------

# 5. Technology Stack

## Frontend

-   React
-   MapLibre / Mapbox
-   Deck.gl
-   Optional CesiumJS for future 3D

Responsibilities:

-   city map
-   layer control
-   scenario builder
-   simulation controls
-   KPI cards
-   before/after visualization
-   recommendation display

## Backend

-   Python
-   FastAPI

Responsibilities:

-   REST API
-   city management
-   data ingestion control
-   scenario management
-   simulation execution
-   result delivery
-   authentication later if required

## Database

### PostgreSQL + PostGIS

PostgreSQL stores structured city and simulation data.

PostGIS stores spatial data:

-   points
-   roads
-   polygons
-   city boundaries
-   routes
-   geographic relationships

## Geospatial / Simulation

-   OSMnx
-   NetworkX
-   GeoPandas
-   NumPy
-   SciPy

## AI/ML

-   scikit-learn
-   XGBoost or LightGBM
-   SHAP where explainability is needed

The initial traffic prediction pipeline is:

``` text
TrafficStateRecord
    ↓
Feature Engineering
    ↓
ML Training Samples
    ↓
Candidate Regression Models
    ↓
Evaluation
    ↓
Best Model Selection
    ↓
Traffic Prediction
```

The traffic-volume regression target is future `vehicle_count` for the same
road at the default 15-minute prediction horizon. Features come from the
centralized feature-engineering layer. Candidate models use the same
chronological train/test split and are evaluated on the same test set using
MAE, RMSE, and R². MAE is the primary model-selection metric; the selected
model is then used for prediction.

Initial candidate models:

-   Linear Regression
-   Random Forest Regressor
-   XGBoost Regressor

The current synthetic MODELLED traffic data is used to validate the ML
pipeline and model-selection implementation. These synthetic metrics must
not be interpreted as real-world traffic accuracy. Meaningful evaluation
requires future real or historical traffic data.

## Deployment

### Local Development

-   Docker
-   PostgreSQL + PostGIS containerized for consistent local development

Docker is used primarily to provide a reproducible development environment
across team members and remains part of the development/tooling architecture.

### Production Deployment

-   Vercel — frontend hosting
-   Render — FastAPI backend hosting
-   PostgreSQL + PostGIS — production database

Docker is not the production hosting platform for the frontend or backend;
Vercel and Render provide those deployment targets while PostgreSQL + PostGIS
remains the database layer.

# Deployment Architecture

CITYTWIN uses separate deployment targets for the frontend and backend.

Frontend:
React/Next.js → Vercel

Backend:
Python/FastAPI → Render

Database:
PostgreSQL + PostGIS

Local development:
Docker → PostgreSQL/PostGIS and supporting services

Separating frontend and backend deployment allows the team to develop and
deploy each layer independently while maintaining the same application
architecture. Vercel and Render are hosting choices; they do not replace
FastAPI, PostgreSQL, PostGIS, OSMnx, NetworkX, ML models or the simulation
engine.

------------------------------------------------------------------------

# 6. Database Architecture

The database should be divided conceptually into four groups.

``` text
CITYTWIN DATABASE
│
├── 1. BASE CITY MODEL
│   ├── cities
│   ├── roads
│   ├── intersections
│   ├── buildings
│   ├── places
│   └── zones
│
├── 2. DYNAMIC CITY STATE
│   ├── traffic_state
│   ├── transit_state
│   ├── weather_state
│   ├── air_quality_state
│   └── emergency_state
│
├── 3. SCENARIOS
│   ├── scenarios
│   ├── scenario_changes
│   └── simulation_runs
│
└── 4. RESULTS / HISTORY
    ├── simulation_metrics
    ├── recommendations
    └── data_ingestion_logs
```

------------------------------------------------------------------------

# 7. Core Database Tables

## cities

Stores supported cities.

``` text
city_id
name
country
state
latitude
longitude
boundary
created_at
updated_at
```

## roads

Stores the city's road network.

``` text
road_id
city_id
osm_id
name
road_type
length_m
speed_limit
lanes
capacity
geometry
created_at
updated_at
```

## intersections

``` text
intersection_id
city_id
osm_id
geometry
created_at
```

## places

One flexible table for POIs.

``` text
place_id
city_id
name
place_type
geometry
created_at
updated_at
```

Example `place_type` values:

``` text
hospital
fire_station
police_station
school
park
industrial_zone
```

## traffic_state

Stores timestamped traffic observations/model states.

``` text
traffic_id
road_id
vehicle_count
average_speed
congestion_level
recorded_at
source
```

## weather_state

``` text
weather_id
city_id
temperature
humidity
rainfall
wind_speed
recorded_at
source
```

## air_quality_state

``` text
air_quality_id
city_id
station_id
pollutant
value
unit
recorded_at
source
```

## scenarios

``` text
scenario_id
city_id
name
scenario_type
created_by
created_at
```

Example:

``` text
Road Closure — Anna Salai — 4 hours
```

## scenario_changes

``` text
change_id
scenario_id
road_id
change_type
start_time
end_time
capacity_factor
traffic_factor
weather_factor
```

## simulation_runs

``` text
run_id
scenario_id
started_at
completed_at
status
model_version
```

## simulation_metrics

``` text
metric_id
run_id
metric_type
baseline_value
scenario_value
change_percent
unit
```

## recommendations

``` text
recommendation_id
run_id
rank
intervention
score
reason
created_at
```

------------------------------------------------------------------------

# 8. Data Sources

## 8.1 OpenStreetMap

Use OpenStreetMap for the geographic baseline:

-   roads
-   intersections
-   buildings
-   hospitals
-   schools
-   fire stations
-   police stations
-   parks
-   POIs

Use OSMnx/Overpass-based extraction for the city model.

Official OSM API/data-access documentation:
https://wiki.openstreetmap.org/wiki/APIs

The Overpass API is designed for consumers to retrieve selected parts of
OSM data based on geography, object types and tags.

## 8.2 GTFS

GTFS provides standardized public-transit information.

Static GTFS can provide:

-   agencies
-   routes
-   trips
-   stops
-   schedules
-   calendars

GTFS Realtime can provide:

-   trip updates
-   vehicle positions
-   service alerts
-   delays
-   detours

Official documentation: https://gtfs.org/documentation/overview/

GTFS Realtime reference:
https://gtfs.org/documentation/realtime/reference/

Important: GTFS Realtime exists only when a transit agency publishes a
realtime feed. CITYTWIN should detect whether realtime data is available
instead of pretending every city has it.

## 8.3 OpenAQ

Use OpenAQ where coverage is available for air-quality observations.

Target fields:

``` text
station
latitude
longitude
pollutant
measurement
unit
timestamp
```

Official documentation: https://docs.openaq.org/

## 8.4 Copernicus Climate Data Store

Use Copernicus datasets for weather/climate/environmental information
where appropriate.

Official Climate Data Store: https://cds.climate.copernicus.eu/

The CDS supports programmatic data retrieval through its API.

For CITYTWIN, use this primarily for
historical/calibration/environmental datasets rather than pretending it
is a universal second-by-second live weather feed.

## 8.5 Municipal / Government Data

Where available, prefer city-specific official feeds for:

-   traffic
-   road closures
-   incidents
-   public transport
-   weather stations
-   emergency data
-   infrastructure

The ingestion layer should support different providers without changing
the database schema.

### Victoria Historical Traffic Observation Layer

Victoria telemetry data enters CITYTWIN through an intermediate
`HistoricalTrafficObservation` layer:

``` text
Victoria sensor files
    ↓
15-minute site + heading aggregation
    ↓
HistoricalTrafficObservation
    ↓
Future OSM/PostGIS enrichment
    ↓
TrafficStateRecord
```

The Victoria source provides traffic volume, vehicle classification, and
categorical speed-bin information. `telemetry_sites.csv` provides sensor
coordinates and descriptions. Raw traffic rows are aggregated across vehicle
classes and speed bins by site, heading, and exact 15-minute timestamp; rows
are not aggregated across headings.

Victoria site IDs identify telemetry sensors, not OSM road IDs. The
observation layer preserves those IDs and coordinates without performing OSM
matching. Road capacity, lanes, road length, measured average speed, weather,
and congestion are intentionally not fabricated. Speed bins remain source
information and are not converted into measured average speed.

Victoria timestamps are interpreted as local `Australia/Melbourne` time and
are stored with that timezone rather than being silently treated as UTC. The
observations retain `HISTORICAL` provenance and remain compatible with the
future target of vehicle volume at the exact same site and heading at T+15.

------------------------------------------------------------------------

# 9. Data Ingestion Architecture

Every external source should have its own connector.

``` text
ingestion/
│
├── osm/
│   ├── downloader.py
│   ├── parser.py
│   └── loader.py
│
├── gtfs/
│   ├── static.py
│   ├── realtime.py
│   └── loader.py
│
├── weather/
│   ├── client.py
│   └── loader.py
│
├── air_quality/
│   ├── client.py
│   └── loader.py
│
└── traffic/
    ├── client.py
    └── loader.py
```

Every connector should follow:

``` text
FETCH
  ↓
VALIDATE
  ↓
NORMALIZE
  ↓
TRANSFORM
  ↓
STORE
  ↓
LOG
```

------------------------------------------------------------------------

# 10. Data Freshness

Each dataset should have:

``` text
source
source_record_id
observed_at
ingested_at
```

This lets CITYTWIN answer:

> When was this information actually observed?

and:

> When did our system receive it?

Example:

``` text
observed_at = 10:30:00
ingested_at = 10:30:08
```

Do not silently treat old data as live data.

The frontend should show a freshness indicator:

``` text
Traffic       Updated 12 sec ago
Transit       Updated 35 sec ago
Weather       Updated 4 min ago
Air Quality   Updated 8 min ago
```

------------------------------------------------------------------------

# 11. Real-Time Update Strategy

Use different update intervals depending on the source.

``` text
GTFS Realtime
    ↓
frequent polling

Traffic feed
    ↓
frequent polling

Weather
    ↓
periodic polling

Air Quality
    ↓
periodic polling

OSM
    ↓
scheduled refresh

Static GTFS
    ↓
scheduled refresh
```

Do not force every source into a one-second update cycle.

GTFS Realtime guidance, for example, recommends frequent feed refreshes
and freshness constraints for vehicle positions and trip updates.

------------------------------------------------------------------------

# 12. Digital Twin State

The database is not the simulation itself.

The Digital Twin Core reads the latest state:

``` text
PostGIS
   ↓
Current roads
Current traffic
Current weather
Current transit
Current air quality
Current emergency assets
   ↓
DIGITAL TWIN STATE
```

The simulation can then create a temporary future state:

``` text
CURRENT STATE
     ↓
COPY
     ↓
APPLY SCENARIO
     ↓
SIMULATE
     ↓
FUTURE STATE
```

The real database should **not be corrupted by a hypothetical
scenario**.

------------------------------------------------------------------------

# 13. Scenario Engine

Example:

``` text
Scenario:
Close Road A

Duration:
4 hours
```

The scenario processor does:

``` text
Road A
capacity = 0
```

Then:

``` text
Road A closed
      ↓
Recalculate routes
      ↓
Traffic redistribution
      ↓
Congestion
      ↓
Transit delay
      ↓
Emergency ETA
      ↓
Pollution
      ↓
Population impact
```

This is the technical centerpiece of CITYTWIN.

------------------------------------------------------------------------

# 14. Simulation Engine

## Traffic

Represent the road network as a graph:

``` text
Intersection = Node
Road = Edge
```

Edge properties:

``` text
length
capacity
speed
traffic
travel_time
```

Scenario changes modify edge conditions.

The engine recalculates routing and congestion.

## Public Transport

Map transit routes onto the road network.

Calculate:

``` text
normal travel time
scenario travel time
delay
```

## Emergency

Use:

``` text
hospital/fire/police
+
road network
+
traffic state
```

Calculate baseline and scenario ETA.

## Pollution

Initially use a transparent estimation model based on:

``` text
traffic intensity
vehicle activity
weather factor
```

Do not present this as a scientifically validated pollution forecast
until it is properly calibrated.

------------------------------------------------------------------------

# 15. AI Layer

CITYTWIN uses AI for three major purposes.

## Prediction

``` text
Historical traffic
+ time
+ day
+ weather
+ events
        ↓
Future traffic
```

The initial traffic prediction implementation compares Linear Regression,
Random Forest Regressor, and XGBoost Regressor using the centralized feature
schema and a shared chronological split. This step implements only the
"AI predicts" portion of CITYTWIN.

## Pollution estimation

``` text
Traffic
+ weather
+ activity
        ↓
Estimated pollution impact
```

## Scenario impact prediction

Eventually:

``` text
Scenario parameters
        ↓
ML model
        ↓
Expected impact
```

AI should complement simulation.

### Key principle

**AI predicts. Simulation explains. Optimization recommends.**

------------------------------------------------------------------------

# 16. Optimization Layer

Run several possible interventions:

``` text
Option A
Full closure

Option B
Partial closure

Option C
Night closure
```

Calculate a multi-dimensional score:

``` text
traffic impact
+
transit impact
+
emergency impact
+
pollution impact
+
population impact
+
optional cost
```

Then rank the interventions.

Example:

``` text
Option A → Score 0.31
Option B → Score 0.14
Option C → Score 0.07

Recommendation → Option C
```

The weights must be configurable instead of hardcoded.

For example:

``` text
Emergency priority = 40%
Traffic priority    = 30%
Transit priority    = 15%
Pollution priority  = 15%
```

A different planner can change the priorities.

------------------------------------------------------------------------

# 17. API Architecture

FastAPI should expose endpoints such as:

``` text
GET    /cities
POST   /cities
GET    /cities/{city_id}

GET    /cities/{city_id}/roads
GET    /cities/{city_id}/places

GET    /cities/{city_id}/traffic/latest
GET    /cities/{city_id}/weather/latest
GET    /cities/{city_id}/air-quality/latest

POST   /scenarios
GET    /scenarios/{scenario_id}

POST   /simulations/run
GET    /simulations/{run_id}

GET    /simulations/{run_id}/metrics
GET    /simulations/{run_id}/recommendation

POST   /ingestion/{source}/refresh
GET    /ingestion/status
```

------------------------------------------------------------------------

# 18. Frontend

Main screen:

``` text
┌────────────────────────────────────────────────────┐
│ CITYTWIN                     City: Chennai ▼       │
├───────────────────────────┬────────────────────────┤
│                           │ SCENARIO BUILDER        │
│                           │                        │
│                           │ Type: Road Closure     │
│         CITY MAP          │ Road: [Select]         │
│                           │ Duration: [4 hrs]      │
│                           │ Rain: [+20%]           │
│                           │ Traffic: [+10%]        │
│                           │                        │
│                           │ [ SIMULATE ]           │
│                           │                        │
├───────────────────────────┴────────────────────────┤
│ IMPACT RESULTS                                     │
│ Traffic  │ Bus Delay │ Emergency │ Pollution       │
│  +31%    │ +13 min   │ +9 min    │ +16%            │
├────────────────────────────────────────────────────┤
│ RECOMMENDATION                                     │
│ Partial/night closure minimizes overall impact.    │
└────────────────────────────────────────────────────┘
```

------------------------------------------------------------------------

# 19. Data Flow for a Real-Time City

``` text
                    CITY
                     │
      ┌──────────────┼──────────────┐
      ↓              ↓              ↓
    Traffic        Transit        Weather
      │              │              │
      └──────────────┼──────────────┘
                     ↓
               INGESTION LAYER
                     ↓
              VALIDATION
                     ↓
               NORMALIZATION
                     ↓
             POSTGRES + POSTGIS
                     ↓
              CURRENT STATE
                     ↓
              DIGITAL TWIN
                     ↓
       ┌─────────────┼─────────────┐
       ↓             ↓             ↓
   Simulation       AI        Optimization
       │             │             │
       └─────────────┼─────────────┘
                     ↓
               RECOMMENDATION
                     ↓
                  USER
```

------------------------------------------------------------------------

# 20. Project Repository Structure

Recommended repository:

``` text
CITYTWIN/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   │
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── api/
│   │   ├── services/
│   │   │
│   │   ├── ingestion/
│   │   │   ├── osm/
│   │   │   ├── gtfs/
│   │   │   ├── weather/
│   │   │   ├── air_quality/
│   │   │   └── traffic/
│   │   │
│   │   ├── simulation/
│   │   ├── ai/
│   │   └── optimization/
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── map/
│   │   ├── scenarios/
│   │   ├── charts/
│   │   └── services/
│   └── package.json
│
├── database/
│   ├── migrations/
│   ├── schema.sql
│   └── indexes.sql
│
├── simulation/
│   ├── traffic/
│   ├── transit/
│   ├── emergency/
│   └── pollution/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── cache/
│
├── docker/
│   └── docker-compose.yml
│
├── docs/
│
├── .env.example
├── .gitignore
└── README.md
```

The `docker/docker-compose.yml` file is intended for local development and
reproducible service setup.

------------------------------------------------------------------------

# 21. Development Roadmap

## Phase 1 --- Database + City Ingestion

Build:

-   PostgreSQL
-   PostGIS
-   cities table
-   roads
-   intersections
-   places
-   OSM ingestion
-   spatial indexes

**Output:** real city map stored in database.

## Phase 2 --- Road Graph

Build:

-   OSMnx
-   NetworkX
-   road graph
-   shortest path
-   travel-time calculations

**Output:** simulation-ready road network.

## Phase 3 --- Traffic Simulation

Build:

-   traffic demand model
-   road capacity
-   congestion
-   routing
-   baseline state

**Output:** functioning traffic simulator.

## Phase 4 --- Road Closure

Build:

-   scenario builder
-   road capacity modification
-   rerouting
-   before/after metrics

**Output:** first CITYTWIN scenario.

## Phase 5 --- Emergency + Transit

Add:

-   hospitals
-   emergency routing
-   GTFS
-   bus delays

**Output:** cross-domain simulation.

## Phase 6 --- Weather + Pollution

Add:

-   weather ingestion
-   air-quality ingestion
-   traffic/weather interaction
-   pollution estimation

## Phase 7 --- AI

Add:

-   traffic forecasting
-   pollution estimation
-   scenario-impact prediction
-   model explainability

## Phase 8 --- Optimization

Add:

-   multiple interventions
-   scoring
-   ranking
-   recommendation engine

## Phase 9 --- Production Dashboard

Add:

-   polished map
-   live status
-   scenario builder
-   charts
-   recommendation cards
-   data freshness indicators
-   Vercel frontend deployment
-   Render FastAPI backend deployment
-   PostgreSQL + PostGIS production database

## Phase 10 --- Advanced Features

Future:

-   3D city visualization
-   IoT integration
-   water simulation
-   electricity simulation
-   disaster scenarios
-   more cities
-   live operational integrations

------------------------------------------------------------------------

# 22. MVP Definition

The MVP is complete when a user can:

``` text
1. Select a city
       ↓
2. Load real geographic data
       ↓
3. View the city on a map
       ↓
4. Select a road
       ↓
5. Close the road virtually
       ↓
6. Run simulation
       ↓
7. See traffic redistribution
       ↓
8. See congestion impact
       ↓
9. See emergency ETA impact
       ↓
10. Compare alternatives
       ↓
11. Receive a recommendation
```

Do NOT start with 3D, IoT, water, electricity or every possible AI
model.

The strongest hackathon demonstration is one complete scenario that
works reliably.

------------------------------------------------------------------------

# 23. What Makes CITYTWIN Different

### 1. Cross-domain simulation

Traffic + transit + emergency + pollution instead of separate
dashboards.

### 2. Cascading impact

A change in one system propagates through connected systems.

### 3. Scenario-based decisions

Users can test interventions before implementing them.

### 4. Automated city generation

The geographic city model is generated from external data rather than
manually designed.

### 5. AI + Simulation + Optimization

Prediction alone is insufficient.

### 6. Privacy-safe design

Use public aggregated data and synthetic/modelled dynamic data where
private data is unavailable.

------------------------------------------------------------------------

# 24. First Implementation Target

Do this exact sequence first:

``` text
PostgreSQL
    ↓
PostGIS
    ↓
OpenStreetMap
    ↓
OSMnx
    ↓
Chennai city model
    ↓
Road graph
    ↓
Synthetic/calibrated traffic state
    ↓
Road closure
    ↓
Rerouting
    ↓
Congestion
    ↓
Emergency ETA
    ↓
Scenario comparison
    ↓
Recommendation
```

After this pipeline works, add live GTFS, weather, air-quality and
traffic feeds.

------------------------------------------------------------------------

# 25. Data Integrity Rules

Never allow the project to silently mix:

-   live data
-   historical data
-   simulated data
-   predicted data

Every record should have metadata such as:

``` text
source
source_record_id
observed_at
ingested_at
data_type
quality_status
```

Recommended `data_type`:

``` text
REALTIME
HISTORICAL
MODELLED
PREDICTED
SCENARIO
```

This is critical for trust.

A dashboard should be able to say:

> Traffic: real observation, 22 seconds old.

or:

> Traffic: modelled because no live feed is available.

------------------------------------------------------------------------

# 26. Final Concept

CITYTWIN should ultimately behave like this:

``` text
                    REAL CITY
                       │
                       │ observations
                       ▼
                ┌──────────────┐
                │ DIGITAL TWIN │
                └──────┬───────┘
                       │
              "What if we..."
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
      Close road    Add event    Heavy rain
          │            │            │
          └────────────┼────────────┘
                       ▼
                   SIMULATE
                       │
                       ▼
             CASCADING IMPACTS
                       │
                       ▼
                  OPTIMIZE
                       │
                       ▼
                RECOMMENDATION
                       │
                       ▼
                  REAL DECISION
```

**CITYTWIN = Real city data + Digital Twin + Simulation + AI +
Optimization = Decision Intelligence.**
