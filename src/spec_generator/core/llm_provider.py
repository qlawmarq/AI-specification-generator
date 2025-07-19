"""
LLM provider abstraction for different OpenAI configurations.

This module provides a unified interface for different LLM providers
including OpenAI, Azure OpenAI, and Google Gemini.
"""

import asyncio
import logging
import time
from typing import Any

from langchain_openai import ChatOpenAI, AzureChatOpenAI

from ..models import SpecificationConfig

logger = logging.getLogger(__name__)


class LLMProvider:
    """LLM provider abstraction for different OpenAI configurations."""

    def __init__(self, config: SpecificationConfig):
        self.config = config
        self._actual_model_name = None  # Initialize before _create_llm
        self.llm = self._create_llm()
        self.request_count = 0
        self.last_request_time = 0.0

    def _create_llm(self) -> Any:
        """Create LLM instance based on configuration."""
        # Determine provider
        provider = self.config.llm_provider or self._detect_provider()

        if provider == "gemini" and self.config.gemini_api_key:
            # Gemini API
            from langchain_google_genai import ChatGoogleGenerativeAI

            # Use gemini-specific model names
            model = self.config.llm_model or "gemini-2.0-flash"
            self._actual_model_name = model  # Store for metadata

            # Note: ChatGoogleGenerativeAI handles async operations internally

            return ChatGoogleGenerativeAI(
                model=model,
                temperature=0.3,
                google_api_key=self.config.gemini_api_key,
                max_retries=self.config.performance_settings.max_retries,
            )
        elif (
            provider == "azure"
            and self.config.azure_openai_endpoint
            and self.config.azure_openai_key
        ):
            # Azure OpenAI - using proper AzureChatOpenAI integration
            model = self.config.llm_model or "gpt-4"
            self._actual_model_name = model  # Store for metadata
            return AzureChatOpenAI(
                azure_deployment=model,  # Azure uses deployment name instead of model
                temperature=0.3,
                azure_endpoint=self.config.azure_openai_endpoint,
                api_key=self.config.azure_openai_key,
                api_version=self.config.azure_openai_version,
                timeout=self.config.performance_settings.request_timeout,
                max_retries=self.config.performance_settings.max_retries,
            )
        elif provider == "openai" and self.config.openai_api_key:
            # Standard OpenAI
            model = self.config.llm_model or "gpt-4"
            self._actual_model_name = model  # Store for metadata
            return ChatOpenAI(
                model=model,
                temperature=0.3,
                api_key=self.config.openai_api_key,
                timeout=self.config.performance_settings.request_timeout,
                max_retries=self.config.performance_settings.max_retries,
            )
        else:
            raise ValueError(f"No valid configuration found for provider: {provider}")

    def _detect_provider(self) -> str:
        """Auto-detect provider based on available credentials."""
        if self.config.gemini_api_key:
            return "gemini"
        elif self.config.azure_openai_endpoint and self.config.azure_openai_key:
            return "azure"
        elif self.config.openai_api_key:
            return "openai"
        return "unknown"

    async def _execute_with_retry(self, operation, operation_name: str, *args, **kwargs):
        """Execute an operation with retry logic and error handling."""
        max_retries = self.config.performance_settings.max_retries
        retry_delay = self.config.performance_settings.retry_delay

        for attempt in range(max_retries + 1):
            try:
                await self._rate_limit()
                return await operation(*args, **kwargs)

            except asyncio.TimeoutError:
                if attempt < max_retries:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.warning(f"{operation_name} timeout (attempt {attempt + 1}), retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"{operation_name} failed after {max_retries + 1} attempts due to timeout")
                    raise

            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)

                # Check for rate limit errors
                if "rate limit" in error_msg.lower() or "429" in error_msg:
                    if attempt < max_retries:
                        wait_time = retry_delay * (2 ** attempt) + 10
                        logger.warning(f"Rate limit exceeded (attempt {attempt + 1}), retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue

                # Check for temporary network errors
                if error_type in ["ConnectionError", "HTTPError", "RequestException"]:
                    if attempt < max_retries:
                        wait_time = retry_delay * (2 ** attempt)
                        logger.warning(f"Network error {error_type} (attempt {attempt + 1}), retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue

                # For other errors, fail immediately
                logger.error(f"{operation_name} failed: {error_type}: {e}")
                raise

    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response with rate limiting and retry logic."""
        async def _generate_operation():
            # Use async execution with timeout to avoid blocking
            # Reason: Apply configured timeout to LLM operations to prevent infinite waits
            timeout_seconds = self.config.performance_settings.request_timeout
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, self.llm.invoke, prompt
                ),
                timeout=timeout_seconds,
            )

            self.request_count += 1
            logger.debug(f"LLM request {self.request_count} completed")

            # Extract content from AIMessage if needed
            if hasattr(response, 'content'):
                return response.content
            return response

        return await self._execute_with_retry(_generate_operation, "LLM generation")

    async def generate_batch(self, prompts: list[str], **kwargs) -> list[str]:
        """Generate responses for multiple prompts using LangChain's batch processing with retry logic."""
        if not prompts:
            return []

        async def _batch_operation():
            # Use LangChain's native batch processing with timeout
            timeout_seconds = self.config.performance_settings.request_timeout

            logger.debug(f"Processing batch of {len(prompts)} prompts")
            start_time = time.time()

            # Use abatch for async batch processing
            responses = await asyncio.wait_for(
                self.llm.abatch(prompts),
                timeout=timeout_seconds * len(prompts)  # Scale timeout with batch size
            )

            batch_duration = time.time() - start_time
            self.request_count += len(prompts)


            logger.info(f"Batch of {len(prompts)} completed in {batch_duration:.2f}s "
                       f"({batch_duration/len(prompts):.2f}s per prompt)")

            # Extract content from responses
            results = []
            for response in responses:
                if hasattr(response, 'content'):
                    results.append(response.content)
                else:
                    results.append(str(response))

            return results

        return await self._execute_with_retry(_batch_operation, "Batch LLM generation")

    async def _rate_limit(self) -> None:
        """Implement rate limiting based on RPM."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 60.0 / self.config.performance_settings.rate_limit_rpm

        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)

        self.last_request_time = time.time()