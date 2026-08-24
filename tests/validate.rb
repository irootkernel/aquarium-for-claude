#!/usr/bin/env ruby
# frozen_string_literal: true

# Validates the invariants that are specific to the Claude Code artifact.
#
# Upstream owns the prose contract and already validates it in its own CI, so
# this file deliberately does not re-assert skill wording. It checks only what
# the transformation is responsible for: invocation gating, host-neutral text,
# manifest agreement, deliberate exclusions, runnable generated scripts, and
# freshness against the pinned upstream.

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
  assert(metadata.fetch("description").include?("Use when"), "description lacks trigger: #{name}")

  # The upstream Codex sidecar is the single source of truth for invocation
  # policy. If these ever disagree, a mutating skill could fire without the
  # user asking for it, so the relationship is asserted as a biconditional.
  sidecar_path = UPSTREAM_PLUGIN.join("skills/#{name}/agents/openai.yaml")
  next unless sidecar_path.file?

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
  upstream_skills = Pathname.glob(UPSTREAM_PLUGIN.join("skills/*/SKILL.md")).map { |p| p.dirname.basename.to_s }.sort
  generated = skill_paths.map { |p| p.dirname.basename.to_s }.sort
  assert(generated == upstream_skills, "generated skills do not match upstream: #{(generated - upstream_skills) | (upstream_skills - generated)}")
end

# --- host-neutral generated text -------------------------------------------

FORBIDDEN_TEXT = ["$aquarium:", "$use-", "$lore-", "$orca-cli", "request_user_input",
                  "--agent codex", "~/.agents/skills", "${PLUGIN_ROOT}", ".codex/config",
                  "Codex"].freeze

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
  found = path.read.scan(SIGIL).uniq.sort
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

# `FORBIDDEN` in scripts/sync.py and `FORBIDDEN_TEXT` here are maintained by
# hand; a needle added to one and not the other halves the guard. Comparing the
# two as sets closes both directions: a Ruby-only needle would let generation
# write text CI then rejects, and a Python-only needle would leave the artifact
# unguarded whenever the generated tree is checked without regenerating it.
# `~/.agents/skills` was Python-only until this check existed.
#
# The needles are read by parsing scripts/sync.py rather than executing it, and
# through a real Python parser rather than a regex, so a literal carrying a
# quote or a backslash cannot silently drop out of the comparison.
EXTRACT_FORBIDDEN = <<~PYTHON
  import ast, json, pathlib

  tree = ast.parse(pathlib.Path("scripts/sync.py").read_text())
  for node in tree.body:
      target = getattr(node, "target", None)
      if getattr(target, "id", None) == "FORBIDDEN":
          print(json.dumps([pair.elts[0].value for pair in node.value.elts]))
          break
  else:
      raise SystemExit("FORBIDDEN not found in scripts/sync.py")
PYTHON

sync_needles = begin
  raw = IO.popen(["python3", "-c", EXTRACT_FORBIDDEN], chdir: ROOT.to_s, &:read)
  assert($?.success?, "could not read FORBIDDEN from scripts/sync.py")
  JSON.parse(raw).to_set
end

assert(
  sync_needles == FORBIDDEN_TEXT.to_set,
  "forbidden needles disagree: only in scripts/sync.py #{(sync_needles - FORBIDDEN_TEXT.to_set).to_a.inspect}, " \
  "only in tests/validate.rb #{(FORBIDDEN_TEXT.to_set - sync_needles).to_a.inspect}"
)

assert(
  skill_paths.any? { |path| path.read.include?("/aquarium:") },
  "generated skills never reference the Claude invocation form"
)

