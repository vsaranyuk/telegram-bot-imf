"""Tests for health check server."""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase

from src.health_check import HealthCheckServer


class TestHealthCheckServer(AioHTTPTestCase):
    """Test suite for HealthCheckServer."""

    async def get_application(self):
        """Create test application."""
        # Create mock scheduler
        mock_scheduler = Mock()
        mock_scheduler.running = True

        # Create mock job
        mock_job = Mock()
        mock_job.id = "test_job"
        mock_job.name = "Test Job"
        mock_job.next_run_time = datetime.now(timezone.utc)

        mock_scheduler.get_jobs = Mock(return_value=[mock_job])

        # Create server
        server = HealthCheckServer(port=8080, scheduler=mock_scheduler)
        return server.app

    async def test_health_endpoint(self):
        """Test /health endpoint returns healthy status."""
        resp = await self.client.request("GET", "/health")
        assert resp.status == 200

        data = await resp.json()
        assert data["status"] == "healthy"
        assert "uptime_seconds" in data
        assert "timestamp" in data
        assert "scheduler" in data

    async def test_root_endpoint(self):
        """Test root endpoint also returns health status."""
        resp = await self.client.request("GET", "/")
        assert resp.status == 200

        data = await resp.json()
        assert data["status"] == "healthy"

    async def test_scheduler_status_included(self):
        """Test scheduler status is included in response."""
        resp = await self.client.request("GET", "/health")
        data = await resp.json()

        assert "scheduler" in data
        assert data["scheduler"]["running"] is True
        assert "jobs" in data["scheduler"]
        assert len(data["scheduler"]["jobs"]) > 0

        job = data["scheduler"]["jobs"][0]
        assert job["id"] == "test_job"
        assert job["name"] == "Test Job"
        assert job["next_run"] is not None


class TestHealthCheckServerWithoutScheduler:
    """Test health check without scheduler."""

    @pytest.mark.asyncio
    async def test_health_without_scheduler(self):
        """Test health check when scheduler is not provided."""
        server = HealthCheckServer(port=8080, scheduler=None)

        # Create mock request
        request = Mock()

        response = await server.health_handler(request)

        assert response.status == 200
        # Response should still work without scheduler
        # (scheduler field would show running=False)


@pytest.mark.asyncio
async def test_server_start_stop():
    """Test server can start and stop cleanly."""
    server = HealthCheckServer(port=8888)

    await server.start()
    assert server.runner is not None
    assert server.site is not None

    await server.stop()
