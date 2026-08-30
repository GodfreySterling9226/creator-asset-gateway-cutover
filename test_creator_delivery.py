from creator_delivery import DeliveryRequest, deliver_asset


class FixedProcessor:
    def write_buyer_message(self, request: DeliveryRequest) -> str:
        return f"{request.asset_name} is ready for {request.buyer_name}."


def make_request(release_state: str) -> DeliveryRequest:
    return DeliveryRequest(
        delivery_id="order_1042_asset_1",
        asset_name="Storefront Lighting Presets",
        download_url="https://downloads.example.com/orders/1042/presets.zip",
        buyer_name="Mina",
        release_state=release_state,
        notify_subscribers=True,
    )


def test_published_asset_queues_subscriber_update() -> None:
    result = deliver_asset(make_request("published"), FixedProcessor())

    assert result.subscriber_update == "queued"
    assert result.buyer_message == "Storefront Lighting Presets is ready for Mina."


def test_draft_asset_skips_subscriber_update() -> None:
    result = deliver_asset(make_request("draft"), FixedProcessor())

    assert result.subscriber_update == "skipped"
