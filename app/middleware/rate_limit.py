"""
Middleware simple de rate limiting por IP
Respaldo al rate limiting de nginx
"""
from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from collections import defaultdict
import time
import logging

logger = logging.getLogger(__name__)

# Configuración: máximo 10 requests por minuto por IP
MAX_REQUESTS_PER_MINUTE = 10
CLEANUP_INTERVAL = 300  # Limpiar datos cada 5 minutos


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware simple para limitar requests por IP"""
    
    def __init__(self, app, max_requests: int = MAX_REQUESTS_PER_MINUTE):
        super().__init__(app)
        self.max_requests = max_requests
        self.request_times: dict[str, list[float]] = defaultdict(list)
        self.last_cleanup = time.time()
    
    def _get_client_ip(self, request: Request) -> str:
        """Obtiene la IP real del cliente"""
        # Verificar headers de proxy primero
        if "x-forwarded-for" in request.headers:
            forwarded = request.headers["x-forwarded-for"].split(",")[0].strip()
            if forwarded:
                return forwarded
        
        # IP directa
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _cleanup_old_requests(self):
        """Limpia requests antiguos para liberar memoria"""
        now = time.time()
        if now - self.last_cleanup < CLEANUP_INTERVAL:
            return
        
        cutoff = now - 60  # Mantener solo últimos 60 segundos
        for ip in list(self.request_times.keys()):
            self.request_times[ip] = [
                t for t in self.request_times[ip] if t > cutoff
            ]
            if not self.request_times[ip]:
                del self.request_times[ip]
        
        self.last_cleanup = now
    
    async def dispatch(self, request: Request, call_next):
        # Health check no tiene límite
        if request.url.path == "/health":
            return await call_next(request)

        # Preflight no cuenta para rate limit
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Limpiar datos antiguos periódicamente
        self._cleanup_old_requests()
        
        # Obtener IP del cliente
        client_ip = self._get_client_ip(request)
        
        # Verificar límite
        now = time.time()
        cutoff = now - 60  # Último minuto
        
        # Filtrar requests del último minuto
        recent_requests = [
            t for t in self.request_times[client_ip] 
            if t > cutoff
        ]
        
        # Si excede el límite, rechazar
        if len(recent_requests) >= self.max_requests:
            logger.warning(
                f"Rate limit exceeded for IP {client_ip}: "
                f"{len(recent_requests)} requests in last minute"
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": "60"},
            )
        
        # Registrar request
        self.request_times[client_ip].append(now)
        
        # Continuar con la request
        return await call_next(request)

