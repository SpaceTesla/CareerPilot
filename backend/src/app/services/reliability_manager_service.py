from __future__ import annotations

import logging
from typing import Callable, Any, Optional
from datetime import datetime, timezone
from uuid import uuid4

from app.core.logging import get_logger
from app.services.redis_service import RedisService
from app.utils.event_bus import EventBus

logger = get_logger(__name__)

class CircuitOpenException(Exception):
    """Exception raised when a circuit breaker is in OPEN state."""
    pass

class ReliabilityManagerService:
    """
    Reliability Manager Service (F6.3).
    Enforces circuit breakers and rate limits to guarantee system resilience.
    """

    @classmethod
    async def check_rate_limit(
        cls, user_id: str, route: str, limit: int, window_seconds: int
    ) -> bool:
        """
        Token-bucket rate limiter using an atomic Redis Lua script.
        Returns True if request is allowed, False if limit is exceeded.
        """
        key = f"rate_limit:{user_id}:{route}"
        
        # Atomic read-and-increment Lua script
        lua_script = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local current = tonumber(redis.call('get', key) or "0")
        if current >= limit then
            return 0
        else
            redis.call("incrby", key, 1)
            if current == 0 then
                redis.call("expire", key, window)
            end
            return 1
        end
        """
        
        try:
            async with RedisService.get_client() as redis:
                result = await redis.eval(lua_script, 1, key, limit, window_seconds)
                return result == 1
        except Exception as e:
            logger.error(f"Rate limiter check failed: {e}. Allowing request as graceful degradation.")
            return True

    @classmethod
    async def execute_with_breaker(
        cls, service_name: str, func: Callable[[], Any], fallback_func: Optional[Callable[[], Any]] = None
    ) -> Any:
        """
        Executes external function wrapped in a Redis-backed circuit breaker.
        Falls back if the circuit is OPEN.
        """
        state_key = f"circuit_breaker:{service_name}:state"
        fail_key = f"circuit_breaker:{service_name}:failure_count"
        time_key = f"circuit_breaker:{service_name}:last_failure_at"
        
        async with RedisService.get_client() as redis:
            state_bytes = await redis.get(state_key)
            state = state_bytes.decode("utf-8") if state_bytes else "CLOSED"
            
            # Cooldown logic: if OPEN but cool-down (e.g. 60s) passed, set to HALF_OPEN
            if state == "OPEN":
                last_fail_bytes = await redis.get(time_key)
                if last_fail_bytes:
                    try:
                        last_fail_dt = datetime.fromisoformat(last_fail_bytes.decode("utf-8"))
                        if (datetime.now(timezone.utc) - last_fail_dt).total_seconds() > 60:
                            state = "HALF_OPEN"
                            await redis.set(state_key, "HALF_OPEN")
                            logger.info(f"Circuit breaker for {service_name} transitioned to HALF_OPEN due to cooldown expiration.")
                    except Exception as e:
                        logger.warning(f"Error parsing last failure time: {e}")
            
            if state == "OPEN":
                logger.warning(f"Circuit breaker for {service_name} is OPEN. Executing fallback.")
                if fallback_func:
                    if asyncio_is_coroutine(fallback_func):
                        return await fallback_func()
                    return fallback_func()
                raise CircuitOpenException(f"Circuit breaker is open for service: {service_name}")
            
            try:
                # Execute primary operation
                import inspect
                if inspect.iscoroutinefunction(func):
                    result = await func()
                else:
                    result = func()
                
                # Success: transition HALF_OPEN back to CLOSED, reset fails
                if state == "HALF_OPEN":
                    await redis.set(state_key, "CLOSED")
                    logger.info(f"Circuit breaker for {service_name} recovered and transitioned to CLOSED.")
                await redis.delete(fail_key)
                await redis.delete(time_key)
                return result
                
            except Exception as err:
                logger.error(f"Error during protected call for {service_name}: {err}")
                
                # Increment failure count
                fail_count = await redis.incr(fail_key)
                if fail_count == 1:
                    await redis.expire(fail_key, 60) # reset failure count window in 1 minute
                
                await redis.set(time_key, datetime.now(timezone.utc).isoformat())
                
                # Trigger circuit transition if count >= 5
                if fail_count >= 5 and state != "OPEN":
                    await redis.set(state_key, "OPEN")
                    logger.error(f"Circuit breaker for {service_name} has OPENED due to {fail_count} failures.")
                    
                    # Publish event
                    try:
                        await EventBus.publish(
                            "circuit.opened",
                            {
                                "event_id": f"evt_circ_opn_{str(uuid4())[:8]}",
                                "event_type": "circuit.opened",
                                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                                "payload": {
                                    "service_name": service_name,
                                    "failure_count": int(fail_count),
                                    "last_error": str(err)
                                }
                            }
                        )
                    except Exception as ev_err:
                        logger.error(f"Failed to publish circuit.opened event: {ev_err}")
                
                if fallback_func:
                    if inspect.iscoroutinefunction(fallback_func):
                        return await fallback_func()
                    return fallback_func()
                raise err

    @classmethod
    async def get_circuits(cls) -> list[dict[str, Any]]:
        """
        Gathers list of all circuit states.
        """
        # We query common service names we protect
        common_services = [
            "openai-api-connector",
            "greenhouse-board-connector",
            "jsearch-api-connector",
            "qdrant-vector-service",
            "google-genai-service"
        ]
        
        circuits = []
        async with RedisService.get_client() as redis:
            for name in common_services:
                state_bytes = await redis.get(f"circuit_breaker:{name}:state")
                state = state_bytes.decode("utf-8") if state_bytes else "CLOSED"
                
                fail_bytes = await redis.get(f"circuit_breaker:{name}:failure_count")
                fail_count = int(fail_bytes) if fail_bytes else 0
                
                time_bytes = await redis.get(f"circuit_breaker:{name}:last_failure_at")
                last_time = time_bytes.decode("utf-8") if time_bytes else None
                
                circuits.append({
                    "service_name": name,
                    "state": state,
                    "failure_count": fail_count,
                    "last_failure_at": last_time
                })
        return circuits

    @classmethod
    async def reset_circuit(cls, service_name: str) -> dict[str, Any]:
        """
        Resets a circuit breaker state to CLOSED.
        """
        async with RedisService.get_client() as redis:
            await redis.set(f"circuit_breaker:{service_name}:state", "CLOSED")
            await redis.delete(f"circuit_breaker:{service_name}:failure_count")
            await redis.delete(f"circuit_breaker:{service_name}:last_failure_at")
        
        return {
            "service_name": service_name,
            "state": "CLOSED",
            "message": "Circuit breaker reset successfully."
        }

    @classmethod
    async def half_open_controller_job(cls) -> None:
        """
        Lightweight job running to test/heal OPEN circuits (F6.3 Background Job).
        """
        circuits = await cls.get_circuits()
        async with RedisService.get_client() as redis:
            for c in circuits:
                if c["state"] == "OPEN":
                    await redis.set(f"circuit_breaker:{c['service_name']}:state", "HALF_OPEN")
                    logger.info(f"Background job transitioned {c['service_name']} to HALF_OPEN.")


def asyncio_is_coroutine(func: Any) -> bool:
    import inspect
    return inspect.iscoroutinefunction(func)
