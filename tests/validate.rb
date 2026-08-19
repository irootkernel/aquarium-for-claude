#!/usr/bin/env ruby
# frozen_string_literal: true

# Validates the invariants that are specific to the Claude Code artifact.
#
# Upstream owns the prose contract and already validates it in its own CI, so
# this file deliberately does not re-assert skill wording. It checks only what
# the transformation is responsible for: invocation gating, host-neutral text,
# manifest agreement, and freshness against the pinned upstream.

require "json"
require "pathname"
require "yaml"

ROOT = Pathname.new(__dir__).parent
PLUGIN = ROOT.join("plugins/root-kernel")
UPSTREAM_PLUGIN = ROOT.join("upstream/plugins/root-kernel")

failures = []

def assert(condition, message)
  return if condition

  warn "error: #{message}"
  exit 1
end

# --- generated tree exists -------------------------------------------------

assert(PLUGIN.directory?, "plugins/root-kernel/ has not been generated; run scripts/sync.py")

skill_paths = Pathname.glob(PLUGIN.join("skills/*/SKILL.md")).sort
assert(!skill_paths.empty?, "no skills were generated")

sync_manifest = JSON.parse(PLUGIN.join("sync-manifest.json").read)
assert(sync_manifest.dig("upstream", "commit").to_s.length == 40, "sync manifest lacks an upstream commit")

# --- invocation gating mirrors the upstream sidecar ------------------------

ALLOWED_FRONTMATTER_KEYS = %w[description disable-model-invocation name].freeze

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
end

if UPSTREAM_PLUGIN.directory?
  upstream_skills = Pathname.glob(UPSTREAM_PLUGIN.join("skills/*/SKILL.md")).map { |p| p.dirname.basename.to_s }.sort
  generated = skill_paths.map { |p| p.dirname.basename.to_s }.sort
  assert(generated == upstream_skills, "generated skills do not match upstream: #{(generated - upstream_skills) | (upstream_skills - generated)}")
end

# --- host-neutral generated text -------------------------------------------

FORBIDDEN_TEXT = ["$root-kernel:", "$lore-", "$orca-cli", "request_user_input", "--agent codex", "Codex"].freeze

Pathname.glob(PLUGIN.join("**/*.md")).sort.each do |path|
  text = path.read
  FORBIDDEN_TEXT.each do |needle|
    assert(!text.include?(needle), "generated text contains `#{needle}`: #{path.relative_path_from(PLUGIN)}")
  end
end

assert(
  skill_paths.any? { |path| path.read.include?("/root-kernel:") },
  "generated skills never reference the Claude invocation form"
)

inspection = PLUGIN.join("skills/dev-setup/scripts/inspect_tools.py")
if inspection.file?
  script = inspection.read
  assert(script.include?("CLAUDE_CONFIG_DIR"), "inspection must honor CLAUDE_CONFIG_DIR")
  assert(script.include?('".claude/skills"'), "inspection must search the Claude Code skill root")
end

# --- manifests agree with upstream -----------------------------------------

manifest = JSON.parse(PLUGIN.join(".claude-plugin/plugin.json").read)
assert(manifest.fetch("skills") == "./skills/", "plugin manifest must point at ./skills/")
assert(manifest.fetch("license") == "MIT", "plugin license must be MIT")
assert(!manifest.fetch("description").include?("Codex"), "plugin description must not name Codex")

if UPSTREAM_PLUGIN.directory?
  codex = JSON.parse(UPSTREAM_PLUGIN.join(".codex-plugin/plugin.json").read)
  %w[name version author homepage repository license keywords].each do |key|
    assert(manifest.fetch(key) == codex.fetch(key), "plugin manifest field `#{key}` diverges from upstream")
  end
end

marketplace = JSON.parse(ROOT.join(".claude-plugin/marketplace.json").read)
assert(marketplace.fetch("name") == "root-kernel-dev-claude-skills", "marketplace name is incorrect")
assert(marketplace.dig("owner", "name").to_s != "", "marketplace requires an owner name")
entries = marketplace.fetch("plugins")
assert(entries.length == 1, "marketplace must publish exactly one plugin")
entry = entries.fetch(0)
assert(entry.fetch("name") == manifest.fetch("name"), "marketplace entry must match the plugin name")
assert(entry.fetch("source") == "./plugins/root-kernel", "marketplace source path is incorrect")

# Claude Code rejects a plugin whose components are declared in both the
# manifest and the marketplace entry unless the entry sets `strict: true`.
COMPONENT_KEYS = %w[skills commands agents hooks mcpServers outputStyles].freeze
overlap = entry.keys & COMPONENT_KEYS
assert(
  overlap.empty? || entry["strict"] == true,
  "marketplace entry declares components #{overlap.inspect} that plugin.json also declares; " \
  "remove them or set strict: true"
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
