#!/usr/bin/env ruby
# frozen_string_literal: true

# Validates the invariants that are specific to the Claude Code artifact.
#
# Upstream owns the prose contract and already validates it in its own CI, so
# this file deliberately does not re-assert skill wording. It checks only what
# the transformation is responsible for: invocation gating and the delegation
# note it implies, host-neutral text, manifest agreement, deliberate
# exclusions, runnable generated scripts, and freshness against the pinned
# upstream.

require "json"
require "pathname"
require "set"
require "yaml"

ROOT = Pathname.new(__dir__).parent
PLUGIN = ROOT.join("plugins/aquarium")
UPSTREAM_PLUGIN = ROOT.join("upstream/plugins/aquarium")

failures = []

def assert(condition, message)
  return if condition

  warn "error: #{message}"
  exit 1
end

# --- generated tree exists -------------------------------------------------

assert(PLUGIN.directory?, "plugins/aquarium/ has not been generated; run scripts/sync.py")

skill_paths = Pathname.glob(PLUGIN.join("skills/*/SKILL.md")).sort
assert(!skill_paths.empty?, "no skills were generated")

sync_manifest = JSON.parse(PLUGIN.join("sync-manifest.json").read)
assert(sync_manifest.dig("upstream", "commit").to_s.length == 40, "sync manifest lacks an upstream commit")

# The committed output is generated from the submodule's working tree, but CI
# regenerates from the gitlink. A checkout that moved without `git add upstream`
# passes `--check` locally and fails in CI one push later, so assert agreement.
gitlink = `git -C #{ROOT} ls-files -s upstream`.split[1].to_s
assert(
  gitlink.empty? || gitlink == sync_manifest.dig("upstream", "commit"),
  "sync manifest commit #{sync_manifest.dig('upstream', 'commit')} differs from the staged submodule gitlink #{gitlink}; run `git add upstream`"
)

# --- invocation gating mirrors the upstream sidecar ------------------------

ALLOWED_FRONTMATTER_KEYS = %w[argument-hint description disable-model-invocation name].freeze
ARGUMENT_HINTS = sync_manifest.fetch("argument_hints")

skill_paths.each do |path|
  name = path.dirname.basename.to_s
  frontmatter = path.read.match(/\A---\n(.*?)\n---\n/m)
  assert(frontmatter, "missing frontmatter: #{name}")

  metadata = YAML.safe_load(frontmatter[1], aliases: false)
  assert((metadata.keys - ALLOWED_FRONTMATTER_KEYS).empty?, "unexpected frontmatter keys: #{name}")
  assert(metadata.key?("name") && metadata.key?("description"), "frontmatter must define name and description: #{name}")
  assert(metadata.fetch("name") == name, "skill name/path mismatch: #{name}")
  # Trigger phrasing is upstream's: v0.1.18–v0.1.21 descriptions no longer all say "Use when".
  assert(!metadata.fetch("description").to_s.strip.empty?, "skill lacks a description: #{name}")

  # The upstream Codex sidecar is the single source of truth for invocation
  # policy. If these ever disagree, a mutating skill could fire without the
  # user asking for it, so the relationship is asserted as a biconditional.
  sidecar_path = UPSTREAM_PLUGIN.join("skills/#{name}/agents/openai.yaml")
  unless sidecar_path.file?
    if UPSTREAM_PLUGIN.directory?
      # A skill with no upstream sidecar must be a recorded addition, and it
      # must gate itself: additions bypass the sidecar-derived decoration.
      assert(sync_manifest.fetch("additions").include?("skills/#{name}/SKILL.md"), "skill has no upstream sidecar and is not a recorded addition: #{name}")
      assert(metadata.fetch("disable-model-invocation", false) == true, "addition skill must declare disable-model-invocation: true: #{name}")
    end
    next
  end

  implicit = YAML.safe_load(sidecar_path.read, aliases: false).fetch("policy").fetch("allow_implicit_invocation")
  assert([true, false].include?(implicit), "allow_implicit_invocation must be a boolean: #{name}")
  assert(
    metadata.fetch("disable-model-invocation", false) == !implicit,
    "disable-model-invocation must mirror the upstream sidecar: #{name} " \
    "(sidecar allow_implicit_invocation=#{implicit})"
  )
  # The slash-menu hint is generated from one table, recorded in the sync
  # manifest; a skill carries a hint exactly when the table names it.
  assert(
    metadata["argument-hint"] == ARGUMENT_HINTS[name],
    "argument-hint must match the recorded table for #{name}: " \
    "#{metadata['argument-hint'].inspect} vs #{ARGUMENT_HINTS[name].inspect}"
  )
end

if UPSTREAM_PLUGIN.directory?
  # The generated skill set is the upstream set, minus the skills this edition
  # excludes whole, plus every skill carried in from additions/; the sync
  # manifest is the single source for both, and the exclusion list is compared
  # with scripts/sync.py below.
  upstream_skills = Pathname.glob(UPSTREAM_PLUGIN.join("skills/*/SKILL.md")).map { |p| p.dirname.basename.to_s }.sort
  addition_skills = sync_manifest.fetch("additions").map { |p| p[%r{\Askills/([^/]+)/SKILL\.md\z}, 1] }.compact
  expected = (upstream_skills - sync_manifest.fetch("excluded_skills") + addition_skills).sort
  generated = skill_paths.map { |p| p.dirname.basename.to_s }.sort
  assert(generated == expected, "generated skills do not match upstream minus exclusions plus additions: #{(generated - expected) | (expected - generated)}")
end

# --- invocations resolve to what ships -----------------------------------------

