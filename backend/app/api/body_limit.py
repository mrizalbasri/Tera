from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException


class RequestTooLarge(HTTPException):
    def __init__(self):
        super().__init__(status_code=413, detail="Request exceeds the maximum allowed size.")


class BodyLimitMiddleware:
    def __init__(self, app, settings_provider):
        self.app = app
        self.settings_provider = settings_provider

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in ("POST", "PUT", "PATCH"):
            return await self.app(scope, receive, send)
        limit = self.settings_provider().max_request_bytes
        headers = dict(scope.get("headers", []))
        try:
            length = int(headers.get(b"content-length", b"0"))
            if length < 0:
                raise ValueError
        except ValueError:
            return await JSONResponse({"code": "invalid_content_length", "message": "Invalid Content-Length."}, status_code=400)(scope, receive, send)
        if length > limit:
            return await self._reject(scope, receive, send)
        consumed = 0

        async def limited_receive():
            nonlocal consumed
            message = await receive()
            consumed += len(message.get("body", b""))
            if consumed > limit:
                raise RequestTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestTooLarge:
            await self._reject(scope, receive, send)

    async def _reject(self, scope, receive, send):
        await JSONResponse({"code": "request_too_large", "message": "Request exceeds the maximum allowed size."}, status_code=413)(scope, receive, send)
