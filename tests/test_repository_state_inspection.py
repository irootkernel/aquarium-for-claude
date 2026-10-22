"""Exercise the repository-state inspector Subagent Review runs for its baseline.

The inspector is an edition addition rather than upstream code, so nothing else
executes it: these tests load the generated copy, prove that no Git filter the
inspected repository or its submodules configure ever runs, and prove that the
comparison still sees the mutations it exists to catch.
"""

from __future__ import annotations

import importlib.util
import json
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSPECTOR = ROOT / "plugins/aquarium/skills/subagent-review/scripts/inspect_repository_state.py"


def load_inspector():
    spec = importlib.util.spec_from_file_location("inspect_repository_state", INSPECTOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(repository: Path, *arguments: str) -> str:
    # Local submodule clones need the file protocol, which Git refuses by default.
    result = subprocess.run(
        ["git", "-c", "protocol.file.allow=always", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def repository(parent: Path, name: str = "repository") -> Path:
    root = parent / name
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.name", "Aquarium Test")
    git(root, "config", "user.email", "aquarium@example.invalid")
    git(root, "config", "commit.gpgsign", "false")
    (root / "tracked.txt").write_text("base\n", encoding="utf-8")
    git(root, "add", "tracked.txt")
    git(root, "commit", "-qm", "base")
    return root


def commit_filtered_file(root: Path, driver: str) -> None:
    (root / ".gitattributes").write_text(f"filtered.txt filter={driver}\n", encoding="utf-8")
    (root / "filtered.txt").write_text("base\n", encoding="utf-8")
    git(root, "add", ".gitattributes", "filtered.txt")
    git(root, "commit", "-qm", "filter baseline")


class InspectorTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_inspector()
        self.temporary = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.temporary, True)

    def workspace(self) -> Path:
        return Path(tempfile.mkdtemp(dir=self.temporary))

    def canonical(self, root: Path) -> Path:
        return self.module.canonical_git_root(root.resolve())

    def configure_filter(self, root: Path, driver: str, kind: str, sentinel: Path) -> None:
        callback = sentinel.with_name("filter.py")
        callback.write_text(
            "import pathlib, sys\n"
            "pathlib.Path(sys.argv[1]).write_text('ran', encoding='utf-8')\n"
            "if sys.argv[2] == 'clean':\n"
            "    sys.stdout.buffer.write(sys.stdin.buffer.read())\n",
            encoding="utf-8",
        )
        command = " ".join(shlex.quote(str(value)) for value in (sys.executable, callback, sentinel, kind))
        git(root, "config", f"filter.{driver}.{kind}", command)
        git(root, "config", f"filter.{driver}.required", "true")

    def superproject_with_submodule(self, parent: Path) -> Path:
        child = repository(parent, "child")
        commit_filtered_file(child, "inner")
        root = repository(parent, "super")
        git(root, "submodule", "add", "-q", str(child), "child")
        git(root, "commit", "-qm", "add submodule")
        return root


class RepositoryFilterTest(InspectorTestCase):
    """No clean, smudge, or process filter the inspected repository names ever runs."""

    def test_snapshot_and_compare_never_run_a_repository_filter(self) -> None:
        for kind in ("clean", "process"):
            for driver in ("sentinel", "sentinel=with.dot"):
                with self.subTest(kind=kind, driver=driver):
                    parent = self.workspace()
                    root = repository(parent)
                    commit_filtered_file(root, driver)
                    (root / "filtered.txt").write_text("next\n", encoding="utf-8")
                    sentinel = parent / "filter-ran"
                    self.configure_filter(root, driver, kind, sentinel)
                    watched = (root / ".git/index", root / ".git/config", root / "filtered.txt")
                    before = {path: path.read_bytes() for path in watched}

                    canonical = self.canonical(root)
                    result = self.module.compare(canonical, self.module.snapshot(canonical))

                    self.assertFalse(sentinel.exists())
                    self.assertEqual({path: path.read_bytes() for path in watched}, before)
                    self.assertFalse(result["drift"])

    def test_snapshot_never_runs_a_filter_a_submodule_configures(self) -> None:
        for kind in ("clean", "process"):
            with self.subTest(kind=kind):
                parent = self.workspace()
                root = self.superproject_with_submodule(parent)
                (root / "child" / "filtered.txt").write_text("next\n", encoding="utf-8")
                sentinel = parent / "filter-ran"
                self.configure_filter(root / "child", "inner", kind, sentinel)

                self.module.snapshot(self.canonical(root))

                self.assertFalse(sentinel.exists())


class RepositoryDriftTest(InspectorTestCase):
    """The comparison still sees the mutations a review must not make."""

    def test_a_tracked_edit_drifts(self) -> None:
        root = self.canonical(repository(self.workspace()))
        baseline = self.module.snapshot(root)
        self.assertFalse(self.module.compare(root, baseline)["drift"])

        (root / "tracked.txt").write_text("changed\n", encoding="utf-8")
        result = self.module.compare(root, baseline)

        self.assertTrue(result["drift"])
        self.assertIn("tracked_worktree_sha256", result["changed"])

    def test_submodule_mutations_drift_without_superproject_recursion(self) -> None:
        # The superproject's diff and status no longer recurse into submodules,
        # so every submodule mutation has to surface through the direct hashing.
        identity = ("-c", "user.name=Aquarium Test", "-c", "user.email=aquarium@example.invalid", "-c", "commit.gpgsign=false")

        def edit_tracked(child: Path) -> None:
            (child / "tracked.txt").write_text("changed\n", encoding="utf-8")

        def add_untracked(child: Path) -> None:
            (child / "new.txt").write_text("new\n", encoding="utf-8")

        def stage_edit(child: Path) -> None:
            edit_tracked(child)
            git(child, "add", "tracked.txt")

        def commit_inside(child: Path) -> None:
            stage_edit(child)
            git(child, *identity, "commit", "-qm", "inner change")

        def deinit(child: Path) -> None:
            git(child.parent, "submodule", "deinit", "-q", "-f", child.name)

        for label, mutate in (
            ("tracked edit", edit_tracked),
            ("untracked file", add_untracked),
            ("staged edit", stage_edit),
            ("commit inside", commit_inside),
            ("deinit", deinit),
        ):
            with self.subTest(mutation=label):
                root = self.canonical(self.superproject_with_submodule(self.workspace()))
                baseline = self.module.snapshot(root)
                self.assertFalse(self.module.compare(root, baseline)["drift"])

                mutate(root / "child")
                result = self.module.compare(root, baseline)

                self.assertTrue(result["drift"])
                self.assertIn("tracked_worktree_sha256", result["changed"])

    def test_the_cli_round_trips_its_own_baseline(self) -> None:
        root = self.canonical(repository(self.workspace()))
        base = [sys.executable, "-B", str(INSPECTOR), "--repository", str(root)]
        snapshot = subprocess.run([*base, "--snapshot"], check=True, capture_output=True)
        compared = subprocess.run([*base, "--compare"], input=snapshot.stdout, check=True, capture_output=True)

        result = json.loads(compared.stdout)
        self.assertEqual(result["baseline_fingerprint"], json.loads(snapshot.stdout)["fingerprint"])
        self.assertFalse(result["drift"])


if __name__ == "__main__":
    unittest.main()
