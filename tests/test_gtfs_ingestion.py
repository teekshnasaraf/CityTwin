"""
Unit tests for GTFS Static & Realtime ETL Ingestion Pipelines.
"""
from backend.app.ingestion.gtfs.static import GTFSStaticParser
from backend.app.ingestion.gtfs.realtime import GTFSRealtimeFetcher
from backend.app.ingestion.gtfs.loader import GTFSLoader


class MockSession:
    def add(self, item): pass
    def commit(self): pass
    def rollback(self): pass


def test_gtfs_static_parser():
    """Verify GTFS static feed parser returns routes and stops."""
    feed = GTFSStaticParser.download_and_parse(feed_url=None)
    assert "routes" in feed
    assert "stops" in feed
    assert len(feed["routes"]) > 0
    assert len(feed["stops"]) > 0


def test_gtfs_realtime_fetcher():
    """Verify GTFS Realtime fetcher returns vehicle positions."""
    rt_data = GTFSRealtimeFetcher.fetch_live_updates()
    assert "vehicle_positions" in rt_data
    assert "data_type" in rt_data
    assert rt_data["data_type"] == "REALTIME"
    assert len(rt_data["vehicle_positions"]) > 0


def test_gtfs_loader_pipeline():
    """Verify end-to-end GTFS loader pipeline output."""
    db = MockSession()
    res = GTFSLoader.load_gtfs_pipeline(db=db, city_id=1)
    assert res["status"] == "COMPLETED"
    assert res["city_id"] == 1
    assert res["routes_count"] > 0
    assert res["vehicles_tracked"] > 0
