
# Vulnerable Rust Test Project

This project intentionally includes two known vulnerable crate versions:

## Included Vulnerabilities

### 1. wasmtime = 38.0.3
- Advisory: RUSTSEC-2025-0118
- Issue: Unsound API access to WebAssembly shared linear memory.

### 2. gix-features = 0.40.0
- Advisory: RUSTSEC-2025-0021
- Issue: SHA‑1 collisions not detected (crypto‑failure).

Both versions are **within the affected ranges** defined by their respective RustSec advisories.

---

## Generate lockfile

```
cargo generate-lockfile
```

## Optional build
```
cargo build
```
