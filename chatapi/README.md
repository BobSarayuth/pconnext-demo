# cap-agentic-chat-api

## Public chat authentication

The chat API accepts the existing `X-API-Key` header for internal service calls and also accepts JWT bearer tokens for
public chat clients after AD/Entra login.

Frontend calls to `/api/chat/*` should include:

```http
Authorization: Bearer <access_token>
```

Configure JWT validation with:

```env
# If the UI sends id_token, use the UI/client app id as audience.
AGENTIC_JWT_AUDIENCE=<same-value-as-AUTH_CLIENT_ID>
AGENTIC_JWT_ISSUER=https://login.microsoftonline.com/<tenant-id>/v2.0
AGENTIC_JWT_JWKS_URL=https://login.microsoftonline.com/<tenant-id>/discovery/v2.0/keys
AGENTIC_JWT_ALGORITHMS=RS256
```
