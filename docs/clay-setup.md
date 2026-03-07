# Clay HTTP Action Setup

## Configuration

- **URL**: `https://clay.nomynoms.com/webhook`
- **Method**: POST
- **Headers**:
  - `Content-Type: application/json`
  - `X-API-Key: your-key`
- **Timeout**: 120000 ms (2 minutes)

## Request Body

```json
{
  "skill": "email-gen",
  "data": {
    "first_name": "/First Name",
    "company_name": "/Company Name",
    "title": "/Title",
    "industry": "/Industry",
    "signal_type": "/Signal Type",
    "signal_detail": "/Signal Detail",
    "linkedin_summary": "/LinkedIn Summary",
    "company_domain": "/Company Domain"
  },
  "model": "opus",
  "instructions": "Optional campaign-specific instructions"
}
```

Map Clay columns using `/Column Name` syntax in the `data` object.

## Async Mode

Add `callback_url` to receive results asynchronously:

```json
{
  "skill": "email-gen",
  "data": { ... },
  "callback_url": "https://your-webhook.com/results",
  "row_id": "optional-row-identifier"
}
```

Returns `202 Accepted` immediately with a `job_id`.

## Skill Chains

Run multiple skills in sequence:

```json
{
  "skills": ["icp-scorer", "email-gen"],
  "data": { ... }
}
```

Output from each step feeds into the next.

## Environment Variables

| Var | Default | Purpose |
|-----|---------|---------|
| `WEBHOOK_API_KEY` | `""` | API key for auth (empty = disabled) |
| `HOST` | `0.0.0.0` | Bind host |
| `PORT` | `8000` | Bind port |
| `MAX_WORKERS` | `10` | Concurrent claude subprocess limit |
| `DEFAULT_MODEL` | `opus` | Default model for skills |
| `REQUEST_TIMEOUT` | `120` | Subprocess timeout (seconds) |
| `CACHE_TTL` | `86400` | Cache TTL (seconds) |
| `MAX_SUBSCRIPTION_MONTHLY_USD` | `200.0` | Usage tracking limit |
