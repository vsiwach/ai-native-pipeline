# Register an API key
Source: https://docs.baseten.co/reference/gateway/api-keys/register-an-api-key

POST https://api.baseten.co/v1/gateway/groups/{group_id}/api_keys/register
Attach a caller-supplied API key to a Frontier Gateway group so downstream consumers can continue using a key they already issued.

Register a caller-supplied API key against an existing group. This exists for white-label deployments where you already mint keys for your end users and want Baseten inference under the hood without forcing them to rotate.

The registered key inherits the group's full live model set and effective limits, exactly like a key produced by [Create an API key](/reference/gateway/api-keys/create-an-api-key). Baseten stores only the hashed key; once registered, the plaintext value is unrecoverable from our side.

### Request signing

This endpoint accepts a key you generated, so Baseten verifies that each request came from you. Sign the request body with an Ed25519 private key; Baseten checks the signature against a public key held for your workspace. Requests without a valid signature return `400 Bad Request`.

Before your first call, generate an Ed25519 keypair and register the public key with Baseten:

```bash theme={"system"}
openssl genpkey -algorithm Ed25519 -out priv.pem
openssl pkey -in priv.pem -pubout -outform DER | tail -c 32 | base64
```

The second command prints the 32-byte public key as base64. Send it to Baseten to store for your workspace; until a key is on file, every call returns `400 Bad Request`. Keep `priv.pem` secret.

Sign the **exact bytes of the JSON body you send**, base64-encode the signature, and pass it in the `X-Baseten-Signature` header. Re-serializing the body before signing (different key order or whitespace) breaks verification, so sign the precise string you send.

### Key requirements

The `key` value you submit must satisfy these constraints. The endpoint returns `400 Bad Request` if any check fails:

| Constraint | Rule                                                                                                           |
| ---------- | -------------------------------------------------------------------------------------------------------------- |
| Length     | Between 32 and 128 characters, inclusive.                                                                      |
| Complexity | Shannon entropy of at least 3.0 bits per character. Any securely-generated random key satisfies this.          |
| Uniqueness | The first 16 characters become the key's stored `prefix` and must not already be registered in your workspace. |

Generate keys with a cryptographically secure random source on your side and bring them to this endpoint. Baseten does not return a generated key from this call.

### Authentication

<ParamField type="string">
  Workspace API key with management scope, passed as `Authorization: Api-Key $BASETEN_API_KEY` (or `Bearer`; both are accepted).
</ParamField>

<ParamField type="string">
  Base64-encoded Ed25519 signature of the raw request body, produced with your workspace's private key. See [Request signing](#request-signing). A missing or invalid signature returns `400 Bad Request`.
</ParamField>

### Path parameters

<ParamField type="string">
  Internal Baseten ID of the group to register the key under. Returned as `id` from [Create a group](/reference/gateway/groups/create-a-group).
</ParamField>

### Body

<ParamField type="string">
  The plaintext API key to register. Must satisfy the [key requirements](#key-requirements). Hand this value to the downstream consumer through your own secure channel. Baseten does not echo it back.
</ParamField>

<ParamField type="string">
  Display name for the key. Useful for distinguishing multiple keys under the same group.
</ParamField>

### Response

<ResponseField name="ok" type="boolean">
  `true` when the registration succeeded. The endpoint does not return the key, so store it on your side before calling.
</ResponseField>

### Errors

| Status            | Meaning                                                                                                                                                   |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `400 Bad Request` | The supplied `key` failed length, complexity, or uniqueness validation.                                                                                   |
| `400 Bad Request` | `Signature verification failed`: the `X-Baseten-Signature` header was missing, wasn't valid base64, or didn't verify against your workspace's public key. |
| `400 Bad Request` | `Must configure a public key before registering API keys`: no Ed25519 public key is on file for your workspace. See [Request signing](#request-signing).  |
| `403 Forbidden`   | The group exists but isn't in your workspace, or the caller doesn't have management scope.                                                                |
| `404 Not Found`   | No group with this `id` in your workspace, or it has been deleted.                                                                                        |

<RequestExample>
  ```bash curl theme={"system"}
  BODY='{"name":"acme-prod-key-1","key":"<your-securely-generated-api-key>"}'
  SIGNATURE=$(printf '%s' "$BODY" | openssl pkeyutl -sign -inkey priv.pem -rawin | openssl base64 -A)

  curl --request POST \
    --url https://api.baseten.co/v1/gateway/groups/abc123hash/api_keys/register \
    --header "Authorization: Api-Key $BASETEN_API_KEY" \
    --header "Content-Type: application/json" \
    --header "X-Baseten-Signature: $SIGNATURE" \
    --data "$BODY"
  ```
</RequestExample>

<ResponseExample>
  ```json 200 theme={"system"}
  {
    "ok": true
  }
  ```
</ResponseExample>
