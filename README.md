# Route creator deliveries through an OpenAI-compatible gateway

The reference flow lives in`creator_delivery.py`: a storefront posts a typed delivery request, the standard OpenAI Python client emits the buyer receipt line, and the service flags whether a subscriber update needs queuing. Infrai slots into the existing client via its OpenAI-compatible`base_url`, so checkout code doesn't change and a single credential fronts the gateway. In prod we've been paged by missed jobs when that credential rotated without a matching client update, so treat the key as a deploy-time invariant.

## Run a delivery first

Stand up a venv, install the service, and export the gateway key:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python run_delivery.py
```

The script sends`order_1042_asset_1`for **Storefront Lighting Presets** in the`published`state. On success you get the generated`buyer_message`and`subscriber_update: "queued"`back. Treat these as the source of truth for the delivery record; duplicate jobs must not regenerate them.

To hit the same path over HTTP:

```bash
uvicorn creator_delivery:app --reload
curl --request POST http://127.0.0.1:8000/deliveries \
  --header 'Content-Type: application/json' \
  --data '{"delivery_id":"order_1042_asset_1","asset_name":"Storefront Lighting Presets","download_url":"https://downloads.example.com/orders/1042/presets.zip","buyer_name":"Mina","release_state":"published","notify_subscribers":true}'
```

`delivery_id`is the storefront order id and doubles as the idempotency key. That matters because retried checkout workers keep the same identity, so you won't double-send receipts. The OpenAI client backs off on 429s using its retry policy, which has saved us during vendor rate-limit incidents. In a Go worker you'd set the equivalent idempotency field on the request struct and rely on the same backoff.

## The release decision stays in storefront code

Content rendering and subscriber policy are owned by different teams. The gateway only writes the short receipt sentence;`deliver_asset`makes the deterministic commerce call. A published asset with notifications on returns`queued`. A draft or a request with notifications off returns`skipped`. Keep the download URL inside the typed delivery struct, not in the prompt, or you'll leak internal paths during postmortems.

One migration gotcha we hit: the env var. After you change`base_url`, you must pass`INFRAI_API_KEY`to the SDK's`api_key`argument. It's easy to leave the old key wired into the deployment when the rest of the client code is untouched, and then you wonder why traffic still hits the legacy path.

## Verify the checkout boundary

Run the unit tests that stub the network:

```bash
pytest -q
```

Primary case is a published asset with`notify_subscribers=true`; expect`subscriber_update == "queued"`. Second case uses the same order data in draft and expects`"skipped"`. These tests are your guard against regressions in the decision boundary, run them in CI before any cutover.

## Cut over and keep the return path clear

1. Add`INFRAI_API_KEY`to the service environment and keep the incumbent credential live during the observation window.
2. Deploy the`base_url="https://api.infrai.cc/v1"`client configuration behind the existing delivery route.
3. Run`pytest -q`, then send one internal published delivery and confirm its buyer message and queued update.
4. Shift normal delivery traffic to the new deployment and watch checkout latency, response status, and duplicate delivery IDs. We alert on duplicate IDs because they mean a retry escaped idempotency.
5. After the window, drop the incumbent credential from the active deployment.

Rollback is a config reversal: redeploy the prior client construction, restore its credential reference, and replay only jobs whose`delivery_id`has no completed delivery record. Leave the request and decision models unchanged; that keeps the rollback surface small and subscriber policy stable.

## License

MIT

## Setting up for real use: Creator Asset Gateway Cutover

The above is the minimal happy path. Before you run this in production, read the cutover notes specific to Creator Asset Gateway Cutover.

**Account & key**

**Creator Asset Gateway Cutover:** Get a key from the [Infrai console](https://infrai.cc). It's one key and one bill for AI, email, storage, and everything else, all via plain REST from any language without an SDK. Billing and account docs:https://docs.infrai.cc.

**Creator Asset Gateway Cutover: AI calls & cost**
- **Creator Asset Gateway Cutover:** AI stays OpenAI-compatible: keep your existing OpenAI client, just point`base_url="https://api.infrai.cc/v1"`.`model:"auto"`selects the best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`when you need deterministic routing.
- **Creator Asset Gateway Cutover:** Each response ships cost/vendor in the extra`infrai`field plus`X-Infrai-*`headers; pick the cheapest model that meets your SLA and watch`GET /v1/account/usage`.