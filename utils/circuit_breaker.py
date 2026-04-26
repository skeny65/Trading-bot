import time
import logging
from typing import Callable, Optional
from enum import Enum

logger = logging.getLogger("circuit_breaker")

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """
    evita llamadas repetidas a servicios fallidos.
    """
    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None

    def call(self, func: Callable, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if (time.time() - self.last_failure_time) >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info(f"circuit {self.name}: probando recuperación")
            else:
                raise Exception(f"circuito {self.name} abierto")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            logger.info(f"circuit {self.name}: recuperado")

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(f"circuit {self.name}: abierto tras {self.failure_threshold} fallos")

alpaca_breaker = CircuitBreaker("alpaca", failure_threshold=5, recovery_timeout=120)