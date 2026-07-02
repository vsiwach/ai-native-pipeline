# baseten truss
Source: https://docs.baseten.co/reference/cli/baseten/truss

Run truss commands

Delegates to the truss CLI if found on PATH, otherwise shows install instructions.

## truss

```sh theme={"system"}
baseten truss [OPTIONS] [args...]
```

### Options

*(no options)*

### Examples

Show truss help by passing `--help` to truss

```sh theme={"system"}
baseten truss --help
```

### Output

**Text mode (`--output text`):** Whatever the truss CLI writes to stdout/stderr, passed through verbatim. `--output` and `--jq` are not honored: all arguments after `truss` are forwarded to the underlying truss binary. The exit code is propagated from truss.

**JSON mode (`--output json`):** payload type `cmd.JSONUndefined`.
