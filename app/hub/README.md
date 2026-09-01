# Trading Hub MVP

## Pipeline

`market data -> MTF scanner -> decision gate -> risk gate -> paper execution`

The MVP is intentionally conservative. Missing data or timeframe conflict results in `WAIT`. MT5 order routing remains disabled while integration is validated.

## Local smoke test

```powershell
python -m pytest -q
```

Then run the existing monitor/application entrypoint from the repository documentation. Do not enable live execution during MVP validation.
