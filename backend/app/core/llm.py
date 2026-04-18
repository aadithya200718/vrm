"""
LLM configuration with Ollama primary and Groq fallback.
"""
import logging
from typing import Optional
from langchain_community.chat_models import ChatOllama
from langchain_groq import ChatGroq
from langchain_core.language_models import BaseChatModel
from app.config import get_settings

logger = logging.getLogger(__name__)

_llm_instance: Optional[BaseChatModel] = None


def get_llm() -> BaseChatModel:
    """
    Get the configured LLM with automatic fallback.
    Primary: Ollama (local, free)
    Fallback: Groq (cloud, free tier)
    """
    global _llm_instance
    if _llm_instance is not None:
        return _llm_instance

    settings = get_settings()

    # Primary: Ollama (self-hosted)
    primary_llm = ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0,
        num_predict=4096,
    )
    logger.info(
        f"Primary LLM configured: Ollama ({settings.ollama_model}) "
        f"at {settings.ollama_base_url}"
    )

    # Fallback: Groq (cloud)
    if settings.groq_api_key:
        fallback_llm = ChatGroq(
            model="llama-3.1-70b-versatile",
            api_key=settings.groq_api_key,
            temperature=0,
            max_tokens=4096,
        )
        logger.info("Fallback LLM configured: Groq (llama-3.1-70b-versatile)")
        _llm_instance = primary_llm.with_fallbacks([fallback_llm])
    else:
        logger.warning("No GROQ_API_KEY set — running without fallback LLM")
        _llm_instance = primary_llm

    return _llm_instance


def get_ollama_direct() -> ChatOllama:
    """Get a direct Ollama instance (no fallback)."""
    settings = get_settings()
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0,
        num_predict=4096,
    )


def check_llm_health() -> dict:
    """Check if LLM services are available."""
    status = {"ollama": False, "groq": False}
    settings = get_settings()

    # Check Ollama
    try:
        import httpx
        resp = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
        status["ollama"] = resp.status_code == 200
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")

    # Check Groq
    if settings.groq_api_key:
        try:
            groq = ChatGroq(
                model="llama-3.1-8b-instant",
                api_key=settings.groq_api_key,
                temperature=0,
                max_tokens=10,
            )
            groq.invoke("ping")
            status["groq"] = True
        except Exception as e:
            logger.warning(f"Groq health check failed: {e}")

    return status