# Upstream renames skills without aliases — v0.1.20 replaced `independent-review`
# with `subagent-review` — and nothing else notices text that still names the
# retired skill or agent: before the v0.1.21 adoption the bundled reviewer's
# description and the catalog override both did. Every `/aquarium:<skill>` in
# generated text must name a generated skill, and every bare `aquarium:<name>` a
# generated skill or a shipped plugin agent; only upstream's own migration
# history may name a retired skill, and each such allowance must still occur.
HISTORICAL_INVOCATIONS = [
  ["references/review-routing-contract.md", "/aquarium:independent-review"]
].freeze
orphan_skill_directories = Pathname.glob(PLUGIN.join("skills/*")).select(&:directory?).reject { |dir| dir.join("SKILL.md").file? }
assert(orphan_skill_directories.empty?, "skill directories without SKILL.md ship nothing Claude Code loads: #{orphan_skill_directories.map { |dir| dir.relative_path_from(PLUGIN).to_s }.inspect}")
generated_skill_names = skill_paths.map { |path| path.dirname.basename.to_s }.to_set
shipped_agent_names = Pathname.glob(PLUGIN.join("agents/*.md")).map { |path| path.basename(".md").to_s }.to_set
unresolved_invocations = []
# FNM_DOTMATCH reaches `.claude-plugin/plugin.json`, whose description goes
# through the substitution table too.
Pathname.glob(PLUGIN.join("**/*"), File::FNM_DOTMATCH).select(&:file?).each do |path|
  next unless %w[.md .py .json .yaml].include?(path.extname)

  relative = path.relative_path_from(PLUGIN).to_s
  path.read.scan(%r{(/?)aquarium:([A-Za-z0-9][A-Za-z0-9_-]*)}) do |slash, name|
    token = "#{slash}aquarium:#{name}"
    resolved = slash.empty? ? generated_skill_names.include?(name) || shipped_agent_names.include?(name) : generated_skill_names.include?(name)
    unresolved_invocations << "#{relative}: #{token}" unless resolved || HISTORICAL_INVOCATIONS.include?([relative, token])
  end
end
assert(unresolved_invocations.empty?, "generated text names a skill or agent the plugin does not ship: #{unresolved_invocations.uniq.inspect}")
HISTORICAL_INVOCATIONS.each do |relative, token|
  occurrences = PLUGIN.join(relative).file? ? PLUGIN.join(relative).read.scan(token).length : 0
  assert(occurrences == 1, "historical invocation #{token} must occur exactly once in #{relative}, found #{occurrences}; remove or re-derive its allowance")
end

# --- host-neutral generated text -------------------------------------------

FORBIDDEN_TEXT = ["$aquarium:", "$use-", "$create-", "$lore-", "$herdr", "$humanize", "request_user_input",
                  "--agent codex", ".agents/skills", "${PLUGIN_ROOT}", ".codex/config",
                  "Codex", "aquarium-status", "production-status"].freeze

# Lowercase `$name` tokens that are shell variables rather than skill sigils, so
# the scan below subtracts them. v0.1.14 pinned the commit identity through
# `git -c user.name="$aquarium_commit_name"`, which the scan read as an unmapped
# sigil; `sync.py` keeps the same list and requires each one to still occur
# upstream.
SIGIL_LITERALS = ["$aquarium_commit_name", "$aquarium_commit_email"].freeze

# Some upstream text names the Codex CLI as a third-party tool rather than as the
# host — a Mulgae provider, a required CLI version — and stays correct here. Each
# exemption is gated on the upstream bytes a human reviewed, so `sync.py` stops
# when that file changes. Only the `Codex` needle is skipped, and only for these.
CODEX_EXEMPTIONS = begin
  path = ROOT.join("overrides/codex-exemptions.json")
  path.file? ? JSON.parse(path.read).keys.to_set : Set.new
end

Pathname.glob(PLUGIN.join("**/*.{md,json,py,yaml}")).sort.each do |path|
  relative = path.relative_path_from(PLUGIN).to_s
  next if relative == "sync-manifest.json"

  text = path.read
  FORBIDDEN_TEXT.each do |needle|
    next if needle == "Codex" && CODEX_EXEMPTIONS.include?(relative)

    assert(!text.include?(needle), "generated text contains `#{needle}`: #{relative}")
  end
end

# `FORBIDDEN_TEXT` names one needle per sigil family that already exists, so a
# family upstream introduces later passes it and ships Codex invocation syntax
# in silence. Uppercase spellings are environment variables and do not match.
SIGIL = /\$[a-z][a-z0-9:_-]*/.freeze

Pathname.glob(PLUGIN.join("**/*.md")).sort.each do |path|
  found = (path.read.scan(SIGIL).uniq - SIGIL_LITERALS).sort
  assert(
    found.empty?,
    "generated text contains Codex skill sigils #{found.join(', ')}: " \
    "#{path.relative_path_from(PLUGIN)}"
  )
end

# The regex is the only thing standing between an upstream `$newthing` and a
# Claude Code user, and nothing else asserts that it still works.
assert(SIGIL.match?("$newthing"), "the sigil regex no longer matches a Codex skill sigil")
assert(!SIGIL.match?("${CLAUDE_PLUGIN_ROOT}"), "the sigil regex must ignore shell variables")
# Each exception exists only because the regex still spells it. One that stopped
# matching would be dead weight hiding behind a guard it no longer needs.
SIGIL_LITERALS.each do |literal|
  assert(literal[SIGIL] == literal, "sigil exception `#{literal}` is not a whole token the scan would emit")
end

