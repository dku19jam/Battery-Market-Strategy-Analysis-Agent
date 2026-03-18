"""Qwen embedding client with Apple Silicon aware device selection."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QwenEmbeddingConfig:
    model_id: str
    device: str = "auto"
    batch_size: int = 4


class QwenEmbeddingClient:
    def __init__(
        self,
        model_id: str,
        device: str = "auto",
        batch_size: int = 4,
        tokenizer: object | None = None,
        model: object | None = None,
        torch_module: object | None = None,
    ) -> None:
        self.model_id = model_id
        self.batch_size = batch_size
        self._torch = torch_module or _import_torch()
        self.resolved_device = _resolve_device(device, self._torch)
        self._tokenizer = tokenizer or _load_tokenizer(model_id)
        self._model = (model or _load_model(model_id)).to(self.resolved_device).eval()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed_texts([f"passage: {text}" for text in texts])

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return self._embed_texts([f"query: {text}" for text in texts])

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        offset = 0
        batch_size = self.batch_size
        while offset < len(texts):
            batch = texts[offset : offset + batch_size]
            try:
                vectors.extend(self._embed_batch(batch))
                offset += len(batch)
                batch_size = self.batch_size
            except RuntimeError as exc:
                if not _is_oom_error(exc):
                    raise
                if batch_size > 1:
                    batch_size = max(1, batch_size // 2)
                    _empty_mps_cache(self._torch)
                    continue
                if self.resolved_device == "mps":
                    self.resolved_device = "cpu"
                    self._model = self._model.to(self.resolved_device).eval()
                    _empty_mps_cache(self._torch)
                    continue
                raise
        return vectors

    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        encoded = self._tokenizer(batch, padding=True, truncation=True, return_tensors="pt")
        encoded = {
            key: value.to(self.resolved_device) if hasattr(value, "to") else value
            for key, value in encoded.items()
        }
        with self._torch.no_grad():
            output = self._model(**encoded)
        pooled = self._mean_pool(output.last_hidden_state, encoded["attention_mask"])
        normalized = self._torch.nn.functional.normalize(pooled, p=2, dim=1)
        if hasattr(normalized, "cpu"):
            normalized = normalized.cpu()
        return normalized.tolist()

    def _mean_pool(self, last_hidden_state: object, attention_mask: object) -> object:
        if _is_fake_tensor(last_hidden_state) and _is_fake_tensor(attention_mask):
            return _fake_mean_pool(last_hidden_state, attention_mask)

        expanded_mask = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
        weighted = last_hidden_state * expanded_mask
        summed = weighted.sum(dim=1)
        counts = self._torch.clamp(expanded_mask.sum(dim=1), min=1e-9)
        return summed / counts


def _resolve_device(device: str, torch_module: object) -> str:
    if device != "auto":
        return device
    if getattr(getattr(torch_module, "backends", object()), "mps", None) is not None:
        if torch_module.backends.mps.is_available():
            return "mps"
    if getattr(torch_module, "cuda", None) is not None and torch_module.cuda.is_available():
        return "cuda"
    return "cpu"


def _import_torch() -> object:
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("torch is required for Qwen embeddings.") from exc
    return torch


def _load_tokenizer(model_id: str) -> object:
    try:
        from transformers import AutoTokenizer
    except ImportError as exc:
        raise RuntimeError("transformers is required for Qwen embeddings.") from exc
    return AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)


def _load_model(model_id: str) -> object:
    try:
        from transformers import AutoModel
    except ImportError as exc:
        raise RuntimeError("transformers is required for Qwen embeddings.") from exc
    return AutoModel.from_pretrained(model_id, trust_remote_code=True)


def _fake_mean_pool(last_hidden_state: object, attention_mask: object) -> object:
    values = getattr(last_hidden_state, "values")
    masks = getattr(attention_mask, "values")
    pooled: list[list[float]] = []
    for row, mask_row in zip(values, masks):
        weighted = [value for value, mask in zip(row, mask_row) if mask]
        if not weighted:
            pooled.append([0.0 for _ in row])
            continue
        mean_value = sum(weighted) / len(weighted)
        pooled.append([mean_value for _ in row])
    return type(last_hidden_state)(pooled)


def _is_fake_tensor(value: object) -> bool:
    values_attr = getattr(value, "values", None)
    return values_attr is not None and not callable(values_attr)


def _is_oom_error(exc: RuntimeError) -> bool:
    return "out of memory" in str(exc).lower()


def _empty_mps_cache(torch_module: object) -> None:
    mps_module = getattr(torch_module, "mps", None)
    if mps_module is not None and hasattr(mps_module, "empty_cache"):
        mps_module.empty_cache()
