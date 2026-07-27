# Contributing to Personal OS

All examples, fixtures, screenshots, benchmarks, and documentation committed
to this repository must use synthetic data. Do not copy a real Personal OS
record, ChatGPT export, attachment, person, employer, address, travel history,
financial value, API key, or local machine path into a tracked file.

Run these checks from the repository root before publishing:

```powershell
.\tools\check_public_release.ps1
```

The working `requirements/` directory is an immutable product-specification
source. The public snapshot builder produces a sanitized copy without editing
that source directory.