# `FORBIDDEN` and `SIGIL_LITERALS` in scripts/sync.py and their counterparts
# here are maintained by hand; an entry added to one and not the other halves
# the guard. Comparing them as sets closes both directions: a Ruby-only needle
# would let generation write text CI then rejects, and a Python-only needle
# would leave the artifact unguarded whenever the generated tree is checked
# without regenerating it. `.agents/skills` was Python-only until this check
# existed. A Ruby-only sigil exception would hide a real sigil from CI, and a
# Python-only one would let generation ship text this file then rejects.
#
# The tables are read by parsing scripts/sync.py rather than executing it, and
# through a real Python parser rather than a regex, so a literal carrying a
# quote or a backslash cannot silently drop out of the comparison.
EXTRACT_TABLES = <<~PYTHON
  import ast, json, pathlib

  tree = ast.parse(pathlib.Path("scripts/sync.py").read_text())
  wanted = {"FORBIDDEN", "SIGIL_LITERALS", "EXCLUDED_PLUGIN_ROOT", "EXCLUDED_SKILLS", "DELEGATION_NOTE"}
  found = {}
  for node in tree.body:
      target = getattr(node, "target", None)
      name = getattr(target, "id", None)
      if name in wanted and isinstance(node.value, ast.Constant):
          found[name] = node.value.value
      elif name in wanted:
          found[name] = [
              element.elts[0].value if isinstance(element, ast.Tuple) else element.value
              for element in node.value.elts
          ]
  missing = sorted(wanted - set(found))
  if missing:
      raise SystemExit("not found in scripts/sync.py: " + ", ".join(missing))
  print(json.dumps(found))
PYTHON

sync_tables = begin
  raw = IO.popen(["python3", "-c", EXTRACT_TABLES], chdir: ROOT.to_s, &:read)
  assert($?.success?, "could not read the text guards from scripts/sync.py")
  JSON.parse(raw)
end

assert(
  sync_tables.fetch("FORBIDDEN").to_set == FORBIDDEN_TEXT.to_set,
  "forbidden needles disagree: only in scripts/sync.py " \
  "#{(sync_tables.fetch('FORBIDDEN').to_set - FORBIDDEN_TEXT.to_set).to_a.inspect}, " \
  "only in tests/validate.rb #{(FORBIDDEN_TEXT.to_set - sync_tables.fetch('FORBIDDEN').to_set).to_a.inspect}"
)

assert(
  sync_tables.fetch("SIGIL_LITERALS").to_set == SIGIL_LITERALS.to_set,
  "sigil exceptions disagree: only in scripts/sync.py " \
  "#{(sync_tables.fetch('SIGIL_LITERALS').to_set - SIGIL_LITERALS.to_set).to_a.inspect}, " \
  "only in tests/validate.rb #{(SIGIL_LITERALS.to_set - sync_tables.fetch('SIGIL_LITERALS').to_set).to_a.inspect}"
)

assert(
  skill_paths.any? { |path| path.read.include?("/aquarium:") },
  "generated skills never reference the Claude invocation form"
)

# Upstream skills delegate to each other by name, and Claude Code's Skill tool
# refuses a gated skill unless the user typed it, so every gated
# upstream-derived skill must open with the note that routes a delegation
# through the delegated skill's file, before any instruction the model could
# act on. A model-invocable skill must not carry it: Claude can start one on its
# own, and a hand-off from it into a gated skill has to keep going back to the
# user. Additions are authored final and delegate to nothing.
DELEGATION_NOTE = sync_tables.fetch("DELEGATION_NOTE")
assert(DELEGATION_NOTE.is_a?(String) && !DELEGATION_NOTE.include?("\n"), "the delegation note must be one paragraph on one line")
assert(DELEGATION_NOTE.scan(SIGIL).empty?, "the delegation note must not spell a skill sigil")
FORBIDDEN_TEXT.each do |needle|
  assert(!DELEGATION_NOTE.include?(needle), "the delegation note contains `#{needle}`")
