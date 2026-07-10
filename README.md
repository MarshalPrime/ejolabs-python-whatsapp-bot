# Kabisa WhatsApp Assistant

This service powers a WhatsApp assistant for Kabisa Rwanda. It receives messages from the Meta WhatsApp Cloud API, retrieves Kabisa knowledge from Qdrant, asks the configured LLM provider to generate a grounded answer, and sends the reply back through WhatsApp.


`I don't have that information yet. Please call Kabisa at 6420.`

## Runtime Flow

1. Meta sends a WhatsApp webhook request to `/webhook`.
2. Flask verifies the Meta signature.
3. The webhook returns `200 OK` quickly.
4. A background worker searches Qdrant for Kabisa Rwanda context.
5. If retrieval is relevant, the configured model provider receives the user question plus Kabisa context.
6. The bot sends a text answer and, when relevant, a vehicle image.

## Local Setup

Create `.env` from `example.env`, then set the Meta, model provider, and Qdrant values.

Select the model provider:

```env
LLM_PROVIDER="ejochat"
KABISA_RESPONSE_LANGUAGE="auto"
```

`KABISA_RESPONSE_LANGUAGE=auto` tells the model to answer in the user's language, falling back to Kinyarwanda when the language is unclear. Use `kinyarwanda`, `english`, or `french` to force one language.

Install dependencies:

```bash
pip install -r requirements.txt
```

Start Qdrant:

```bash
docker compose up -d qdrant
```

Ingest Kabisa Rwanda content:

```bash
python scripts/ingest_kabisa.py
```

Run Flask:

```bash
python run.py
```

Expose the webhook with ngrok on the same port:

```bash
ngrok http --url=overpay-drab-series.ngrok-free.dev 8000
```

Access Qdrant:
- url: http://localhost:6333/dashboard
- Go to Collections -> kabisa_rw

Meta callback URL:

```text
https://your-domain.ngrok-free.dev/webhook
```

If ngrok reports `ERR_NGROK_8012` or `localhost:80`, restart ngrok with port `8000`.

## Important Checks

- Qdrant must be running before the assistant can answer from Kabisa knowledge.
- Run ingestion again after Kabisa website or vehicle data changes.
- Restart Flask after code or environment changes.
- Rotate any Meta or EjoChat credentials that were printed in terminals, screenshots, logs, or shared chat.
