# ML endpoint contracts (v1 scaffold)

## detect

- **Input**: `{ "image_b64": string }`
- **Output**: `{ "bboxes": [{ "x", "y", "w", "h", "angle" }] }`

## embed

- **Input**: `{ "image_b64": string }`
- **Output**: `{ "embedding_dim": 1024, "vector": number[] }` (L2-normalised)

## ocr

- **Input**: `{ "image_b64": string }`
- **Output**: `{ "text": string, "fields": { "name"?, "number"?, "set"? } }`

## grade

- **Input**: `{ "image_b64": string }`
- **Output**:
  ```json
  {
    "overall": number,
    "centering": number,
    "corners": number,
    "edges": number,
    "surface": number,
    "psa_low": number,
    "psa_high": number,
    "psa_label": string,
    "confidence": number,
    "model": "heuristic-v0" | "resnet50-v1"
  }
  ```
  Scores are on a 1–10 internal scale; `psa_label` is the estimated PSA range (e.g. `"PSA 8–9"`).
