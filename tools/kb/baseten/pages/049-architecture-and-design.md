# Architecture and design
Source: https://docs.baseten.co/development/chain/design

How to structure your Chainlets

A Chain is composed of multiple connected Chainlets working together to perform
a task.

For example, the Chain in the following diagram takes a large audio file as input.
Then it splits it into smaller chunks, transcribes each chunk in parallel
(reducing the end-to-end latency), and finally aggregates and returns the
results.

<Frame>
  <img />
</Frame>

To build an efficient Chain, we recommend drafting your high level
structure as a flowchart or diagram. This can help you identify
parallelizable units of work and steps that need different (model/hardware)
resources.

If one Chainlet creates many "sub-tasks" by calling other dependency
Chainlets (for example, in a loop over partial work items),
these calls should be done as `asyncio`-tasks that run concurrently.
That way you get the most out of the parallelism that Chains offers. This
design pattern is extensively used in the
[audio transcription example](/examples/chains-audio-transcription).

<Warning>
  While using `asyncio` is essential for performance, it can also be tricky.
  Here are a few caveats to look out for:

  * Executing operations in an async function that block the event loop for
    more than a fraction of a second. This hinders the "flow" of processing
    requests concurrently and starting RPCs to other Chainlets. Ideally use
    native async APIs. Frameworks like vLLM or triton server offer such APIs,
    similarly file downloads can be made async and you might find
    [`AsyncBatcher`](https://github.com/hussein-awala/async-batcher) useful.
    If there is no async support, consider running blocking code in a
    thread/process pool (as an attribute of a Chainlet).
  * Creating async tasks (for example, with `asyncio.create_task`) does not start
    the task *immediately*. In particular, when starting several tasks in a loop,
    `create_task` must be alternated with operations that yield to the event
    loop that, so the task can be started. If the loop is not `async for` or
    contains other `await` statements, a "dummy" await can be added, for example
    `await asyncio.sleep(0)`. This allows the tasks to be started concurrently.
</Warning>
