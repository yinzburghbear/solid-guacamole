from pathlib import Path

root = Path(__file__).resolve().parents[1]
src = root / "graphite" / "src" / "index.css"
out = root / "graphite" / "graphite.css"

parts = []
for line in src.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line.startswith("@import"):
        continue
    rel = line.split('"', 2)[1]
    parts.append((src.parent / rel).read_text(encoding="utf-8").rstrip() + "\n")

out.write_text("\n".join(parts), encoding="utf-8")
print(f"Built {out}")
