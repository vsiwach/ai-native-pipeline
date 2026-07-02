# Vision
Source: https://docs.baseten.co/inference/model-apis/vision

Send images and videos alongside text to vision-capable models

Model APIs support both text and vision inputs, but multimodal capability depends on the underlying model. Vision-capable models accept images alongside text in the same request, using the OpenAI-compatible `image_url` content type. The model processes both modalities together, so it can answer questions about image content, compare multiple images, or extract structured data from screenshots.

Not all models support vision. Check the table below before sending image inputs.

## Supported models

| Model     | Slug                   |
| --------- | ---------------------- |
| Kimi K2.5 | `moonshotai/Kimi-K2.5` |
| Kimi K2.6 | `moonshotai/Kimi-K2.6` |

## Send a vision request

Use the `image_url` content type to include images in your messages.

Baseten retrieves image URLs **from the inference service**, so the URL must be reachable over HTTPS from Baseten's environment (for example your own object storage, Hugging Face artifact links, or other hosts that allow server-side fetches). Prefer stable, direct HTTPS links.

Optional `image_url.detail` controls preprocessing resolution: `low`, `high`, `original`, or `auto` (OpenAI-compatible). When in doubt, use `auto`. Send an image alongside a text prompt like this:

<Tabs>
  <Tab title="Python">
    ```python vision.py theme={"system"}
    from openai import OpenAI
    import os

    client = OpenAI(
        base_url="https://inference.baseten.co/v1",
        api_key=os.environ["BASETEN_API_KEY"],
    )

    response = client.chat.completions.create(
        model="moonshotai/Kimi-K2.6",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Describe the natural environment in the image.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "https://huggingface.co/datasets/YiYiXu/testing-images/resolve/main/seashore.png",
                            "detail": "auto",
                        },
                    },
                ],
            }
        ],
    )

    print(response.choices[0].message.content)
    ```
  </Tab>

  <Tab title="JavaScript">
    ```javascript vision.js theme={"system"}
    import OpenAI from "openai";

    const client = new OpenAI({
        baseURL: "https://inference.baseten.co/v1",
        apiKey: process.env.BASETEN_API_KEY,
    });

    const response = await client.chat.completions.create({
        model: "moonshotai/Kimi-K2.6",
        messages: [
            {
                role: "user",
                content: [
                    {
                        type: "text",
                        text: "Describe the natural environment in the image.",
                    },
                    {
                        type: "image_url",
                        image_url: {
                            url: "https://huggingface.co/datasets/YiYiXu/testing-images/resolve/main/seashore.png",
                            detail: "auto",
                        },
                    },
                ],
            },
        ],
    });

    console.log(response.choices[0].message.content);
    ```
  </Tab>

  <Tab title="cURL">
    ```bash Request theme={"system"}
    curl https://inference.baseten.co/v1/chat/completions \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $BASETEN_API_KEY" \
      -d '{
        "model": "moonshotai/Kimi-K2.6",
        "messages": [
          {
            "role": "user",
            "content": [
              {
                "type": "text",
                "text": "Describe the natural environment in the image."
              },
              {
                "type": "image_url",
                "image_url": {
                  "url": "https://huggingface.co/datasets/YiYiXu/testing-images/resolve/main/seashore.png",
                  "detail": "auto"
                }
              }
            ]
          }
        ]
      }'
    ```
  </Tab>
</Tabs>

## Image and video limits

Each vision-capable model enforces its own per-request limits on media count and size. The current limits for Kimi are:

| Limit                                  | Kimi K2.5 | Kimi K2.6 |
| -------------------------------------- | --------: | --------: |
| Max images per request                 |        96 |        96 |
| Max videos per request                 |        12 |        12 |
| Max total media size per request (URL) |    240 MB |    240 MB |
| Max size per image (URL)               |     90 MB |     80 MB |
| Max request body (base64)              |      5 MB |      5 MB |

Pass images by URL whenever you can. The model's vision encoder fetches each URL and enforces the per-image and total-media caps directly, while the request body stays small. Base64-encoded images travel inside the request body and hit the 5 MB cap quickly.

<Note>Other Model APIs models set their own limits. Confirm the values for a given slug in the Baseten app or through [`/v1/models`](/inference/model-apis/overview#list-available-models).</Note>

## Pricing

There is no additional per-image fee. Images are converted to input tokens and priced at the model's standard input rate. Higher resolution images produce more tokens and cost more to process.

The exact conversion from pixels to tokens depends on the model. Kimi K2.5 and Kimi K2.6 divide each image into 14×14 pixel tiles where each tile becomes one input token. The cost table below uses Kimi K2.5's uncached input rate (\$0.60 per million tokens); for Kimi K2.6 and other models, use the rates on the [Model APIs pricing page](https://www.baseten.co/pricing).

| Image resolution |  Tiles | Input tokens | Cost at \$0.60/M |
| ---------------- | -----: | -----------: | ---------------: |
| 256×256          |    324 |          324 |         \$0.0002 |
| 512×512          |  1,296 |        1,296 |         \$0.0008 |
| 1024×1024        |  5,329 |        5,329 |         \$0.0032 |
| 1920×1080        | 10,234 |       10,234 |         \$0.0061 |

For videos, token count scales with both resolution and the number of sampled frames.

## Next steps

<CardGroup>
  <Card title="Model APIs overview" icon="layer-group" href="/inference/model-apis/overview">
    Supported models, pricing, and the feature support matrix
  </Card>

  <Card title="Chat Completions reference" icon="code" href="/reference/inference-api/chat-completions">
    Full request and response schema for the `image_url` content type
  </Card>
</CardGroup>