inspection = PLUGIN.join("skills/dev-setup/scripts/inspect_tools.py")
if inspection.file?
  script = inspection.read
  assert(script.include?("CLAUDE_CONFIG_DIR"), "inspection must honor CLAUDE_CONFIG_DIR")
  assert(script.include?('".claude/skills"'), "inspection must search the Claude Code skill root")
  assert(script.include?("plugin:ouroboros:ouroboros"), "inspection must probe the plugin-scoped Ouroboros MCP server")
  assert(script.include?('"host_integration"'), "inspection must report host integration, not Codex integration")
  assert(!script.include?('"codex_integration"'), "inspection must not report a Codex integration component")
  assert(script.include?("registration_not_connected"), "inspection must classify registration from the Status line")
  # Mulgae and Gaori registrations are read from Claude Code configuration, never
  # probed through another host's CLI and never by starting the server.
  assert(script.include?("def inspect_claude_mcp("), "inspection must read Mulgae and Gaori MCP registrations from Claude Code configuration")
  assert(script.include?('".mcp.json"'), "inspection must read the project MCP registration file")
  # Upstream's Codex-based probe helpers stay defined but must have no callers:
  # each name may appear exactly once, at its `def`.
  %w[mcp_registration_probe classify_mulgae_mcp_scope classify_gaori_mcp_scope effective_mcp_registration].each do |helper|
    assert(script.scan("#{helper}(").length == 1, "inspection must not call the Codex-based #{helper}")
  end
  assert(!script.include?('"mcp", "get", "mulgae"') && !script.include?('"mcp", "get", "gaori"'), "inspection must not health-check Mulgae or Gaori through claude mcp get")
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
if UPSTREAM_PLUGIN.directory?
  upstream_directories = UPSTREAM_PLUGIN.children.select(&:directory?).map { |p| p.basename.to_s } - [".codex-plugin"]
  upstream_directories.sort.each do |name|
    assert(PLUGIN.join(name).directory?, "generated plugin is missing upstream directory `#{name}/`")
  end
end

# --- deliberate exclusions --------------------------------------------------

# `scripts/sync.py` drops upstream files that have no consumer in a Claude Code
# artifact (`assets/hero.png` is a 2.3 MB README banner). Assert both halves of
# each exclusion: the file is absent from the generated tree, and it still
# exists upstream, or the exclusion has silently stopped applying.
excluded = sync_manifest.fetch("excluded")
assert(excluded.include?("assets/hero.png"), "the upstream README banner must stay excluded")
generated_text = Pathname.glob(PLUGIN.join("**/*.{md,json,py,yaml}")).sort.reject { |p| p.basename.to_s == "sync-manifest.json" }
excluded.each do |relative|
  assert(!PLUGIN.join(relative).exist?, "excluded file was generated: #{relative}")
  assert(UPSTREAM_PLUGIN.join(relative).file?, "exclusion targets a file upstream no longer ships: #{relative}") if UPSTREAM_PLUGIN.directory?
  assert(!sync_manifest.fetch("files").key?(relative), "excluded file is listed in the sync manifest: #{relative}")
  basename = File.basename(relative)
  generated_text.each do |path|
    assert(!path.read.include?(basename), "generated text references the excluded #{relative}: #{path.relative_path_from(PLUGIN)}")
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

# --- README agrees with the generated artifact -----------------------------

# The README's override table is the public explanation of every file that
# diverges from upstream; it must name exactly the overrides the sync applied.
readme = ROOT.join("README.md").read
override_rows = readme.scan(/^\| `(skills\/[^`]+)` \| /).flatten.sort
assert(
  override_rows == sync_manifest.fetch("overrides").sort,
  "README override table #{override_rows.inspect} does not match the applied overrides #{sync_manifest.fetch('overrides').inspect}"
)

# --- documentation convention ----------------------------------------------

def structural?(line)
  # Match the stripped line: an indented sub-bullet is still structural, and
  # classifying it as prose makes two adjacent ones look hard-wrapped.
  stripped = line.strip
  stripped.empty? || stripped.match?(/\A(?:\#{1,6}\s|[-*+]\s|\d+\.\s|>|\||<)/)
end

Pathname.glob(ROOT.join("**/*.md")).reject { |p| p.to_s.include?("/upstream/") }.sort.each do |path|
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
