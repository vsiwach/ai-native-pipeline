# Binary I/O
Source: https://docs.baseten.co/development/chain/binaryio

Performant serialization of numeric data

Numeric data or audio/video are most efficiently transmitted as bytes.

Other representations such as JSON or base64 encoding lose precision, add
significant parsing overhead and increase message sizes (for example, \~33% increase
for base64 encoding).

Chains extends the JSON-centred pydantic ecosystem with two ways how you can
include binary data: numpy array support and raw bytes.

## Numpy `ndarray` support

<Tip>
  Once you have your data represented as a numpy array, you can (and
  often without copying) convert it to `torch`, `tensorflow`, or other common
  numeric libraries' objects.
</Tip>

To include numpy arrays in a pydantic model, chains has a special field type
implementation `NumpyArrayField`. For example:

```python data_model.py theme={"system"}
import numpy as np
import pydantic

from truss_chains import pydantic_numpy


class DataModel(pydantic.BaseModel):
    some_numbers: pydantic_numpy.NumpyArrayField
    other_field: str
    ...


numbers = np.random.random((3, 2))
data = DataModel(some_numbers=numbers, other_field="Example")
print(data)
# some_numbers=NumpyArrayField(shape=(3, 2), dtype=float64, data=[
#   [0.39595027 0.23837526]
#   [0.56714894 0.61244946]
#   [0.45821942 0.42464844]])
# other_field='Example'
```

`NumpyArrayField` is a wrapper around the actual numpy array. Inside your
python code, you can work with its `array` attribute:

```python theme={"system"}
data.some_numbers.array += 10
# some_numbers=NumpyArrayField(shape=(3, 2), dtype=float64, data=[
#   [10.39595027 10.23837526]
#   [10.56714894 10.61244946]
#   [10.45821942 10.42464844]])
# other_field='Example'
```

The interesting part is how it serializes when communicating between Chainlets
or with a client.
It can work in two modes: JSON and binary.

### Binary

As a JSON alternative that supports byte data, Chains uses `msgpack` (with
`msgpack_numpy`) to serialize the dict representation.

For Chainlet-Chainlet RPCs this is done automatically for you by enabling binary
mode of the dependency Chainlets, see
[all options](/reference/sdk/chains#function-truss_chains-depends):

```python binary_rpc.py theme={"system"}
import truss_chains as chains


class Worker(chains.ChainletBase):
    async def run_remote(self, data: DataModel) -> DataModel:
        data.some_numbers.array += 10
        return data


class Consumer(chains.ChainletBase):

    def __init__(self, worker=chains.depends(Worker, use_binary=True)):
        self._worker = worker

    async def run_remote(self):
        numbers = np.random.random((3, 2))
        data = DataModel(some_numbers=numbers, other_field="Example")
        result = await self._worker.run_remote(data)
```

Now the data is transmitted in a fast and compact way between Chainlets
which often gives performance increases.

### Binary client

If you want to send such data as input to a chain or parse binary output
from a chain, you have to add the `msgpack` serialization client-side:

```python binary_client.py theme={"system"}
import requests
import msgpack
import msgpack_numpy

msgpack_numpy.patch()  # Register hook for numpy.

# Dump to "python" dict and then to binary.
data_dict = data.model_dump(mode="python")
data_bytes = msgpack.dumps(data_dict)

# Set binary content type in request header.
headers = {
    "Content-Type": "application/octet-stream", "Authorization": ...
}

response = requests.post(url, data=data_bytes, headers=headers)
response_dict = msgpack.loads(response.content)
response_model = ResponseModel.model_validate(response_dict)
```

The steps of dumping from a pydantic model and validating the response dict
into a pydantic model can be skipped, if you prefer working with raw dicts
on the client.

<Tip>
  The implementation of `NumpyArrayField` only needs `pydantic`, no other Chains
  dependencies. So you can take that implementation code in isolation and
  integrate it in your client code.
</Tip>

<Warning>
  Some version combinations of `msgpack` and `msgpack_numpy` give errors, we
  know that `msgpack = ">=1.0.2"` and `msgpack-numpy = ">=0.4.8"` work.
</Warning>

### JSON

The JSON-schema to represent the array is a dict of `shape (tuple[int]), 
dtype (str), data_b64 (str)`. For example,

```python theme={"system"}
print(data.model_dump_json())
'{"some_numbers":{"shape":[3,2],"dtype":"float64", "data_b64":"30d4/rnKJEAsvm...'
```

The base64 data corresponds to `np.ndarray.tobytes()`.

To get back to the array from the JSON string, use the model's
`model_validate_json` method.

As discussed in the beginning, this schema is not performant for numeric data
and only offered as a compatibility layer (JSON does not allow bytes);
generally prefer the binary format.

## Simple `bytes` fields

It is possible to add a `bytes` field to a pydantic model used in a chain,
or as a plain argument to `run_remote`. This can be useful to include
non-numpy data formats such as images or audio/video snippets.

In this case, the "normal" JSON representation does not work and all
involved requests or Chainlet-Chainlet-invocations must use binary mode.

The same steps as for arrays [above](#binary-client) apply: construct dicts
with `bytes` values and keys corresponding to the `run_remote` argument
names or the field names in the pydantic model. Then use `msgpack` to
serialize and deserialize those dicts.

Don't forget to add `Content-type` headers and that `response.json()` will
not work.
