"""Run every test from the repository root:  python -m tests.run_all  [--bench]
--bench also runs the recognition benchmarks (several minutes)."""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ["test_correspondences", "test_layouts", "test_synthesis", "test_natal", "test_i18n", "test_datasets",
         "test_narrator", "test_flow", "test_e2e"]
BENCH = ["scale_test", "partial_test"]


def main() -> int:
    failed = []
    with tempfile.TemporaryDirectory() as out:
        for name in TESTS + (BENCH if "--bench" in sys.argv else []):
            args = [out] if name in ("test_flow", "test_e2e") else []
            r = subprocess.run([sys.executable, "-m", f"tests.{name}", *args], cwd=ROOT, capture_output=True, text=True)
            bad = r.returncode != 0 or any(line.startswith("MAL") or " MAL " in line for line in r.stdout.splitlines())
            print(f"{'FAIL' if bad else 'ok  '}  {name}")
            if bad:
                failed.append(name)
                print((r.stdout + r.stderr)[-1500:])
            elif name in BENCH:
                print(r.stdout)
    print(f"\n{'FAILED: ' + ', '.join(failed) if failed else 'All tests passed'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
