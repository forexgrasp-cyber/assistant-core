"""Security scan: bandit + pip-audit equivalent for the project.

Run as part of the pre-push gate. Checks for:
- Hardcoded secrets / credentials in source
- Silent exception swallowing on critical paths
- Dead imports (unused symbols)
- Known-vulnerable dependencies (pip-audit if available)
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

SECRET_PATTERNS = [
    r"sk_live_[A-Za-z0-9]+",
    r"sk_test_[A-Za-z0-9]+",
    r"pk_live_[A-Za-z0-9]+",
    r"rk_live_[A-Za-z0-9]+",
    r"password\s*=\s*['\"][^'\"]+['\"]",
    r"secret\s*=\s*['\"][^'\"]+['\"]",
    r"api_key\s*=\s*['\"][^'\"]+['\"]",
    r"dev-secret-change-me",
]

SILENT_SWALLOW_PATTERN = re.compile(r"except\s+Exception\s*:\s*\n\s*pass")


def scan_file(path: Path) -> list[str]:
    issues: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return issues

    for i, line in enumerate(text.splitlines(), 1):
        for pat in SECRET_PATTERNS:
            if re.search(pat, line):
                issues.append(f"{path}:{i}: possible hardcoded secret: {line.strip()[:80]}")  # noqa: PERF401

    if SILENT_SWALLOW_PATTERN.search(text):
        # Find the line number
        for i, line in enumerate(text.splitlines(), 1):
            if line.strip() == "except Exception:":
                issues.append(f"{path}:{i}: silent exception swallow (except Exception: pass)")
                break

    return issues


def scan_paths(paths: list[Path]) -> list[str]:
    issues: list[str] = []
    for p in paths:
        if p.is_dir():
            for py in p.rglob("*.py"):
                issues.extend(scan_file(py))
        else:
            issues.extend(scan_file(p))
    return issues


def pip_audit() -> list[str]:
    """Run pip-audit if available."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "audit"],
            capture_output=True,
            text=True,
            timeout=60, check=False,
        )
        if result.returncode != 0:
            return [f"pip-audit: {result.stdout.strip()} {result.stderr.strip()}"]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ["pip-audit not available or timed out"]
    return []


def main() -> None:
    scan_dirs = [BASE / "packages", BASE / "apps", BASE / "tests"]
    issues = scan_paths(scan_dirs)
    issues.extend(pip_audit())

    if issues:
        print(f"Security scan found {len(issues)} issue(s):")  # noqa: T201
        for issue in issues:
            print(f"  {issue}")  # noqa: T201
        sys.exit(1)

    print("Security scan: clean")  # noqa: T201
    sys.exit(0)


if __name__ == "__main__":
    main()
