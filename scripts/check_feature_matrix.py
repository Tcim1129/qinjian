"""Validate that the client migration matrix covers every declared route.

This is intentionally dependency-free so it can run before either frontend is
installed.  It checks literal route paths and aliases from both Vue routers,
then requires the matrix to describe the five decision dimensions used by the
migration: interface, real data, sample data, and visual status, alongside the
route mapping itself.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "docs" / "architecture" / "current-feature-matrix.md"
ROUTERS = {
    "qinjian-ui-preview": ROOT / "qinjian-ui-preview" / "src" / "router.js",
    "web-vue3": ROOT / "web-vue3" / "src" / "router" / "index.js",
}
REQUIRED_COLUMNS = (
    "接口差异",
    "真实数据差异",
    "样例数据差异",
    "视觉状态差异",
)


def extract_routes(router_path: Path) -> set[str]:
    source = router_path.read_text(encoding="utf-8")
    routes = set(re.findall(r"\bpath\s*:\s*['\"]([^'\"]+)['\"]", source))
    for aliases in re.findall(r"\balias\s*:\s*\[([^\]]*)\]", source):
        routes.update(re.findall(r"['\"]([^'\"]+)['\"]", aliases))
    return routes


def main() -> int:
    missing_inputs = [str(path.relative_to(ROOT)) for path in ROUTERS.values() if not path.is_file()]
    if missing_inputs:
        print("missing router input: " + ", ".join(missing_inputs), file=sys.stderr)
        return 2

    if not MATRIX_PATH.is_file():
        print(f"matrix missing: {MATRIX_PATH.relative_to(ROOT)}", file=sys.stderr)
        return 1

    matrix = MATRIX_PATH.read_text(encoding="utf-8")
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in matrix]
    missing_routes: dict[str, list[str]] = {}
    for client, router_path in ROUTERS.items():
        routes = extract_routes(router_path)
        absent = sorted(route for route in routes if f"`{route}`" not in matrix)
        if absent:
            missing_routes[client] = absent

    if missing_columns:
        print("matrix missing columns: " + ", ".join(missing_columns), file=sys.stderr)
    for client, routes in missing_routes.items():
        print(f"{client} missing routes: {', '.join(routes)}", file=sys.stderr)
    if missing_columns or missing_routes:
        return 1

    counts = ", ".join(
        f"{client}={len(extract_routes(path))}" for client, path in ROUTERS.items()
    )
    print(f"matrix complete ({counts})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
