"""Writes openapi.json and openapi.yaml from the FastAPI source."""
import json, pathlib, yaml
from app.main import app

spec = app.openapi()
root = pathlib.Path(__file__).parent
(root / "openapi.json").write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n")
(root / "openapi.yaml").write_text(yaml.safe_dump(spec, sort_keys=False, allow_unicode=True))
print("paths:", *spec["paths"], sep="\n  ")
