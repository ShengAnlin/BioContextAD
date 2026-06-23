# src/llm_client.py — UTF-8 cache patch (for next run)

This patch prevents future cache writes from corrupting non-ASCII responses.
**It does not need to be applied right now** — the current 270 cache files
are already on disk and are cleaned in-place by `scripts/clean_cache.py`.
Apply this patch the next time you regenerate cache (e.g. when expanding
the eval set or running a new experiment).

---

## What to change

Open `src/llm_client.py`, find the function that writes cache (typically
named `_write_cache` or inline in `call_llm`), and locate the line:

```python
json.dump(payload, f, indent=2)
```

Change it to:

```python
json.dump(payload, f, indent=2, ensure_ascii=False)
```

Also, find the `open(cache_path, "w")` call and ensure it specifies UTF-8:

```python
# Before:
with open(cache_path, "w") as f:
    ...

# After:
with open(cache_path, "w", encoding="utf-8") as f:
    ...
```

If `encoding="utf-8"` is already there, only the `ensure_ascii=False` change
is needed.

---

## Why

- `json.dump(..., ensure_ascii=True)` (the default) escapes non-ASCII as
  `\uXXXX`. That's safe — but when paired with Windows' default `cp936`
  file encoding on `open()`, and an upstream that returns mixed bytes,
  certain code paths cause double-encoding artifacts to land in the file.
- `ensure_ascii=False` + explicit `encoding="utf-8"` makes the write path
  fully UTF-8 end-to-end, eliminating the ambiguity.

---

## Verification after applying

After the next API call, open a fresh cache file and confirm:

```powershell
Get-Content results\raw\<task>\<sample_id>_<role>.json -Encoding utf8 | Select-Object -First 30
```

Any Chinese characters should display correctly (not as `鎴戝缓璁` style mojibake).
