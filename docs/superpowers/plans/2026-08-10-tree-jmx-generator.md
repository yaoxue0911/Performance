# Tree JMX Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new JSON-driven JMX generator that preserves nested JMeter controller/sampler structure, without modifying `generate_jmx.py`, and switch the JMeter skill to the new generator.

**Architecture:** `generate_jmx_tree.py` reads a scenario containing a test plan and one or more thread groups. A recursive renderer converts every child node into a JMeter element followed by its paired `hashTree`; controller children and sampler-scoped processors/assertions are rendered into that paired tree. Independent XML factories live in `jmx_tree_components.py`; the deprecated `generate_jmx.py` is neither imported nor required.

**Tech Stack:** Python 3 standard library, `xml.etree.ElementTree`, JSON, `unittest`.

## Global Constraints

- Do not modify `scripts/generate_jmx.py`.
- Dynamic generation uses only `scripts/generate_jmx_tree.py --scenario ... --output ...`.
- Empty controller children, unknown node types, and malformed scenario structures fail with actionable errors.
- Login is represented explicitly as an `once_only_controller` node containing the complete login flow.

---

### Task 1: Tree renderer and CLI

**Files:**
- Create: `AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/generate_jmx_tree.py`
- Create: `AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/jmx_tree_components.py`
- Test: `AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/tests/test_generate_jmx_tree.py`

**Interfaces:**
- Consumes: JSON object with `test_plan` and non-empty `thread_groups`.
- Produces: `build_jmx(scenario: dict) -> str`, `load_scenario(path: str) -> dict`, and CLI exit status `0` on success.

- [ ] Write tests for nested Once Only/Transaction placement, sampler-scoped assertions, validation failures, and CLI output.
- [ ] Run the test file and confirm failure because `generate_jmx_tree.py` is absent.
- [ ] Implement schema validation, component dispatch, recursive paired-`hashTree` rendering, and JSON-only CLI.
- [ ] Run the test file and confirm all cases pass.

### Task 2: Skill migration

**Files:**
- Modify: `AI Jmx Generator/.agents/skills/jmeter-loader-skills/SKILL.md`

**Interfaces:**
- Consumes: user-approved text architecture and analyzed SAZ data.
- Produces: a scenario JSON plus JMX generated exclusively by `generate_jmx_tree.py`.

- [ ] Replace flat `generate_jmx.py --http-sampler` instructions with the recursive scenario contract.
- [ ] Require complete login flow nesting under `once_only_controller` and protected-page verification in the approved architecture.
- [ ] Document the new CLI and forbid one-off generator scripts for structures supported by the tree schema.

### Task 3: End-to-end verification

**Files:**
- Verify only; no additional production files.

**Interfaces:**
- Consumes: a representative nested scenario.
- Produces: parseable JMX with Login inside Once Only and business samplers outside it.

- [ ] Run unit tests.
- [ ] Run the new CLI against a temporary nested scenario and parse the output XML.
- [ ] Confirm `git diff` contains no change to `scripts/generate_jmx.py` from this task.
- [ ] Compile the new Python file and inspect the final focused diff.
