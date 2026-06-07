import os
import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("vrski.mcp.http_client")

class VrskiHttpClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.environ.get("VRSKI_API_URL", "http://localhost:7070")
        self._client: Optional[httpx.AsyncClient] = None
        logger.info(f"Vrski HTTP Client initialized with base URL: {self.base_url}")

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.info("Vrski HTTP Client connection pool closed.")

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            client = await self.get_client()
            res = await client.get(url, params=params)
            if res.status_code == 200:
                return res.json()
            try:
                return res.json()
            except Exception:
                return {"success": False, "error": f"HTTP {res.status_code}: {res.text}"}
        except Exception as e:
            logger.exception(f"GET request to {url} failed")
            return {"success": False, "error": f"Connection error: {str(e)}"}

    async def post(self, path: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            client = await self.get_client()
            timeout = 360.0 if "install" in path else 150.0 if "auth" in path or "wait" in path or "setup" in path else 30.0
            res = await client.post(url, json=json, timeout=timeout)
            if res.status_code == 200:
                return res.json()
            try:
                return res.json()
            except Exception:
                return {"success": False, "error": f"HTTP {res.status_code}: {res.text}"}
        except Exception as e:
            logger.exception(f"POST request to {url} failed")
            return {"success": False, "error": f"Connection error: {str(e)}"}
