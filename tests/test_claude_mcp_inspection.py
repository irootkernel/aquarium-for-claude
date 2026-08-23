"""Regression tests for the Claude Code MCP inspection that scripts/sync.py injects.

The generated `inspect_tools.py` is loaded directly, so these tests exercise the
bytes that ship. Every scenario is built from configuration files alone under a
private `CLAUDE_CONFIG_DIR`; no `claude` executable and no MCP server is needed,
which is also the property the inspection is required to have.
"""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSPECTOR = ROOT / "plugins/aquarium/skills/dev-setup/scripts/inspect_tools.py"


def load_inspector():
    specification = importlib.util.spec_from_file_location("inspect_tools", INSPECTOR)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class ClaudeMcpInspectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_inspector()
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name).resolve()
        self.config_dir = base / "config"
        self.config_dir.mkdir()
        self.repository = base / "repo"
        self.repository.mkdir()
        self.binary = base / "bin" / "mulgae"
        self.binary.parent.mkdir()
        self.binary.write_text("#!/bin/sh\nexit 0\n")
        self.binary.chmod(0o755)
        self.previous = os.environ.get("CLAUDE_CONFIG_DIR")
        os.environ["CLAUDE_CONFIG_DIR"] = str(self.config_dir)
        self.addCleanup(self.restore_environment)

    def restore_environment(self) -> None:
        if self.previous is None:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
        else:
            os.environ["CLAUDE_CONFIG_DIR"] = self.previous

    def write_user_configuration(self, payload: dict) -> None:
        (self.config_dir / ".claude.json").write_text(json.dumps(payload))

    def write_project_configuration(self, payload: dict) -> None:
        (self.repository / ".mcp.json").write_text(json.dumps(payload))

    def entry(self, args: list[str], command: str | None = None) -> dict:
        return {"type": "stdio", "command": command or str(self.binary), "args": args, "env": {}}

    def inspect(self, tool: str = "mulgae") -> dict:
        return self.module.inspect_claude_mcp(tool, self.repository, str(self.binary), 5.0)

    def test_nothing_configured_is_missing(self) -> None:
        registration = self.inspect()
        self.assertEqual(registration["status"], "missing")
        self.assertEqual(registration["effective_scope"], "none")
        self.assertEqual(registration["global"]["reason"], "user_configuration_missing")
        self.assertEqual(registration["local"]["reason"], "project_configuration_missing")
        self.assertEqual(registration["recommendation"], "install_global_registration")

    def test_user_scope_registration_is_configured_globally(self) -> None:
        self.write_user_configuration({"mcpServers": {"mulgae": self.entry(["mcp"])}})
        registration = self.inspect()
        self.assertEqual(registration["status"], "configured")
        self.assertEqual(registration["effective_scope"], "global")
        self.assertEqual(registration["recommendation"], "none")
        self.assertEqual(registration["global"]["required_verification"], "not_applicable")
        self.assertEqual(registration["global"]["tool_timeout_source"], "host")

    def test_user_scope_registration_must_not_pin_a_repository(self) -> None:
        self.write_user_configuration(
            {"mcpServers": {"mulgae": self.entry(["mcp", "--project-root", str(self.repository)])}}
        )
        registration = self.inspect()
        self.assertEqual(registration["status"], "degraded")
        self.assertEqual(registration["global"]["reason"], "registration_mismatch")
        self.assertFalse(registration["global"]["arguments_match"])

    def test_project_registration_is_pending_until_approved(self) -> None:
        self.write_user_configuration({"mcpServers": {}, "projects": {}})
        self.write_project_configuration(
            {"mcpServers": {"mulgae": self.entry(["mcp", "--project-root", str(self.repository)])}}
        )
        registration = self.inspect()
        self.assertEqual(registration["status"], "unverifiable")
        self.assertEqual(registration["reason"], "registration_pending_approval")
        self.assertEqual(registration["local"]["source"], "project")
        self.assertEqual(registration["local"]["approval"], "pending")
        self.assertTrue(registration["local_confirmation_required"])

    def test_approved_project_registration_is_configured_locally(self) -> None:
        self.write_user_configuration(
            {
                "mcpServers": {},
                "projects": {str(self.repository): {"enabledMcpjsonServers": ["mulgae"]}},
            }
        )
        self.write_project_configuration(
            {"mcpServers": {"mulgae": self.entry(["mcp", "--project-root", str(self.repository)])}}
        )
        registration = self.inspect()
        self.assertEqual(registration["status"], "configured")
        self.assertEqual(registration["effective_scope"], "local")
        self.assertEqual(registration["local"]["approval"], "approved")
        self.assertEqual(registration["recommendation"], "confirm_local_intent_or_migrate_to_global")

    def test_disabled_project_registration_is_degraded(self) -> None:
        self.write_user_configuration(
            {
                "mcpServers": {},
                "projects": {str(self.repository): {"disabledMcpjsonServers": ["mulgae"]}},
            }
        )
        self.write_project_configuration(
            {"mcpServers": {"mulgae": self.entry(["mcp", "--project-root", str(self.repository)])}}
        )
        registration = self.inspect()
        self.assertEqual(registration["status"], "degraded")
        self.assertEqual(registration["reason"], "registration_disabled")

    def test_private_local_registration_shadows_the_user_one(self) -> None:
        self.write_user_configuration(
            {
                "mcpServers": {"mulgae": self.entry(["mcp"])},
                "projects": {
                    str(self.repository): {
                        "mcpServers": {
                            "mulgae": self.entry(["mcp", "--project-root", str(self.repository)])
                        }
                    }
                },
            }
        )
        registration = self.inspect()
        self.assertEqual(registration["status"], "configured")
        self.assertEqual(registration["effective_scope"], "local")
        self.assertEqual(registration["local"]["source"], "local")
        self.assertEqual(registration["global"]["status"], "configured")
        self.assertEqual(registration["recommendation"], "confirm_or_remove_local_registration")

    def test_wrong_binary_is_a_mismatch(self) -> None:
        self.write_user_configuration(
            {"mcpServers": {"mulgae": self.entry(["mcp"], command="/usr/bin/true")}}
        )
        registration = self.inspect()
        self.assertEqual(registration["status"], "degraded")
        self.assertFalse(registration["global"]["binary_matches_selected"])

    def test_gaori_local_arguments_bind_the_repository(self) -> None:
        self.write_user_configuration(
            {
                "mcpServers": {},
                "projects": {str(self.repository): {"enableAllProjectMcpServers": True}},
            }
        )
        self.write_project_configuration(
            {"mcpServers": {"gaori": self.entry(["--repo", str(self.repository), "mcp"])}}
        )
        registration = self.inspect("gaori")
        self.assertEqual(registration["status"], "configured")
        self.assertEqual(registration["local"]["approval"], "approved")
        self.assertTrue(registration["local"]["repository_bound"])

    def test_invalid_project_configuration_is_never_proof_of_absence(self) -> None:
        self.write_user_configuration({"mcpServers": {"mulgae": self.entry(["mcp"])}})
        (self.repository / ".mcp.json").write_text("{ not json")
        registration = self.inspect()
        self.assertEqual(registration["status"], "degraded")
        self.assertEqual(registration["reason"], "project_configuration_invalid_json")

    def test_symlinked_project_configuration_is_unverifiable(self) -> None:
        target = Path(self.temporary.name) / "elsewhere.json"
        target.write_text(json.dumps({"mcpServers": {}}))
        (self.repository / ".mcp.json").symlink_to(target)
        registration = self.inspect()
        self.assertEqual(registration["status"], "unverifiable")
        self.assertEqual(registration["reason"], "project_configuration_symlinked")
        self.assertEqual(registration["recommendation"], "resolve_symlinked_local_configuration")
        self.assertIsNone(registration["local_confirmation_required"])

    def test_configuration_inventory_names_the_project_registration_file(self) -> None:
        tool = self.module.inspect_mulgae(self.repository, 5.0)
        self.assertIn(".mcp.json", [entry["path"] for entry in tool["configuration"]])
        self.assertNotIn("codex_version", tool["mcp_registration"])
        self.assertIn("claude_version", tool["mcp_registration"])


if __name__ == "__main__":
    unittest.main()
