# Scenario Fragment Skill Implementation Report

Status: DONE

## Implemented scope

- Added deterministic recursive Scenario assembly through `scripts/assemble_scenario.py` while leaving `generate_jmx_tree.py --scenario FILE` unchanged.
- Added object replacement, ordered array splicing, nested includes, manifest-root containment, missing-file handling, cycle reporting, exact include-object shape validation, final Scenario validation, and atomic UTF-8 JSON output.
- Added the documented fragment threshold (over 30 KB or over 20 samplers), transaction/business-unit split guidance, per-fragment `json.tool`, assembly validation, remaining-include check, count reconciliation, and failover from an oversized complete patch.
- Added the validator terminal PASS/FAIL contract and scoped revalidation protocol.
- Updated active skill documentation from JMeter 5.4.1/5.4+ to 5.6.3.
- Kept generator output at 5.6.3 without adding a validator blocker for other metadata.
- Removed `test_root_metadata_targets_supported_jmeter_version`; no dedicated root-version regression assertion remains.

## Modified files

- `AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/assemble_scenario.py` (new)
- `AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/tests/test_assemble_scenario.py` (new)
- `AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/tests/test_generate_jmx_tree.py`
- `AI Jmx Generator/.agents/skills/jmeter-loader-skills/SKILL.md`
- `AI Jmx Generator/.agents/skills/jmeter-loader-skills/references/scenario-schema.md`
- `AI Jmx Generator/.agents/skills/jmeter-loader-skills/references/validation-rules.md`
- `AI Jmx Generator/.agents/skills/jmeter-loader-skills/references/jmx_structure.md`
- `AI Jmx Generator/.codex/agents/jmx_validator.toml`
- `.superpowers/scenario-fragment-skill-report.md` (this report)

## TDD evidence

RED command:

```text
python3 -m unittest discover -s "AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/tests" -p "test_assemble_scenario.py" -v
```

RED result before implementation:

```text
Ran 9 tests in 0.020s
FAILED (failures=9)
AssertionError: assemble_scenario.py has not been implemented
```

GREEN result after minimal implementation:

```text
Ran 9 tests in 0.410s
OK
```

The tests cover object replacement, array splicing order, nested relative includes, missing includes, include cycles with a chain, manifest-root escape, mixed include fields, invalid final thread-group structure, and assembly-to-JMX end-to-end generation.

## Final verification

Initial full suite before final review fixes:

```text
python3 -m unittest discover -s "AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/tests" -v
Ran 21 tests in 3.954s
OK
```

Final review identified a read-only validator/report-writing contract conflict and two missing safety coverage cases. The validator now returns results only to its caller; non-5.6.3 metadata is explicitly warning-only. Added absolute-include rejection and failed-validation output-preservation tests.

Final full suite:

```text
python3 -m unittest discover -s "AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/tests" -v
Ran 23 tests
OK
```

Compilation:

```text
python3 -m py_compile scripts/assemble_scenario.py scripts/generate_jmx_tree.py
exit 0
```

Skill validation:

```text
quick_validate.py "AI Jmx Generator/.agents/skills/jmeter-loader-skills"
Skill is valid!
```

Active skill version scan:

```text
rg -n "5\\.4\\.1" "AI Jmx Generator/.agents/skills/jmeter-loader-skills"
exit 1, no matches
```

Temporary fragmented end-to-end verification:

```text
Scenario assembly validation passed
JMX structure validation passed
samplers=1
remaining_includes=False
jmeter=5.6.3
```

## Constraints observed

- Did not change the generator's single-file input interface.
- Did not add variable producer-consumer closure validation.
- Did not add a 5.6.3-specific regression test.
- Did not classify non-5.6.3 metadata as a validator blocker.
- Validator remains read-only and does not write reports; callers may persist its terminal result.
- Did not run JMeter or access a target environment.
- Did not commit, restore, or delete unrelated worktree changes.
- Removed only the verification-generated `scripts/__pycache__/assemble_scenario.cpython-314.pyc`; it is not part of the deliverable.
