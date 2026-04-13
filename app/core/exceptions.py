"""
Custom exceptions and FastAPI exception handlers.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AstroBaseException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class LocationResolutionError(AstroBaseException):
    def __init__(self, location: str):
        super().__init__(f"Could not resolve location: '{location}'", status_code=404)


class EphemerisError(AstroBaseException):
    def __init__(self, detail: str = "Ephemeris computation failed"):
        super().__init__(detail, status_code=500)


class WeatherServiceError(AstroBaseException):
    def __init__(self, detail: str = "Weather service unavailable"):
        super().__init__(detail, status_code=503)


class NarrationError(AstroBaseException):
    def __init__(self, detail: str = "AI narration service unavailable"):
        super().__init__(detail, status_code=503)


class RateLimitExceededError(AstroBaseException):
    def __init__(self):
        super().__init__("Rate limit exceeded. Please slow down.", status_code=429)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AstroBaseException)
    async def astro_exception_handler(request: Request, exc: AstroBaseException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message, "type": type(exc).__name__},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"error": "An unexpected error occurred.", "type": "InternalServerError"},
        )
