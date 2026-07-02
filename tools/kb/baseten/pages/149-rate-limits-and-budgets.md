# Rate limits and budgets
Source: https://docs.baseten.co/inference/model-apis/rate-limits-and-budgets

Rate limits and usage budgets for Model APIs

Baseten enforces two rate limits to ensure fair use and system stability:

* **Request rate limits**: Maximum API requests per minute.
* **Token rate limits**: Maximum tokens processed per minute (input + output combined).

Default limits vary by account status.

| Account                |                                         RPM |                                         TPM |
| :--------------------- | ------------------------------------------: | ------------------------------------------: |
| **Basic** (unverified) |                                          15 |                                     100,000 |
| **Basic** (verified)   |                                         120 |                                     500,000 |
| **Pro**                |                                         120 |                                   1,000,000 |
| **Enterprise**         | [Custom](https://www.baseten.co/talk-to-us) | [Custom](https://www.baseten.co/talk-to-us) |

If your workspace is on the Basic (unverified) tier and you need the higher Basic (verified) limits, [contact us](https://www.baseten.co/talk-to-us/increase-rate-limits/) to request verification. To move to the Pro or Enterprise tier, contact us through the same form.

<Warning>
  If you exceed these limits, the API returns a `429 Too Many Requests` error. See [Inference errors](/inference/errors#429-too-many-requests) for how to respond.
  To request a rate limit increase, [contact us](https://www.baseten.co/talk-to-us/increase-rate-limits/).
</Warning>

## Set budgets

Budgets let you control Model API usage and avoid unexpected costs. Budgets apply only to Model APIs, not dedicated deployments. Your team receives email notifications at 75%, 90%, and 100% of budget.

### Enforce budgets

Budgets can be enforced or non-enforced:

* **Enforced**: Requests are rejected when the budget is reached.
* **Not enforced**: You receive notifications but remain responsible for costs over the budget.

## Next steps

<CardGroup>
  <Card title="Inference errors" icon="triangle-exclamation" href="/inference/errors#429-too-many-requests">
    Handle `429 Too Many Requests` and other status codes
  </Card>

  <Card title="Model APIs overview" icon="layer-group" href="/inference/model-apis/overview">
    Supported models, pricing, and feature support
  </Card>
</CardGroup>
