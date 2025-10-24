"""Simple HTTP health check server for container monitoring."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from aiohttp import web


logger = logging.getLogger(__name__)


class HealthCheckServer:
    """Simple HTTP server for health checks.

    Provides /health endpoint for container orchestration systems
    (Docker, Render, Kubernetes) to verify the bot is running.
    """

    def __init__(self, port: int = 8080, scheduler=None):
        """Initialize health check server.

        Args:
            port: HTTP port to listen on (default: 8080)
            scheduler: APScheduler instance to check status (optional)
        """
        self.port = port
        self.scheduler = scheduler
        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self.start_time = datetime.now(timezone.utc)

        # Register routes
        self.app.router.add_get('/health', self.health_handler)
        self.app.router.add_get('/', self.health_handler)  # Root also responds

    async def health_handler(self, request: web.Request) -> web.Response:
        """Handle health check requests.

        Returns:
            JSON response with health status and scheduler info
        """
        uptime_seconds = (datetime.now(timezone.utc) - self.start_time).total_seconds()

        health_data = {
            "status": "healthy",
            "uptime_seconds": int(uptime_seconds),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Include scheduler status if available
        if self.scheduler:
            scheduler_running = self.scheduler.running
            health_data["scheduler"] = {
                "running": scheduler_running,
                "jobs": [
                    {
                        "id": job.id,
                        "name": job.name,
                        "next_run": job.next_run_time.isoformat() if job.next_run_time else None
                    }
                    for job in self.scheduler.get_jobs()
                ]
            }
        else:
            health_data["scheduler"] = {"running": False, "jobs": []}

        return web.json_response(health_data)

    async def start(self) -> None:
        """Start the health check server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        self.site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await self.site.start()

        logger.info(f"Health check server started on port {self.port}")
        logger.info(f"  GET http://0.0.0.0:{self.port}/health")

    async def stop(self) -> None:
        """Stop the health check server."""
        if self.site:
            await self.site.stop()

        if self.runner:
            await self.runner.cleanup()

        logger.info("Health check server stopped")
