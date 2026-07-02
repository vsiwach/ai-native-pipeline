# truss.load
Source: https://docs.baseten.co/reference/sdk/truss/load



Returns a handle to a local Truss: a build context that can be built into a container locally or deployed to Baseten.

**Parameters:**

| Name              | Type                        | Description                                                                                      |
| ----------------- | --------------------------- | ------------------------------------------------------------------------------------------------ |
| `truss_directory` | *Union\[str, pathlib.Path]* | The local directory of an existing Truss                                                         |
| `config_path`     | *Optional\[pathlib.Path]*   | Optional path to a config file. If not provided, defaults to config.yaml in the truss directory. |
