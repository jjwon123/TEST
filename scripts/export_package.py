"""Package export boundary.

Future implementation should copy QA-approved exports into package folders and
write final distribution manifests.
"""

from pathlib import Path


def package_root(run_dir: Path) -> Path:
    return run_dir / "06_qa_packaging"
