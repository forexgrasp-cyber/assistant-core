"""
LLM Provider Base and Implementations
"""
import asyncio
import uuid
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, AsyncIterator, Union
from abc import ABC, abstractmethod
import structlog
import tiktoken

from ..config import get_ai_orchestrator_settings
from ..models import (
    LLMProvider, LLMProviderConfig, LLMMessage, LLMResponse,
    LLMProviderConfig, ToolDefinition
)

logger = structlog.get_logger(__name__)


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, config: LLMProviderConfig):
        self.config = config
        self.encoder = None
        self._init_tokenizer()

    def _init_tokenizer(self):
        """Initialize tokenizer for token counting"""
        try:
            # Default to cl100k_base (GPT-4 tokenizer)
            self.encoder = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.encoder = None

    @abstractmethod
    async def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Complete chat completion"""
        pass

    @abstractmethod
    async def stream_complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[LLMResponse]:
        """Stream chat completion"""
        yield LLMResponse(content="")  # Make it a proper async generator
        return
        yield  # Make it async generator

    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if self.encoder:
            return len(self.encoder.encode(text))
        # Fallback: rough estimate
        return len(text) // 4

    def count_message_tokens(self, messages: List[LLMMessage]) -> int:
        """Count tokens in messages"""
        total = 0
        for msg in messages:
            total += self.count_tokens(msg.content)
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    total += self.count_tokens(str(tc))
        return total

    async def close(self):
        """Cleanup resources"""
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider"""

    def __init__(self, config: LLMProviderConfig):
        super().__init__(config)
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            organization=config.organization,
            base_url=config.base_url,
            timeout=config.timeout_seconds,
            max_retries=config.max_retries,
        )
        self.default_model = config.default_model

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        start_time = time.time()

        try:
            response = await self.client.chat.completions.create(
                model=kwargs.get("model", self.default_model),
                messages=messages,
                tools=tools,
                temperature=temperature if temperature is not None else self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
                timeout=self.config.timeout_seconds,
                **kwargs
            )

            latency_ms = int((time.time() - start_time) * 1000)

            choice = response.choices[0]
            tool_calls = None
            if choice.message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in choice.message.tool_calls
                ]

            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }

            return LLMResponse(
                content=choice.message.content or "",
                tool_calls=tool_calls,
                finish_reason=choice.finish_reason,
                usage=usage,
                model=response.model,
                provider=LLMProvider.OPENAI,
                latency_ms=int((time.time() - start_time) * 1000)
            )

        except Exception as e:
            logger.error("openai_completion_error", error=str(e))
            raise

    async def stream_complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[LLMResponse]:
        try:
            stream = await self.client.chat.completions.create(
                model=kwargs.get("model", self.default_model),
                messages=messages,
                tools=tools,
                temperature=temperature if temperature is not None else self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
                stream=True,
                timeout=self.config.timeout_seconds,
                **kwargs
            )

            accumulated_content = ""
            accumulated_tool_calls = []

            async for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    content = delta.content or ""
                    accumulated_content += content

                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            if tc.index >= len(accumulated_tool_calls):
                                accumulated_tool_calls.append({
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""}
                                })
                            if tc.function.name:
                                accumulated_tool_calls[tc.index]["function"]["name"] = tc.function.name
                            if tc.function.arguments:
                                accumulated_tool_calls[tc.index]["function"]["arguments"] += tc.function.arguments

                    yield LLMResponse(
                        content=content,
                        tool_calls=[accumulated_tool_calls[-1]] if accumulated_tool_calls else None,
                        finish_reason=chunk.choices[0].finish_reason,
                        model=chunk.model,
                        provider=LLMProvider.OPENAI,
                        latency_ms=0
                    )

        except Exception as e:
            logger.error("openai_stream_error", error=str(e))
            raise

    async def close(self):
        await self.client.close()


