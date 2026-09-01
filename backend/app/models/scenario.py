"""
Scenario, Simulation, Recommendation & Ingestion Log SQLAlchemy ORM definitions.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import relationship

try:
    from app.database import Base
except ImportError:
    from ..database import Base


class Scenario(Base):
    """Stores user-defined hypothetical interventions."""
    __tablename__ = "scenarios"

    scenario_id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, ForeignKey("cities.city_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    scenario_type = Column(String(100), nullable=False)
    created_by = Column(String(100), nullable=True, default="user")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    changes = relationship("ScenarioChange", back_populates="scenario", cascade="all, delete-orphan")
    runs = relationship("SimulationRun", back_populates="scenario", cascade="all, delete-orphan")


class ScenarioChange(Base):
    """Stores parameters for specific road interventions within a scenario."""
    __tablename__ = "scenario_changes"

    change_id = Column(BigInteger, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.scenario_id", ondelete="CASCADE"), nullable=False, index=True)
    road_id = Column(BigInteger, ForeignKey("roads.road_id", ondelete="SET NULL"), nullable=True)
    change_type = Column(String(100), nullable=False)  # e.g., 'road_closure', 'capacity_reduction'
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    capacity_factor = Column(Float, default=1.0)  # 0.0 = total closure, 0.5 = 50% capacity
    traffic_factor = Column(Float, default=1.0)   # 1.1 = +10% traffic multiplier
    weather_factor = Column(Float, default=1.0)   # 1.2 = +20% rain multiplier

    scenario = relationship("Scenario", back_populates="changes")


class SimulationRun(Base):
    """Tracks execution instances of scenarios against the Digital Twin state."""
    __tablename__ = "simulation_runs"

    run_id = Column(BigInteger, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.scenario_id", ondelete="CASCADE"), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False, default="completed")
    model_version = Column(String(50), nullable=False, default="1.0.0")

    scenario = relationship("Scenario", back_populates="runs")
    metrics = relationship("SimulationMetric", back_populates="run", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="run", cascade="all, delete-orphan")


class SimulationMetric(Base):
    """Stores quantitative baseline vs scenario cascading impact metrics."""
    __tablename__ = "simulation_metrics"

    metric_id = Column(BigInteger, primary_key=True, index=True)
    run_id = Column(BigInteger, ForeignKey("simulation_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    metric_type = Column(String(100), nullable=False)  # e.g., 'traffic_congestion', 'bus_delay', 'emergency_eta', 'pollution'
    baseline_value = Column(Float, nullable=False)
    scenario_value = Column(Float, nullable=False)
    change_percent = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)

    run = relationship("SimulationRun", back_populates="metrics")


class Recommendation(Base):
    """Stores ranked multi-objective intervention recommendations."""
    __tablename__ = "recommendations"

    recommendation_id = Column(BigInteger, primary_key=True, index=True)
    run_id = Column(BigInteger, ForeignKey("simulation_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    rank = Column(Integer, nullable=False)
    intervention = Column(String(255), nullable=False)
    score = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    run = relationship("SimulationRun", back_populates="recommendations")


class DataSource(Base):
    """Catalogs registered external data feeds and update policies."""
    __tablename__ = "data_sources"

    source_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    source_type = Column(String(50), nullable=False)
    url = Column(String(500), nullable=True)
    refresh_interval_seconds = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class IngestionLog(Base):
    """Tracks external data pipeline runs, throughput, and status."""
    __tablename__ = "ingestion_logs"

    log_id = Column(BigInteger, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("data_sources.source_id", ondelete="SET NULL"), nullable=True)
    city_id = Column(Integer, ForeignKey("cities.city_id", ondelete="SET NULL"), nullable=True)
    dataset_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    records_processed = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class DataQualityLog(Base):
    """Records validation rules, anomaly detection, and data integrity checks."""
    __tablename__ = "data_quality_logs"

    quality_id = Column(BigInteger, primary_key=True, index=True)
    log_id = Column(BigInteger, ForeignKey("ingestion_logs.log_id", ondelete="SET NULL"), nullable=True)
    dataset_type = Column(String(50), nullable=False)
    check_name = Column(String(100), nullable=False)
    passed = Column(Boolean, nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
