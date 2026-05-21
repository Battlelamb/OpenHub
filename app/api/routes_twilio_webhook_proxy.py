"""Public Twilio webhook bridge for Hermes SMS.

Cloudflare currently routes hub.brunhilde.cloud to OpenHub. This narrow public
endpoint forwards Twilio webhook POSTs to the local Hermes gateway SMS listener
without logging secrets or message bodies.
"""

from __future__ import annotations

import os

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["webhooks"])

_HERMES_SMS_TARGET = os.environ.get(
    "HERMES_SMS_WEBHOOK_PROXY_TARGET",
    "http://127.0.0.1:8080/webhooks/twilio",
)

# Forward only headers Hermes/Twilio signature validation can need. Avoid hop-by-hop
# headers and never log body/header values here.
_FORWARD_HEADERS = {
    "content-type",
    "x-twilio-signature",
    "x-forwarded-for",
    "x-forwarded-proto",
    "user-agent",
}


@router.get("/webhooks/twilio", include_in_schema=False)
async def twilio_webhook_probe() -> PlainTextResponse:
    """Readiness probe for the public Cloudflare route.

    Twilio will use POST. GET intentionally returns 405-equivalent text for
    humans/probes while proving that the public path reaches this process.
    """

    return PlainTextResponse("Twilio webhook expects POST", status_code=405)


@router.post("/webhooks/twilio", include_in_schema=False)
async def twilio_webhook_proxy(request: Request) -> Response:
    """Forward Twilio webhook payloads to Hermes SMS gateway."""

    body = await request.body()
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() in _FORWARD_HEADERS
    }

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        upstream = await client.post(_HERMES_SMS_TARGET, content=body, headers=headers)

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "text/xml"),
    )