end
addition_skill_names = sync_manifest.fetch("additions").map { |p| p[%r{\Askills/([^/]+)/SKILL\.md\z}, 1] }.compact
skill_paths.each do |path|
  name = path.dirname.basename.to_s
  text = path.read
  frontmatter = text.match(/\A---\n(.*?)\n---\n/m)
  gated = YAML.safe_load(frontmatter[1], aliases: false).fetch("disable-model-invocation", false) == true
  if addition_skill_names.include?(name) || !gated
    assert(!text.include?(DELEGATION_NOTE), "only a gated upstream-derived skill may carry the delegation note: #{name}")
    next
  end
  assert(
    text[frontmatter.end(0)..].match?(/\A\n# [^\n]+\n\n#{Regexp.escape(DELEGATION_NOTE)}\n\n/),
    "gated skill must open with the delegation note directly under its title: #{name}"
  )
  assert(text.scan(DELEGATION_NOTE).length == 1, "gated skill must carry the delegation note exactly once: #{name}")
end

inspection = PLUGIN.join("skills/dev-setup/scripts/inspect_tools.py")
if inspection.file?
  script = inspection.read
  assert(script.include?("CLAUDE_CONFIG_DIR"), "inspection must honor CLAUDE_CONFIG_DIR")
  assert(script.include?('".claude/skills"'), "inspection must search the Claude Code skill root")
  assert(script.include?("plugin:ouroboros:ouroboros"), "inspection must probe the plugin-scoped Ouroboros MCP server")
  assert(script.include?('"host_integration"'), "inspection must report host integration, not Codex integration")
  assert(!script.include?('"codex_integration"'), "inspection must not report a Codex integration component")
  assert(script.include?("registration_not_connected"), "inspection must classify registration from the Status line")
  # The Ouroboros MCP runtime derives from the plugin-scoped registration — the
  # Claude analog of upstream's isolated launcher — and the base-environment
  # doctor is never run for it.
  assert(script.include?("plugin_launcher_configured"), "inspection must derive the Ouroboros runtime from the plugin-scoped registration")
  assert(!script.include?('"mcp", "doctor"'), "inspection must not run ooo mcp doctor for the plugin launcher")
  # Mulgae and Gaori registrations are read from Claude Code configuration, never
  # probed through another host's CLI and never by starting the server.
  assert(script.include?("def inspect_claude_mcp("), "inspection must read Mulgae and Gaori MCP registrations from Claude Code configuration")
  assert(script.include?('".mcp.json"'), "inspection must read the project MCP registration file")
  # Upstream v0.1.16 moved the neutral-cwd probe into the project inspector as
  # `inspect_global_mcp_scope`, so the rewrite moved with it.
  assert(script.include?('return inspect_claude_mcp(name, root, executable, timeout_seconds)["global"]'), "the global MCP view must come from the configuration read")
  # The writing skills must be diagnosed against a root this host can reach;
  # upstream expects them in the shared cross-agent root and the Codex home.
  assert(!script.include?('".agents/skills/humanizer"'), "inspection must not expect Humanizer in another host's skill root")
  # Counting the two known calls would let a third writing skill upstream adds
  # ship against an unreachable root, so the totals must agree instead.
  assert(
    script.scan('expected_target=').length == script.scan('expected_target=skill_roots()[0]').length,
    "every writing skill must be expected in the Claude Code skill root"
  )
  # Upstream's Codex-based probe helpers stay defined but must have no callers:
  # each name may appear exactly once, at its `def`. `codex_version_from_output`
  # lost its only caller when the Mulgae registration probe was replaced, so it
  # joins the list.
  %w[mcp_registration_probe classify_mulgae_mcp_scope classify_gaori_mcp_scope effective_mcp_registration
     ouroboros_direct_launcher_matches ouroboros_isolated_launcher_matches effective_codex_skill_root
     codex_version_from_output].each do |helper|
    assert(script.scan("#{helper}(").length == 1, "inspection must not call the Codex-based #{helper}")
  end
  assert(!script.include?('"mcp", "get", "mulgae"') && !script.include?('"mcp", "get", "gaori"'), "inspection must not health-check Mulgae or Gaori through claude mcp get")
  # v0.1.15 added a presence-only trust table for the paired and third-party
  # skills. The forbidden scan already rejects the shared root, but the table
  # must positively resolve through `skill_roots()`, or a future entry could
  # reach an unreachable path some other way.
  assert(script.include?("trusted_root = skill_roots()[0]"), "the trusted skill table must resolve through the Claude Code skill root")
end

# The global inspector reaches the project inspector across skill directories, so
# the excluded per-home Ouroboros module must be gone from both its imports and
# its component set, and its user-scope MCP view must come from the project
# inspector, whose `inspect_global_mcp_scope` is the configuration read.
global_inspection = PLUGIN.join("skills/dev-setup-global/scripts/inspect_global_tools.py")
if global_inspection.file?
  script = global_inspection.read
  assert(!script.include?("inspect_ouroboros import"), "the global inspector must not import the excluded per-home module")
  assert(!script.include?("InvalidCodexHome"), "the global inspector must not handle a Codex-home error it cannot raise")
  assert(!script.include?("codex_home"), "the global inspector must not carry per-home options")
  assert(!script.include?('"aquarium-dev",'), "the global inspector must not offer the excluded development channel")
  # v0.1.17 made the production-status runtime a default component loaded from
  # the plugin-root `tools/`, which this edition does not ship; a surviving
  # loader would fail every unscoped global inspection.
  assert(!script.include?("aquarium-status"), "the global inspector must not offer the excluded production-status runtime")
  assert(!script.include?("tools/"), "the global inspector must not load anything from the excluded plugin-root tools/")
  assert(script.include?("inspector.inspect_ouroboros("), "the global inspector must keep the plugin-scoped Ouroboros probe")
  assert(script.include?("inspector.inspect_global_mcp_scope("), "the global inspector must take its user-scope MCP view from the project inspector's configuration read")
  assert(script.include?("inspector.skill_roots()[0]"), "the global inspector must diagnose canonical skills in the Claude Code skill root")
end

# --- generated scripts run -----------------------------------------------

# Scripts are rewritten by literal block substitution, so a drift that parses
# but cannot run is a realistic failure. `compile()` rather than `py_compile`:
# the latter writes `__pycache__` into the generated tree.
scripts = Pathname.glob(PLUGIN.join("**/*.py")).sort
assert(!scripts.empty?, "no Python was generated")
assert(
  system(
    "python3", "-c",
    "import sys, pathlib\nfor p in sys.argv[1:]: compile(pathlib.Path(p).read_text(), p, 'exec')",
    *scripts.map(&:to_s), out: File::NULL, err: File::NULL
  ),
  "generated Python does not compile"
)

# v0.1.17 moved the writing-skill target choice into two helpers that pick the
# other host's skill roots. They are deleted together with their last callers,
# and the arity gate cannot see a call to a name it does not know, so a
# reference that survived would fail only at run time.
%w[humanizer_skill_roots humanizer_expected_target].each do |helper|
  scripts.each do |path|
    assert(!path.read.include?(helper), "generated Python still references the deleted #{helper}: #{path.relative_path_from(PLUGIN)}")
  end
end

# --- manifests agree with upstream -----------------------------------------

manifest = JSON.parse(PLUGIN.join(".claude-plugin/plugin.json").read)
assert(manifest.fetch("skills") == "./skills/", "plugin manifest must point at ./skills/")
assert(manifest.fetch("license") == "MIT", "plugin license must be MIT")
assert(!manifest.fetch("description").include?("Codex"), "plugin description must not name Codex")

# Upstream removed its manifest icon and logo in v0.1.10 along with the PNGs
# they named; a reintroduced key would point at a file this artifact excludes.
plugin_metadata = manifest.fetch("metadata")
assert(!plugin_metadata.key?("icon") && !plugin_metadata.key?("logo"), "plugin metadata must not reference the logo assets upstream removed")
assert(plugin_metadata.fetch("brandColor").to_s.start_with?("#"), "plugin metadata lost its brand color")

if UPSTREAM_PLUGIN.directory?
  codex = JSON.parse(UPSTREAM_PLUGIN.join(".codex-plugin/plugin.json").read)
  %w[name version author homepage repository license keywords].each do |key|
    assert(manifest.fetch(key) == codex.fetch(key), "plugin manifest field `#{key}` diverges from upstream")
  end
end

marketplace = JSON.parse(ROOT.join(".claude-plugin/marketplace.json").read)
assert(marketplace.fetch("name") == "aquarium-for-claude", "marketplace name is incorrect")
assert(marketplace.dig("owner", "name").to_s != "", "marketplace requires an owner name")
entries = marketplace.fetch("plugins")
assert(entries.length == 1, "marketplace must publish exactly one plugin")
entry = entries.fetch(0)
assert(entry.fetch("name") == manifest.fetch("name"), "marketplace entry must match the plugin name")
assert(entry.fetch("source") == "./plugins/aquarium", "marketplace source path is incorrect")

# Claude Code rejects a plugin whose components are declared in both the
# manifest and the marketplace entry unless the entry sets `strict: true`.
COMPONENT_KEYS = %w[skills commands agents hooks mcpServers outputStyles].freeze
overlap = entry.keys & COMPONENT_KEYS
assert(
  overlap.empty? || entry["strict"] == true,
  "marketplace entry declares components #{overlap.inspect} that plugin.json also declares; " \
  "remove them or set strict: true"
)

# --- generated tree covers upstream ----------------------------------------

# `COPIED_DIRECTORIES` is an allowlist with no counterpart check, so `hooks/`
# appeared upstream and was dropped in silence until someone noticed.
#
# A plugin-root entry may also be excluded on purpose — v0.1.15 bundled a
# development channel under `tools/` and registered it from a `.mcp.json` that
# only the other host can read. Those names come from `scripts/sync.py`, so an
# exclusion retired there stops being tolerated here in the same commit.
excluded_plugin_root = sync_tables.fetch("EXCLUDED_PLUGIN_ROOT")
if UPSTREAM_PLUGIN.directory?
  upstream_directories = UPSTREAM_PLUGIN.children.select(&:directory?).map { |p| p.basename.to_s } -
                         [".codex-plugin"] - excluded_plugin_root
  upstream_directories.sort.each do |name|
    assert(PLUGIN.join(name).directory?, "generated plugin is missing upstream directory `#{name}/`")
  end
  # Nothing copies a top-level upstream file, so one that is neither excluded nor
  # deliberately copied would vanish exactly the way `hooks/` once did.
  # `reject(&:directory?)` rather than `select(&:file?)`, so this partitions the
  # plugin root with the directory scan above and a broken symlink cannot fall
  # between them.
  upstream_root_files = UPSTREAM_PLUGIN.children.reject(&:directory?).map { |p| p.basename.to_s } -
                        excluded_plugin_root
  assert(
    upstream_root_files.empty?,
    "upstream plugin-root files are neither copied nor excluded: #{upstream_root_files.sort.inspect}"
  )
  excluded_plugin_root.each do |name|
    assert(UPSTREAM_PLUGIN.join(name).exist?, "plugin-root exclusion targets `#{name}`, which upstream no longer ships")
    assert(!PLUGIN.join(name).exist?, "excluded plugin-root entry was generated: #{name}")
  end
end

# --- deliberate exclusions --------------------------------------------------

# `scripts/sync.py` drops upstream files that have no consumer in a Claude Code
# artifact (`assets/hero.png` is a 2.3 MB README banner). Assert both halves of
# each exclusion: the file is absent from the generated tree, and it still
# exists upstream, or the exclusion has silently stopped applying.
excluded = sync_manifest.fetch("excluded")
assert(excluded.include?("assets/hero.png"), "the upstream README banner must stay excluded")
# Upstream keeps the Dolgorae consumer contract only as dormant material for a
# separately named future route; no shipped route consumes it, so it stays
# excluded here.
assert(
  excluded.include?("references/dolgorae-review-contract.md"),
  "the Dolgorae consumer contract must stay excluded while no skill routes through it"
)
# The bundled `aquarium-dev` channel is excluded whole, so the shared contract
# that describes its producers, manager, and plugin MCP registration documents a
# lifecycle this edition does not have.
assert(
  excluded.include?("references/development-contract.md"),
  "the development-channel contract must stay excluded while the channel is not shipped"
)
# Ouroboros reaches this host as a plugin, so per-home rules, skills, and MCP
# registration are dimensions that do not exist here; the shrunken global
# component calls the project inspector's plugin-scoped probe instead.
assert(
  excluded.include?("skills/dev-setup-global/scripts/inspect_ouroboros.py"),
  "the per-home Ouroboros inspector must stay excluded"
)
generated_text = Pathname.glob(PLUGIN.join("**/*.{md,json,py,yaml}")).sort.reject { |p| p.basename.to_s == "sync-manifest.json" }
assert(
  sync_manifest.fetch("excluded_plugin_root").sort == excluded_plugin_root.sort,
  "sync manifest plugin-root exclusions #{sync_manifest.fetch('excluded_plugin_root').inspect} " \
  "do not match scripts/sync.py #{excluded_plugin_root.inspect}"
)
excluded.each do |relative|
  assert(!PLUGIN.join(relative).exist?, "excluded file was generated: #{relative}")
  assert(UPSTREAM_PLUGIN.join(relative).file?, "exclusion targets a file upstream no longer ships: #{relative}") if UPSTREAM_PLUGIN.directory?
  assert(!sync_manifest.fetch("files").key?(relative), "excluded file is listed in the sync manifest: #{relative}")
  basename = File.basename(relative)
  generated_text.each do |path|
    assert(!path.read.include?(basename), "generated text references the excluded #{relative}: #{path.relative_path_from(PLUGIN)}")
  end
end

# A whole skill is excluded by name: `EXCLUDED_FILES` cannot express it, because
# generation refuses a skill directory without `SKILL.md` and a basename check on
# `SKILL.md` would match every skill. v0.1.17's `status` reports a ledger whose
# runtime lives under the excluded plugin-root `tools/`.
excluded_skills = sync_tables.fetch("EXCLUDED_SKILLS")
assert(
  sync_manifest.fetch("excluded_skills").sort == excluded_skills.sort,
  "sync manifest skill exclusions #{sync_manifest.fetch('excluded_skills').inspect} " \
  "do not match scripts/sync.py #{excluded_skills.inspect}"
)
excluded_skills.each do |name|
  assert(!PLUGIN.join("skills", name).exist?, "excluded skill was generated: #{name}")
  assert(UPSTREAM_PLUGIN.join("skills", name, "SKILL.md").file?, "skill exclusion targets a skill upstream no longer ships: #{name}") if UPSTREAM_PLUGIN.directory?
  assert(sync_manifest.fetch("files").keys.none? { |key| key.start_with?("skills/#{name}/") }, "excluded skill is listed in the sync manifest: #{name}")
  invocation = /aquarium:#{Regexp.escape(name)}(?![A-Za-z0-9_-])/
  generated_text.each do |path|
    text = path.read
    assert(
      !text.match?(invocation) && !text.include?("skills/#{name}/") && !text.include?("../#{name}/"),
      "generated text references the excluded skill #{name}: #{path.relative_path_from(PLUGIN)}"
    )
  end
end

# An excluded plugin-root directory hides everything under it, including a tool
# upstream adds later: v0.1.17's `tools/aquarium-status` arrived that way with no
# abort. Generated text must never point into one of its children.
if UPSTREAM_PLUGIN.directory?
  excluded_plugin_root.each do |name|
    source = UPSTREAM_PLUGIN.join(name)
    next unless source.directory?

    source.children.map { |child| "#{name}/#{child.basename}" }.each do |needle|
      generated_text.each do |path|
        assert(!path.read.include?(needle), "generated text references the excluded #{needle}: #{path.relative_path_from(PLUGIN)}")
      end
    end
  end
end

# A name-based exclusion only catches the file it names; a size guard catches
# the next multi-megabyte asset upstream adds under any name.
Pathname.glob(PLUGIN.join("**/*")).select(&:file?).reject { |p| p.to_s.include?("__pycache__/") }.sort.each do |path|
  assert(path.size <= 1_000_000, "generated file exceeds 1 MB: #{path.relative_path_from(PLUGIN)}")
end

# Every generated file is recorded, so a partial write cannot pass as complete.
# Bytecode caches are ignored by Git and appear whenever a bundled script is
# imported locally; they are not part of the artifact.
Pathname.glob(PLUGIN.join("**/*")).select(&:file?).sort.each do |path|
  relative = path.relative_path_from(PLUGIN).to_s
  next if relative == "sync-manifest.json" || relative.include?("__pycache__/")

  assert(sync_manifest.fetch("files").key?(relative), "generated file is missing from the sync manifest: #{relative}")
end

# --- roadmap commit hook ----------------------------------------------------

hooks_path = PLUGIN.join("hooks/hooks.json")
gate_path = PLUGIN.join("hooks/task_commit_gate.py")
assert(hooks_path.file? && gate_path.file?, "the roadmap commit hook was not generated")

pre_tool_use = JSON.parse(hooks_path.read).fetch("hooks").fetch("PreToolUse")
assert(pre_tool_use.length == 1, "the commit hook must register exactly one PreToolUse matcher")
assert(pre_tool_use.fetch(0).fetch("matcher") == "^Bash$", "the commit hook must match Bash only")

# Claude Code expands `CLAUDE_PLUGIN_ROOT`. Under the Codex spelling the shell
# expands nothing, `python3` cannot open `/hooks/task_commit_gate.py`, and it
# exits 2 — which PreToolUse reads as deny. Every Bash call would be blocked, so
# assert the correct spelling positively and the wrong one negatively.
hook_command = pre_tool_use.fetch(0).fetch("hooks").fetch(0).fetch("command")
assert(
  hook_command == 'python3 "${CLAUDE_PLUGIN_ROOT}/hooks/task_commit_gate.py"',
  "the commit hook must resolve its script through CLAUDE_PLUGIN_ROOT: #{hook_command}"
)

gate = gate_path.read
assert(gate.include?("/aquarium:task-commit"), "the commit hook must name the Claude invocation form")
assert(gate.include?("permissionDecision"), "the commit hook must use the PreToolUse permission protocol")
assert(!gate.match?(%r{https?://}), "the commit hook must stay local")

# `hooks/hooks.json` is loaded automatically from the plugin root. Declaring the
# key as well would shadow the default folder and break the overlap rule above.
assert(!manifest.key?("hooks"), "plugin manifest must not declare hooks; hooks/hooks.json is automatic")

# --- bundled subagents -------------------------------------------------------

# `agents/` is likewise discovered from the plugin root. The files come from
# `additions/`, have no upstream counterpart, and are the one place this
# artifact ships behaviour of its own, so their contract is asserted here.
assert(!manifest.key?("agents"), "plugin manifest must not declare agents; agents/ is automatic")
additions = sync_manifest.fetch("additions")
additions.each do |relative|
  assert(PLUGIN.join(relative).file?, "recorded addition was not generated: #{relative}")
  assert(ROOT.join("additions", relative).file?, "recorded addition has no source under additions/: #{relative}")
end

# The repository-state inspector is this edition's no-mutation baseline for
# Subagent Review. Upstream shipped it beside `orca-review` and removed it in
# v0.1.14; it moved with its skill when v0.1.20 renamed `independent-review`
# to `subagent-review` without an alias.
INSPECTOR = "skills/subagent-review/scripts/inspect_repository_state.py"
assert(additions.include?(INSPECTOR), "the repository-state inspector must be a recorded addition")
subagent_review = PLUGIN.join("skills/subagent-review/SKILL.md").read
assert(
  subagent_review.include?("scripts/inspect_repository_state.py") && subagent_review.include?("--snapshot") && subagent_review.include?("--compare"),
  "subagent review must still take and compare the repository-state baseline"
)
assert(subagent_review.include?("target.target_digest"), "subagent review must compare only the target digest")
assert(
  subagent_review.include?("`aquarium:subagent-reviewer`") && PLUGIN.join("agents/subagent-reviewer.md").file?,
  "subagent review must dispatch the bundled reviewer it ships"
)
assert(
  !subagent_review.include?("../independent-review/") && !subagent_review.include?("../orca-review/"),
  "subagent review must not reach into a retired skill directory"
)

# `fable` is deliberately absent: Opus is the baseline for every delegated role
# here, and Fable is used only when the user explicitly asks, because it can bill
# usage credits and a non-interactive run bills them without asking.
AGENT_MODELS = %w[inherit opus sonnet haiku].freeze
EDITING_TOOLS = %w[Edit Write NotebookEdit].freeze

Pathname.glob(PLUGIN.join("agents/*.md")).sort.each do |path|
  relative = path.relative_path_from(PLUGIN).to_s
  assert(additions.include?(relative), "agent is not a recorded addition: #{relative}")
  frontmatter = path.read.match(/\A---\n(.*?)\n---\n/m)
  assert(frontmatter, "agent lacks frontmatter: #{relative}")
  agent = YAML.safe_load(frontmatter[1], aliases: false)
  assert(agent.fetch("name") == path.basename(".md").to_s, "agent name must match its filename: #{relative}")
  assert(!agent.fetch("description").to_s.strip.empty?, "agent lacks a description: #{relative}")
  assert(AGENT_MODELS.include?(agent.fetch("model")), "agent model must be one of #{AGENT_MODELS.join(', ')}: #{relative}")
  # Claude Code ignores these keys on plugin subagents — it only logs a warning,
  # and `claude plugin validate --strict` stays silent — so a declared key would
  # claim a restriction or behaviour the agent does not have. `initialPrompt` is
  # documented as "Ignored for plugin subagents".
  %w[permissionMode hooks mcpServers initialPrompt].each do |key|
    assert(!agent.key?(key), "plugin agents cannot set #{key}; Claude Code ignores it: #{relative}")
  end
  tools = agent.fetch("tools").to_s.split(",").map(&:strip)
  assert(!tools.empty? && (tools & EDITING_TOOLS).empty?, "reviewer agent must carry a tool allowlist without editing tools: #{relative}")
end

# --- managed Podway procedures ----------------------------------------------

# The integration contract requires the installed copies to be byte-identical to
# these sources, so the procedure IDs must survive transformation untouched.
if UPSTREAM_PLUGIN.directory?
  Pathname.glob(PLUGIN.join("assets/podway/procedures/*.yaml")).sort.each do |path|
    relative = path.relative_path_from(PLUGIN)
    assert(
      path.binread == UPSTREAM_PLUGIN.join(relative).binread,
      "managed Podway procedure must be byte-identical to upstream: #{relative}"
    )
    assert(
      YAML.safe_load(path.read, aliases: false).fetch("id") == path.basename(".yaml").to_s,
      "managed Podway procedure id must match its filename: #{relative}"
    )
  end
end

# --- adaptive material ships verbatim ----------------------------------------

# v0.1.20's known sources pin the bundled Procedures by SHA-256, and its
# capability signatures and operation contracts pin canonical JSON, so the
# plugin-root `shared/` helpers and the `assets/adaptive/` and `assets/schemas/`
# data ship verbatim: a rewrite would break a digest nothing regenerates.
# `shared/` carries no host text. Each tree must hold exactly upstream's files,
# so a file added or dropped on either side fails, not only one that changed.
VERBATIM_TREES = %w[shared assets/adaptive assets/schemas].freeze

# Bytecode caches appear whenever a bundled script is imported locally and are
# not part of the artifact.
def tree_files(root, directory)
  Pathname.glob(root.join(directory, "**/*")).select(&:file?)
          .reject { |path| path.to_s.include?("__pycache__/") }
          .map { |path| path.relative_path_from(root).to_s }.sort
end

if UPSTREAM_PLUGIN.directory?
  VERBATIM_TREES.each do |directory|
    upstream_files = tree_files(UPSTREAM_PLUGIN, directory)
    generated_files = tree_files(PLUGIN, directory)
    assert(!upstream_files.empty?, "upstream no longer ships #{directory}/, which this edition copies verbatim")
    assert(
      generated_files == upstream_files,
      "generated #{directory}/ must hold exactly upstream's files: #{((generated_files - upstream_files) | (upstream_files - generated_files)).inspect}"
    )
    generated_files.each do |relative|
      assert(
        PLUGIN.join(relative).binread == UPSTREAM_PLUGIN.join(relative).binread,
        "#{directory}/ must be byte-identical to upstream: #{relative}"
      )
    end
  end
end

# `shared/` imports these names from `skills/dev-setup/scripts/inspect_tools.py`
# and `skills/goal-evaluator/scripts/ordinary_assignment.py`, and
# `inspect_tools.py` imports `shared/` back, so a script rule that renamed one
# would break the adaptive helpers with no parse or arity failure.
ADAPTIVE_COUPLINGS = {
  "skills/dev-setup/scripts/inspect_tools.py" => [
    "PODWAY_PRIOR_CANONICAL_SHA256 = {", "def podway_v025_workaround_bytes(", "def resolve_repository(",
    "def inspect_selected_podway(", "class InspectionError"
  ],
  "skills/goal-evaluator/scripts/ordinary_assignment.py" => ["def prepare(", "class AssignmentError"]
}.freeze
ADAPTIVE_COUPLINGS.each do |relative, needles|
  path = PLUGIN.join(relative)
  assert(path.file?, "the adaptive helpers in shared/ import from #{relative}, which was not generated")
  script = path.read
  needles.each do |needle|
    assert(script.include?(needle), "#{relative} must still contain `#{needle}`; the adaptive helpers in shared/ import it")
  end
end

# --- README agrees with the generated artifact -----------------------------

# The README's override table is the public explanation of every file that
# diverges from upstream; it must name exactly the overrides the sync applied.
readme = ROOT.join("README.md").read
# The path prefixes are the generated tree's own top-level directories, so a
# skills-table row (a bare skill name, no slash) can never be mistaken for one.
override_rows = readme.scan(%r{^\| `((?:skills|references|agents|hooks|assets)/[^`]+)` \| }).flatten.sort
assert(
  override_rows == sync_manifest.fetch("overrides").sort,
  "README override table #{override_rows.inspect} does not match the applied overrides #{sync_manifest.fetch('overrides').inspect}"
)

# The Skills table is the README's public index of what the plugin ships. A
# skill upstream adds arrives through generation with no prose of its own —
# v0.1.16's `mulgae-review` did — so every generated top-level skill must have
# a row. The seven `task-*` phase skills are described once in the prose beside
# `task-handler` and are exempt, and each exempted name must still be a
# generated skill so the exemption cannot outlive a rename.
PHASE_SKILLS = %w[task-plan task-implement task-refine task-verify task-document task-review task-close].freeze
generated_skills = skill_paths.map { |p| p.dirname.basename.to_s }
assert((PHASE_SKILLS - generated_skills).empty?, "phase-skill exemptions name skills that are not generated: #{(PHASE_SKILLS - generated_skills).inspect}")
skill_rows = readme.scan(/^\| `([a-z0-9-]+)` \| /).flatten
missing_rows = generated_skills - PHASE_SKILLS - skill_rows
assert(missing_rows.empty?, "README Skills table lacks a row for generated skills: #{missing_rows.inspect}")
# The reverse direction keeps an excluded or renamed skill from staying listed
# as something the plugin ships.
stale_rows = skill_rows - generated_skills
assert(stale_rows.empty?, "README Skills table lists skills that are not generated: #{stale_rows.inspect}")

# --- documentation convention ----------------------------------------------

# The convention is this repository's, so it is asserted on the Markdown this
# repository writes: its own documents, the full-file overrides, and the
# host-only additions. The generated tree is excluded because most of it is
# upstream's prose under upstream's style — v0.1.15 shipped two hard-wrapped
# references — and the part this repository does author lands there byte for
# byte from `overrides/` and `additions/`, which are checked at the source. The
# one authored thing left unchecked is a substitution's replacement text, so
# keep a multi-line replacement to one prose line per paragraph by hand.
def structural?(line)
  # Match the stripped line: an indented sub-bullet is still structural, and
  # classifying it as prose makes two adjacent ones look hard-wrapped.
  stripped = line.strip
  stripped.empty? || stripped.match?(/\A(?:\#{1,6}\s|[-*+]\s|\d+\.\s|>|\||<)/)
end

authored_markdown = Pathname.glob(ROOT.join("**/*.md")).reject do |path|
  path.to_s.include?("/upstream/") || path.to_s.start_with?(PLUGIN.to_s + File::SEPARATOR)
end
authored_markdown.sort.each do |path|
  fenced = false
  in_frontmatter = false
  previous_prose = false
  path.read.lines.each_with_index do |line, index|
    stripped = line.chomp
    if index.zero? && stripped == "---"
      in_frontmatter = true
      next
    end
    if in_frontmatter
      in_frontmatter = false if stripped == "---"
      next
    end
    if stripped.start_with?("```")
      fenced = !fenced
      previous_prose = false
      next
    end
    next if fenced

    prose = !structural?(stripped)
    if prose && previous_prose
      failures << "#{path.relative_path_from(ROOT)}:#{index + 1}: hard-wrapped prose"
    end
    previous_prose = prose
  end
end

assert(failures.empty?, "hard-wrapped prose found:\n#{failures.join("\n")}")

puts "validated #{skill_paths.length} generated skills and Claude artifact invariants"