class AnthropicProvider(BaseLLMProvider):
    """Anthropic API provider"""

    def __init__(self, config: LLMProviderConfig):
        super().__init__(config)
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(
            api_key=config.api_key,
            base_url=config.base_url or "https://api.anthropic.com",
            timeout=config.timeout_seconds,
            max_retries=config.max_retries,
        )
        self.default_model = config.default_model

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> tuple:
        """Convert OpenAI format to Anthropic format"""
        system_prompt = ""
        anthropic_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            elif msg["role"] == "tool":
                # Tool results
                anthropic_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.get("tool_call_id", ""),
                            "content": msg["content"]
                        }
                    ]
                })
            elif msg["role"] == "assistant" and msg.get("tool_calls"):
                # Assistant with tool calls
                content = []
                if msg.get("content"):
                    content.append({"type": "text", "text": msg["content"]})
                for tc in msg["tool_calls"]:
                    content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "input": tc["function"]["arguments"]
                    })
                anthropic_messages.append({"role": "assistant", "content": content})
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        return system_prompt, anthropic_messages

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        start_time = time.time()

        try:
            system_prompt, anthropic_messages = self._convert_messages(messages)

            # Convert tools to Anthropic format
            anthropic_tools = None
            if tools:
                anthropic_tools = [
                    {
                        "name": t["function"]["name"],
                        "description": t["function"]["description"],
                        "input_schema": t["function"]["parameters"]
                    }
                    for t in tools
                ]

            response = await self.client.messages.create(
                model=kwargs.get("model", self.default_model),
                system=system_prompt,
                messages=anthropic_messages,
                tools=anthropic_tools,
                temperature=temperature if temperature is not None else self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
                timeout=self.config.timeout_seconds,
                **kwargs
            )

            latency_ms = int((time.time() - start_time) * 1000)

            content = ""
            tool_calls = None

            for block in response.content:
                if block.type == "text":
                    content += block.text
                elif block.type == "tool_use":
                    if tool_calls is None:
                        tool_calls = []
                    tool_calls.append({
                        "id": block.id,
                        "type": "function",
                        "function": {
                            "name": block.name,
                            "arguments": block.input
                        }
                    })

            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                }

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                finish_reason=response.stop_reason,
                usage=usage,
                model=response.model,
                provider=LLMProvider.ANTHROPIC,
                latency_ms=int((time.time() - start_time) * 1000)
            )

        except Exception as e:
            logger.error("anthropic_completion_error", error=str(e))
            raise

    async def stream_complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[LLMResponse]:
        # Anthropic streaming is more complex, implement if needed
        raise NotImplementedError("Anthropic streaming not yet implemented")


class LocalLLMProvider(BaseLLMProvider):
    """Local LLM provider (Ollama, etc.)"""

    def __init__(self, config: LLMProviderConfig):
        super().__init__(config)
        import httpx
        self.client = httpx.AsyncClient(
            base_url=config.base_url or "http://localhost:11434",
            timeout=config.timeout_seconds,
        )
        self.default_model = config.default_model

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        start_time = time.time()

        try:
            # Ollama format
            payload = {
                "model": kwargs.get("model", self.default_model),
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature if temperature is not None else self.config.temperature,
                    "num_predict": max_tokens or self.config.max_tokens,
                }
            }

            response = await self.client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

            latency_ms = int((time.time() - start_time) * 1000)

            return LLMResponse(
                content=data.get("message", {}).get("content", ""),
                finish_reason="stop",
                model=data.get("model"),
                provider=LLMProvider.LOCAL,
                latency_ms=latency_ms
            )

        except Exception as e:
            logger.error("local_llm_completion_error", error=str(e))
            raise

    async def stream_complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[LLMResponse]:
        try:
            payload = {
                "model": kwargs.get("model", self.default_model),
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": temperature if temperature is not None else self.config.temperature,
                    "num_predict": max_tokens or self.config.max_tokens,
                }
            }

            async with self.client.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        import json
                        data = json.loads(line)
                        if "message" in data:
                            content = data["message"].get("content", "")
                            yield LLMResponse(
                                content=content,
                                finish_reason="stop" if data.get("done") else None,
                                model=data.get("model"),
                                provider=LLMProvider.LOCAL,
                                latency_ms=0
                            )
                        if data.get("done"):
                            break

        except Exception as e:
            logger.error("local_llm_stream_error", error=str(e))
            raise

    async def close(self):
        await self.client.aclose()


import time


class LLMProviderFactory:
    """Factory for creating LLM providers"""

    _providers: Dict[LLMProvider, BaseLLMProvider] = {}

    @classmethod
    def create_provider(cls, provider: LLMProvider, config: Optional[LLMProviderConfig] = None) -> BaseLLMProvider:
        settings = get_ai_orchestrator_settings()

        if config is None:
            config = LLMProviderConfig(
                provider=provider,
                default_model=cls._get_default_model(provider, settings),
                api_key=cls._get_api_key(provider, settings),
                base_url=cls._get_base_url(provider, settings),
            )

        if provider == LLMProvider.OPENAI:
            return OpenAIProvider(config)
        elif provider == LLMProvider.ANTHROPIC:
            return AnthropicProvider(config)
        elif provider == LLMProvider.LOCAL:
            return LocalLLMProvider(config)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    @classmethod
    def _get_default_model(cls, provider: LLMProvider, settings: Any) -> str:
        if provider == LLMProvider.OPENAI:
            return settings.openai_default_model
        elif provider == LLMProvider.ANTHROPIC:
            return settings.anthropic_default_model
        elif provider == LLMProvider.LOCAL:
            return settings.local_llm_model
        return "gpt-4o-mini"

    @classmethod
    def _get_api_key(cls, provider: LLMProvider, settings: Any) -> Optional[str]:
        if provider == LLMProvider.OPENAI:
            return settings.openai_api_key
        elif provider == LLMProvider.ANTHROPIC:
            return settings.anthropic_api_key
        return None

    @classmethod
    def _get_base_url(cls, provider: LLMProvider, settings: Any) -> Optional[str]:
        if provider == LLMProvider.LOCAL:
            return settings.local_llm_base_url
        return None

    @classmethod
    async def get_default_provider(cls) -> BaseLLMProvider:
        settings = get_ai_orchestrator_settings()
        return cls.create_provider(LLMProvider(settings.default_llm_provider))