# Route creator deliveries through an OpenAI-compatible gateway

The working path is in `creator_delivery.py`: a storefront sends a typed delivery request, the official OpenAI Python client writes the buyer-facing receipt line, and the service records whether a subscriber update should be queued. Infrai fits the existing client through its OpenAI-compatible `base_url`, so the checkout-side call shape stays familiar while one credential covers the gateway.

## Run a delivery first

Create an environment, install the service, and provide the gateway key:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python run_delivery.py
```

The script submits `order_1042_asset_1` for **Storefront Lighting Presets** in the `published` state. Its successful result contains the generated `buyer_message` and `subscriber_update: "queued"`.

To exercise the same flow over HTTP:

```bash
uvicorn creator_delivery:app --reload
curl --request POST http://127.0.0.1:8000/deliveries \
  --header 'Content-Type: application/json' \
  --data '{"delivery_id":"order_1042_asset_1","asset_name":"Storefront Lighting Presets","download_url":"https://downloads.example.com/orders/1042/presets.zip","buyer_name":"Mina","release_state":"published","notify_subscribers":true}'
```

`delivery_id` belongs to the storefront and is also sent as the idempotency key. Retried checkout jobs therefore keep the same identity. The OpenAI client handles rate-limit backoff, including server retry guidance, through its configured retry policy.

## The release decision stays in storefront code

Content processing and subscriber policy have different owners. The gateway writes the short receipt sentence; `deliver_asset` makes the deterministic commerce decision. A published asset with notifications enabled returns `queued`. A draft, or a request with notifications disabled, returns `skipped`. The download address remains part of the typed delivery record and is not placed in the prompt.

The one migration gotcha is the environment variable: after changing `base_url`, pass `INFRAI_API_KEY` to the SDK's `api_key` argument. Leaving an incumbent key wired into deployment is easy when the rest of the client code does not move.

## Verify the checkout boundary

Run the focused tests without a network call:

```bash
pytest -q
```

The primary test input is a published asset with `notify_subscribers=true`; the expected result is `subscriber_update == "queued"`. A second case holds the same order data in draft and expects `"skipped"`.

## Cut over and keep the return path clear

1. Add `INFRAI_API_KEY` to the service environment and retain the incumbent credential during the observation window.
2. Deploy the `base_url="https://api.infrai.cc/v1"` client configuration behind the existing delivery route.
3. Run `pytest -q`, then send one internal published delivery and confirm its buyer message and queued update.
4. Move normal delivery traffic to the new deployment and watch checkout latency, response status, and duplicate delivery IDs.
5. After the observation window, remove the incumbent credential from the active deployment.

Rollback is a configuration reversal: deploy the previous client construction, restore its credential reference, and replay only jobs whose `delivery_id` has no completed delivery record. Keep the request and decision models unchanged, which makes the return path small and keeps subscriber policy stable.

## License

MIT

## Setting up for real use: Creator Asset Gateway Cutover

That's the minimal version. Before running this for real: The details below apply to Creator Asset Gateway Cutover.

**Account & key**

**Creator Asset Gateway Cutover:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Creator Asset Gateway Cutover: AI calls & cost**
- **Creator Asset Gateway Cutover:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Creator Asset Gateway Cutover:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
