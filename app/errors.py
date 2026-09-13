"""Human-readable browser errors while keeping API errors as JSON."""
import logging
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException
from app.routers.pages import render_template


def error_page(request, status, message):
    title = {404: "Page not found", 409: "Change not allowed", 422: "Invalid request", 500: "Something went wrong"}.get(status, "Request could not be completed")
    return HTMLResponse(render_template("error.html", dict(status_code=status, title=title, message=message), request=request), status_code=status)


def register_error_handlers(app):
    @app.exception_handler(HTTPException)
    async def http_error(request, error):
        if request.url.path.startswith("/api/"):
            return await http_exception_handler(request, error)
        return error_page(request, error.status_code, str(error.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        if request.url.path.startswith("/api/"):
            return await request_validation_exception_handler(request, error)
        message = "; ".join(f"{'.'.join(str(part) for part in item['loc'][1:])}: {item['msg']}" for item in error.errors())
        return error_page(request, 422, message)

    @app.exception_handler(Exception)
    async def unexpected_error(request, error):
        logging.getLogger(__name__).error("Unexpected request failure", exc_info=error)
        message = "The request could not be completed. Check the server log for details."
        if request.url.path.startswith("/api/"):
            return JSONResponse({"detail": message}, status_code=500)
        return error_page(request, 500, message)
