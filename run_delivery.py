"""Run one published digital-asset delivery from the command line."""

from creator_delivery import DeliveryRequest, GatewayContentProcessor, deliver_asset


def main() -> None:
    request = DeliveryRequest(
        delivery_id="order_1042_asset_1",
        asset_name="Storefront Lighting Presets",
        download_url="https://downloads.example.com/orders/1042/presets.zip",
        buyer_name="Mina",
        release_state="published",
        notify_subscribers=True,
    )
    result = deliver_asset(request, GatewayContentProcessor())
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
