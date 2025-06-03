import os
import asyncio
import logging
import openai
import aiohttp
from aiohttp import TCPConnector, ClientSession

# We will lazily initialize the aiohttp session when first making an OpenAI call
_oai_session = None

class BaseAgent:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        openai.api_key = os.getenv("OPENAI_API_KEY", "")  # ensure loaded

    async def _ensure_openai_session(self):
        global _oai_session
        if _oai_session is None:
            # Create TCPConnector on the running loop to force IPv4
            connector = TCPConnector(ssl=True, family=0)
            _oai_session = ClientSession(connector=connector)
            openai.aiosession.set(_oai_session)

    async def call_openai(self, **kwargs):
        """
        Wrap openai.ChatCompletion.acreate with retries and exponential back-off.
        Returns the response object on success, or None if all retries fail.
        """
        await self._ensure_openai_session()

        max_retries = 3
        backoff = 1  # seconds

        for attempt in range(1, max_retries + 1):
            try:
                return await openai.ChatCompletion.acreate(**kwargs)
            except (openai.error.APIConnectionError,
                    openai.error.RateLimitError,
                    asyncio.TimeoutError,
                    aiohttp.ClientConnectorError) as e:
                if attempt < max_retries:
                    self.logger.warning(
                        f"OpenAI call failed (attempt {attempt}/{max_retries}): {e!r}. "
                        f"Retrying in {backoff}s..."
                    )
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                else:
                    self.logger.error(
                        f"OpenAI call failed after {max_retries} attempts: {e!r}. Skipping."
                    )
                    return None

    async def close(self):
        """Close the shared aiohttp session at shutdown."""
        global _oai_session
        if _oai_session is not None:
            await _oai_session.close()
            _oai_session = None
