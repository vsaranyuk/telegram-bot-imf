"""Webhook server for receiving Telegram updates via HTTP.

This module provides an aiohttp-based webhook server that replaces
long polling for receiving Telegram updates. Key benefits:
- Instant message delivery (no polling delay)
- Lower resource usage (no constant HTTP requests)
- Better scalability (push vs pull model)
"""

import asyncio
import hashlib
import hmac
import ipaddress
import json
import logging
from typing import Callable, Optional

from aiohttp import web
from telegram import Update
from telegram.ext import Application

from src.config.settings import Settings

logger = logging.getLogger(__name__)


class WebhookServer:
    """HTTP server for receiving Telegram webhook updates.

    Handles incoming POST requests from Telegram API with security validation:
    - Secret token verification (X-Telegram-Bot-Api-Secret-Token)
    - IP whitelist validation (Telegram server IPs)
    - Request payload validation

    Attributes:
        app: aiohttp web application
        runner: aiohttp web runner
        site: aiohttp TCP site
        port: HTTP server port
        webhook_path: URL path for webhook endpoint
        secret_token: Secret token for request validation
    """

    # Telegram API server IP ranges (as of 2024)
    # Source: https://core.telegram.org/bots/webhooks#the-short-version
    TELEGRAM_IP_RANGES = [
        "149.154.160.0/20",  # Primary Telegram servers
        "91.108.4.0/22",     # Telegram servers (EU)
    ]

    def __init__(
        self,
        application: Application,
        settings: Settings,
        webhook_path: str = "/webhook"
    ):
        """Initialize webhook server.

        Args:
            application: Telegram Application instance for update processing
            settings: Application settings with configuration
            webhook_path: URL path for webhook endpoint (default: /webhook)
        """
        self.application = application
        self.settings = settings
        self.webhook_path = webhook_path
        self.secret_token = settings.webhook_secret_token
        self.port = settings.webhook_port

        # aiohttp components
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None

        # Precompute IP networks for validation
        self._telegram_networks = [
            ipaddress.ip_network(net) for net in self.TELEGRAM_IP_RANGES
        ]

    def _is_telegram_ip(self, ip_address: str) -> bool:
        """Validate if IP address belongs to Telegram servers.

        Args:
            ip_address: Client IP address string

        Returns:
            True if IP is in Telegram ranges, False otherwise
        """
        try:
            ip = ipaddress.ip_address(ip_address)
            return any(ip in network for network in self._telegram_networks)
        except ValueError:
            logger.error(f"Invalid IP address format: {ip_address}")
            return False

    def _validate_secret_token(self, request: web.Request) -> bool:
        """Validate X-Telegram-Bot-Api-Secret-Token header.

        Args:
            request: aiohttp request object

        Returns:
            True if token matches, False otherwise
        """
        token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")

        if not self.secret_token:
            # No secret token configured - warn and allow (for local testing)
            logger.warning(
                "No WEBHOOK_SECRET_TOKEN configured. "
                "This is insecure for production!"
            )
            return True

        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(token, self.secret_token)

    async def handle_webhook(self, request: web.Request) -> web.Response:
        """Handle incoming webhook POST request from Telegram.

        Security validations:
        1. IP address whitelist
        2. Secret token verification
        3. JSON payload validation

        Args:
            request: aiohttp request object

        Returns:
            HTTP response (200 OK or error)
        """
        # Get client IP (handle X-Forwarded-For from Render proxy)
        client_ip = request.headers.get(
            "X-Forwarded-For",
            request.remote or ""
        ).split(",")[0].strip()

        logger.debug(f"📨 Webhook request from {client_ip}")

        # Security validation: IP whitelist
        if not self._is_telegram_ip(client_ip):
            logger.warning(
                f"⚠️ Rejected webhook from unauthorized IP: {client_ip}"
            )
            return web.Response(status=403, text="Forbidden: Invalid source IP")

        # Security validation: Secret token
        if not self._validate_secret_token(request):
            logger.warning(
                f"⚠️ Rejected webhook with invalid secret token from {client_ip}"
            )
            return web.Response(status=401, text="Unauthorized: Invalid token")

        # Parse and validate JSON payload
        try:
            data = await request.json()
            logger.debug(f"Webhook payload: {json.dumps(data, indent=2)[:500]}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse webhook JSON: {e}")
            return web.Response(status=400, text="Bad Request: Invalid JSON")

        # Process Telegram Update
        try:
            # Create Update object from JSON
            update = Update.de_json(data, self.application.bot)

            if not update:
                logger.warning("Received empty update from Telegram")
                return web.Response(status=200, text="OK")

            logger.debug(
                f"✅ Processing update {update.update_id} "
                f"(type: {update.effective_message and 'message' or 'other'})"
            )

            # Process update through bot handlers
            # This is async, so we don't wait for completion
            asyncio.create_task(
                self.application.process_update(update)
            )

            # Telegram expects 200 OK quickly (within 1 second)
            return web.Response(status=200, text="OK")

        except Exception as e:
            logger.error(f"Error processing webhook update: {e}", exc_info=True)
            # Still return 200 to prevent Telegram retries
            return web.Response(status=200, text="OK")

    async def handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint for Render.

        Args:
            request: aiohttp request object

        Returns:
            HTTP 200 OK if server is healthy
        """
        return web.Response(status=200, text="OK")

    async def start(self) -> None:
        """Start the webhook HTTP server.

        Creates aiohttp application, registers routes, and starts TCP listener.
        """
        logger.info(f"🌐 Starting webhook server on port {self.port}")
        logger.info(f"📍 Webhook endpoint: {self.webhook_path}")
        logger.info(f"🔐 Secret token: {'configured' if self.secret_token else 'NOT SET (insecure!)'}")

        # Create aiohttp app
        self.app = web.Application()

        # Register routes
        self.app.router.add_post(self.webhook_path, self.handle_webhook)
        self.app.router.add_get("/health", self.handle_health)

        # Start server
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        self.site = web.TCPSite(
            self.runner,
            host="0.0.0.0",  # Listen on all interfaces (required for Render)
            port=self.port
        )

        await self.site.start()

        logger.info(f"✅ Webhook server started successfully on 0.0.0.0:{self.port}")

    async def stop(self) -> None:
        """Stop the webhook HTTP server gracefully."""
        logger.info("Stopping webhook server...")

        if self.site:
            await self.site.stop()

        if self.runner:
            await self.runner.cleanup()

        logger.info("Webhook server stopped")
