# Watch
Source: https://docs.baseten.co/development/chain/watch

Live-patch deployed code

The [watch command](/reference/cli/chains/chains-cli#watch) (`truss chains watch`) combines
the best of local development and full deployment. `watch` lets you run on an
exact copy of the production hardware and interface but gives you live code
patching that lets you test changes in seconds without creating a new
deployment.

To use `truss chains watch`:

1. Push a chain in development mode with `truss chains push --watch SOURCE`.
   This creates a development deployment and starts watching in one step.
   You can also create the deployment separately and then run
   `truss chains watch SOURCE` to attach the watcher.
2. Each time you edit a file and save the changes, the watcher patches the
   remote deployments. Updating the deployments might take a moment, but is
   generally *much* faster than creating a new deployment.
3. You can call the chain with test data using `cURL` or the playground dialogue
   in the UI and observe the result and logs.
4. Iterate steps 2. and 3. until your chain behaves in the desired way.

By default, `watch` keeps your development Chainlets warm so they don't scale to
zero while you iterate. On startup, the watcher wakes any scaled-to-zero
Chainlets, waits for them to be ready before applying the first patch, then keeps
them warm for the rest of the session. This avoids the readiness wait and the
occasional patch failures that happen when a Chainlet falls asleep between edits.

The `--no-sleep` flag controls this keepalive and is on by default. To let idle
Chainlets scale to zero during a long watch session, opt out with
`truss chains watch my_chain.py --no-sleep=false`. When you watch through `push`,
pass `--watch-no-sleep=false` instead:
`truss chains push my_chain.py --watch --watch-no-sleep=false`.

## Selective watch

Some large ML models might have a slow cycle time to reload (for example, if the
weights are huge). For this case, we provide a "selective" watch option. For
example, if your chain has such a heavy model Chainlet and other Chainlets
that contain only business logic, you can iterate on those, while not patching
and reloading the heavy model Chainlet.

<Warning>
  This feature is useful for advanced use cases, but must be used with
  caution. If you change the code of a Chainlet not watched, in particular I/O types,
  you get an inconsistent deployment.
</Warning>

Add the Chainlet names you want to watch as a comma-separated list:

```bash Terminal theme={"system"}
truss chains watch ... --experimental-chainlet-names=ChainletA,ChainletB
```
