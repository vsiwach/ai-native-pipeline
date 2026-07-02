# Deprecation
Source: https://docs.baseten.co/inference/model-apis/deprecation

Baseten's deprecation policy for Model APIs

Open-source models advance rapidly. Baseten prioritizes serving the highest-quality models and deprecates specific Model APIs when stronger alternatives become available. When a model is selected for deprecation, Baseten follows this process:

1. **Announcement**
   * Deprecations are announced approximately two weeks before the deprecation date.
   * Documentation is updated to identify the model being deprecated and recommend a replacement.
   * Affected users are contacted by email.
2. **Transition**
   * The deprecated model remains fully functional until the deprecation date. You have approximately two weeks to transition using one of these options:
     1. Migrate to a dedicated deployment with the deprecated model weights. [Contact us](https://www.baseten.co/talk-to-us/deprecation-inquiry/) for assistance.
     2. Update your code to use an active model (a recommendation is provided in the deprecation announcement).
3. **Deprecation date**
   * The model ID for the deprecated model becomes inactive and returns an error for all requests.
   * A changelog notification is published with the recommended replacement.

## Planned deprecations

There are no planned deprecations at this time.

## Next steps

<CardGroup>
  <Card title="Supported models" icon="layer-group" href="/inference/model-apis/overview#supported-models">
    See the models currently available through Model APIs
  </Card>

  <Card title="Dedicated deployments" icon="server" href="/development/model/overview">
    Deploy a model with Truss to keep using specific weights
  </Card>
</CardGroup>
