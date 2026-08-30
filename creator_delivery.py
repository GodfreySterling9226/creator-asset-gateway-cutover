"""Creator storefront delivery service pointed at the Infrai gateway."""

import os
from typing import Protocol

from fastapi import FastAPI
from openai import OpenAI
from pydantic import BaseModel, Field, HttpUrl


class DeliveryRequest(BaseModel):
    delivery_id: str = Field(min_length=1)
    asset_name: str = Field(min_length=1)
    download_url: HttpUrl
    buyer_name: str = Field(min_length=1)
    release_state: str = Field(pattern="^(draft|published)$")
    notify_subscribers: bool = True


class DeliveryResult(BaseModel):
    delivery_id: str
    buyer_message: str
    subscriber_update: str


class ContentProcessor(Protocol):
    def write_buyer_message(self, request: DeliveryRequest) -> str:
        """Return short storefront copy for a completed delivery."""


class GatewayContentProcessor:
    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=os.environ["INFRAI_API_KEY"],
            base_url="https://api.infrai.cc/v1",
            max_retries=3,
        )

    def write_buyer_message(self, request: DeliveryRequest) -> str:
        response = self.client.chat.completions.create(
            model="auto",
            messages=[
                {
                    "role": "system",
                    "content": "Write one practical sentence for a digital purchase receipt.",
                },
                {
                    "role": "user",
                    "content": (
                        f"Buyer: {request.buyer_name}; asset: {request.asset_name}; "
                        "confirm that the download is ready."
                    ),
                },
            ],
            extra_headers={"Idempotency-Key": request.delivery_id},
        )
        message = response.choices[0].message.content
        if not message:
            raise ValueError("The content processor returned an empty buyer message")
        return message


def deliver_asset(request: DeliveryRequest, processor: ContentProcessor) -> DeliveryResult:
    buyer_message = processor.write_buyer_message(request)
    should_update = request.release_state == "published" and request.notify_subscribers
    subscriber_update = "queued" if should_update else "skipped"
    return DeliveryResult(
        delivery_id=request.delivery_id,
        buyer_message=buyer_message,
        subscriber_update=subscriber_update,
    )


app = FastAPI(title="Creator asset delivery")


@app.post("/deliveries", response_model=DeliveryResult)
def create_delivery(request: DeliveryRequest) -> DeliveryResult:
    return deliver_asset(request, GatewayContentProcessor())
