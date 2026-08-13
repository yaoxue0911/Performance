# JMeter Scenario Fragments, Validator Contract, and 5.6.3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic multi-file Scenario assembly, require finite validator PASS/FAIL outcomes, and make JMeter 5.6.3 the single supported generated metadata version.

**Architecture:** A new standalone assembler recursively resolves safe `$include` nodes into one existing-schema Scenario JSON, leaving `generate_jmx_tree.py --scenario` backward-compatible. Validator instructions define a finite initial-review and scoped-revalidation contract. Documentation and regression tests enforce JMeter 5.6.3.

**Tech Stack:** Python 3 standard library, JSON, `unittest`, Apache JMeter JMX XML.

## Global Constraints

- Keep `generate_jmx_tree.py --scenario FILE --output FILE --validate` backward-compatible.
- Use only Python standard-library dependencies.
- Resolve include paths relative to the including file and keep them under the manifest root.
- Reject missing files, cycles, path traversal, malformed include objects, and invalid final Scenario structure.
- Generated JMX root metadata must be `jmeter="5.6.3"`.
- Do not modify or restore unrelated worktree changes.
- Do not execute a JMX or access a target environment.

---

### Task 1: Add failing assembler tests

**Files:**
- Create: `AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/tests/test_assemble_scenario.py`

**Interfaces:**
- Consumes: CLI contract `assemble_scenario.py --manifest PATH --output PATH --validate`.
- Produces: executable acceptance tests for recursive include assembly and safety errors.

- [ ] Test object replacement, array splicing order, nested includes, missing file, include cycle, root escape, mixed `$include` fields, invalid final `thread_groups`, and end-to-end generation with `generate_jmx_tree.py --validate`.
- [ ] Run `python3 -m unittest ...test_assemble_scenario -v` and confirm failure because `assemble_scenario.py` does not exist.

### Task 2: Implement the Scenario assembler

**Files:**
- Create: `AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/assemble_scenario.py`
- Test: `AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/tests/test_assemble_scenario.py`

**Interfaces:**
- `assemble(manifest_path: Path) -> dict`
- `resolve(value, source_path, root_dir, stack) -> object | list`
- CLI writes formatted UTF-8 JSON only after complete successful assembly.

- [ ] Implement recursive object replacement and list splicing using an internal expansion marker rather than writing partial output.
- [ ] Enforce canonical resolved paths within `root_dir`, exact include-object shape, existence, JSON validity, and cycle detection with an include chain in errors.
- [ ] Under `--validate`, require a dictionary root, non-empty `thread_groups`, and non-empty `children` for every thread group.
- [ ] Write output atomically using a temporary file in the destination directory followed by `Path.replace()`.
- [ ] Run assembler tests and confirm all pass.

### Task 3: Document and enforce the fragment workflow

**Files:**
- Modify: `AI Jmx Generator/.agents/skills/jmeter-loader-skills/SKILL.md`
- Modify: `AI Jmx Generator/.agents/skills/jmeter-loader-skills/references/scenario-schema.md`

**Interfaces:**
- Consumes: assembler CLI from Task 2.
- Produces: mandatory workflow selection and fragment schema instructions for future JMX agents.

- [ ] Add the threshold: prefer fragments when the full Scenario is expected to exceed 30 KB or 20 samplers.
- [ ] Require transaction/business-unit fragments, per-fragment `json.tool`, assembly validation, no remaining `$include`, and node/sampler count reconciliation before JMX generation.
- [ ] State that an oversized patch failure must switch to fragments instead of retrying the same complete patch.
- [ ] Add one concise manifest/include example and exact CLI command.

### Task 4: Add the validator terminal contract

**Files:**
- Modify: `AI Jmx Generator/.codex/agents/jmx_validator.toml`
- Modify: `AI Jmx Generator/.agents/skills/jmeter-loader-skills/references/validation-rules.md`

**Interfaces:**
- Consumes: initial validation or a list of prior blockers.
- Produces: `Verdict`, blocker/warning counts, completed checklist, and evidence-backed findings.

- [ ] Require the fixed terminal format from the design.
- [ ] Require the first review to collect all findings in one pass and return PASS immediately when blocker count is zero.
- [ ] Limit revalidation to prior blockers plus JSON/XML, counts, load model, assertions, listeners, and multipart regression checks.
- [ ] Forbid progress-only responses from replacing the terminal result.
- [ ] Keep the validator read-only: return the terminal result to the caller instead of writing a report; classify non-5.6.3 metadata as warning at most.

### Task 5: Make JMeter 5.6.3 consistent

**Files:**
- Modify: `AI Jmx Generator/.agents/skills/jmeter-loader-skills/SKILL.md`
- Modify: `AI Jmx Generator/.agents/skills/jmeter-loader-skills/references/validation-rules.md`
- Modify: `AI Jmx Generator/.agents/skills/jmeter-loader-skills/references/jmx_structure.md`
- Verify: `AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/generate_jmx_tree.py`
- Verify: `AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/tests/test_generate_jmx_tree.py`

**Interfaces:**
- Consumes: generated JMX XML root.
- Produces: consistent 5.6.3 metadata and documentation.

- [ ] Replace active `5.4.1` documentation with `5.6.3`.
- [ ] Keep the generator's current `jmeter="5.6.3"` output without adding a version-specific regression assertion or validator blocker.
- [ ] Scan the active skill directory for `5.4.1` and require zero matches.

### Task 6: Run the full verification suite

**Files:**
- Test: all files under `AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/tests/`

**Interfaces:**
- Consumes: Tasks 1–5.
- Produces: reproducible final verification evidence.

- [ ] Run `python3 -m unittest discover -s "AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/tests" -v` with zero failures/errors.
- [ ] Assemble a temporary fragmented sample, generate a temporary JMX using `--validate`, parse its XML, and confirm root metadata 5.6.3.
- [ ] Run `python3 -m py_compile` on both generator scripts.
- [ ] Run the skill-folder validator if available; otherwise verify YAML frontmatter, referenced files, and command paths manually.
- [ ] Review the diff to ensure no unrelated user changes were altered.
