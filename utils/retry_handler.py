import time
import random
import functools
import logging
from typing import Callable, Type, Tuple, Optional

logger = logging.getLogger("retry")

class RetryHandler:
    """
    ejecuta funciones con reintentos automáticos y backoff exponencial.
    """
    def __init__(
        self,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_exceptions = retry_exceptions
    
    def execute(self, func: Callable, *args, **kwargs):
        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except self.retry_exceptions as e:
                last_exception = e
                if attempt == self.max_retries:
                    logger.error(f"fallo después de {self.max_retries} intentos: {e}")
                    raise last_exception
                delay = self._calculate_delay(attempt)
                logger.warning(f"intento {attempt}/{self.max_retries} falló: {e}. reintentando en {delay:.1f}s...")
                time.sleep(delay)
        raise last_exception
    
    async def execute_async(self, func: Callable, *args, **kwargs):
        import asyncio
        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except self.retry_exceptions as e:
                last_exception = e
                if attempt == self.max_retries:
                    logger.error(f"fallo después de {self.max_retries} intentos: {e}")
                    raise last_exception
                delay = self._calculate_delay(attempt)
                logger.warning(f"intento {attempt}/{self.max_retries} falló: {e}. reintentando en {delay:.1f}s...")
                await asyncio.sleep(delay)
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)
        if self.jitter:
            delay = delay * (0.75 + random.random() * 0.5)
        return delay

alpaca_retry = RetryHandler(
    max_retries=5, base_delay=2.0, max_delay=30.0,
    retry_exceptions=(ConnectionError, TimeoutError, Exception)
)