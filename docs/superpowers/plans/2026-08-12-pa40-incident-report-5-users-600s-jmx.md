# PA40 Incident Report 5-User 600-Second JMX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a statically validated JMeter JMX from the approved PA40 SAZ architecture for five concurrent users running for 600 seconds, with the three user-approved business assertions.

**Architecture:** Convert the approved Markdown tree into the supported nested scenario JSON, preserving captured request order and dependencies. Run per-thread authentication once, repeat the complete report workflow in a Forever business loop until the Thread Group scheduler reaches 600 seconds, and parameterize user identity through the adjacent five-row CSV. Generate only through `generate_jmx_tree.py`, then perform structural and semantic validation without sending requests to the target.

**Tech Stack:** Apache JMeter 5.6.x JMX XML, nested scenario JSON, Python tree generator, HTTP samplers, CSS/XPath/JSON/boundary extractors, Groovy JSR223 processors, CSV Data Set Config.

## Global Constraints

- Source capture: `Fiddler file/PA40_Incident report.saz`.
- Approved architecture: `Output/PA40_Incident_Report_Test_Plan.md`.
- Load: 5 threads, default 5-second ramp-up, Thread Group scheduler duration 600 seconds, business Loop Controller Forever.
- Duration includes ramp-up and per-thread login.
- Login and initialization execute once per thread; cookies persist across business iterations.
- Preserve captured `person_id=1` in the Vehicle save request as a static value.
- Add only the approved assertion groups: authenticated-home feature after login; CreateIntake `message == OK` and positive `report_id`; Intake auto_confirm trimmed response body `WF`.
- Keep all request paths, methods, headers, parameters, bodies, order, correlations, and static business values traceable to the SAZ and approved architecture.
- Do not execute the JMX or send traffic to `parms42test.csitech.com`.
- Do not restore, delete, stage, or commit unrelated worktree changes.

---

### Task 1: Freeze the approved architecture

**Files:**
- Modify: `Output/PA40_Incident_Report_Test_Plan.md`
- Read: `Fiddler file/PA40_Incident report.saz`

**Interfaces:**
- Consumes: the user's approval and assertion choices.
- Produces: the authoritative stage-2 architecture used by the scenario JSON.

- [ ] **Step 1: Record resolved choices**

Mark the plan approved for JMX generation, state that duration includes ramp-up/login, retain the default 5-second ramp-up and 500–1500 ms timer, and classify Vehicle `person_id=1` as an approved captured static value.

- [ ] **Step 2: Convert the three approved recommendations into enabled assertion nodes**

Place the authenticated-home assertion on the first captured page after Login that reliably contains the chosen logged-in feature. Place two JSON assertions under CreateIntake: `$.message` equals `OK`, and `$.report_id` matches `^[1-9][0-9]*$`. Place a response-text assertion under Intake auto_confirm matching `(?s)^\s*WF\s*$`.

- [ ] **Step 3: Remove unresolved language for approved choices**

Search the authoritative plan for the resolved `person_id`, duration, ramp-up, timer, and assertion questions. Retain only execution prerequisites that genuinely depend on user-supplied CSV data or environment authorization.

### Task 2: Build and validate the nested scenario

**Files:**
- Create: `Output/PA40_Incident_Report_5Users_600Seconds.scenario.json`
- Read: `Output/PA40_Incident_Report_Test_Plan.md`
- Read: `Output/pa40_incident_users.csv`
- Read: `AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/jmx_tree_components.py`

**Interfaces:**
- Consumes: the final approved tree and exact builder method signatures.
- Produces: one nested JSON document accepted by `generate_jmx_tree.py`.

- [ ] **Step 1: Map the global test configuration**

Encode property-backed defaults for concurrency `5`, ramp-up `5`, and duration `600`; add HTTP defaults, cookie/cache managers, CSV Data Set Config, Thread Group scheduling, enabled View Results Tree, and disabled Simple Data Writer with distinct JTL paths.

- [ ] **Step 2: Map authentication and the business loop**

Keep the complete login/Disclaimer sequence inside a non-empty Once Only Controller. Put the complete active-case → report → Victim → Vehicle → PA charge → CreateIntake → save → workflow sequence in a sibling Forever Loop Controller with the approved transaction hierarchy.

- [ ] **Step 3: Map every dynamic dependency**

Encode CSV variables, per-iteration random values, CSRF and timestamp extractors, `mapping_key`, `case_id`, `form_guid`, popup values, current-iteration XPath matches, `report_id`, dynamic Referers, multipart correlation, and STX/ETX object-graph construction. Keep Vehicle `person_id=1` literal.

- [ ] **Step 4: Map only the approved assertions**

Use supported `response_assertion` and `json_assertion` nodes with the exact scopes and expressions from Task 1. Do not add HTTP-200-only, duration, popup-save, workflow, or final-list assertions.

- [ ] **Step 5: Validate JSON before generation**

Run:

```bash
python3 -m json.tool Output/PA40_Incident_Report_5Users_600Seconds.scenario.json
```

Expected: exit 0 and the full JSON printed without a parse error.

### Task 3: Generate the JMX using the supported entry point

**Files:**
- Create: `Output/PA40_Incident_Report_5Users_600Seconds.jmx`
- Use: `Output/PA40_Incident_Report_5Users_600Seconds.scenario.json`
- Use: `AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/generate_jmx_tree.py`

**Interfaces:**
- Consumes: the validated nested scenario JSON.
- Produces: a JMeter test plan XML document.

- [ ] **Step 1: Run the tree generator with built-in validation**

Run from `AI Jmx Generator/.agents/skills/jmeter-loader-skills`:

```bash
python3 scripts/generate_jmx_tree.py \
  --scenario ../../../../Output/PA40_Incident_Report_5Users_600Seconds.scenario.json \
  --output ../../../../Output/PA40_Incident_Report_5Users_600Seconds.jmx \
  --validate
```

Expected: exit 0 and a non-empty JMX file. Do not replace this command with a one-off generator.

- [ ] **Step 2: Parse the generated XML**

Run:

```bash
python3 -c "import xml.etree.ElementTree as ET; ET.parse('Output/PA40_Incident_Report_5Users_600Seconds.jmx')"
```

Expected: exit 0 with no XML parse error.

### Task 4: Verify generator regression and JMX semantics

**Files:**
- Test: `AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/tests/test_generate_jmx_tree.py`
- Validate: `Output/PA40_Incident_Report_5Users_600Seconds.jmx`
- Create or modify: `reports/validation_report.md`

**Interfaces:**
- Consumes: generated JMX, approved Markdown, scenario JSON, and CSV.
- Produces: reproducible static validation evidence and an independent validator verdict.

- [ ] **Step 1: Run the existing generator test suite**

Run:

```bash
python3 -m unittest discover -s "AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/tests" -v
```

Expected: all tests pass with zero failures and zero errors.

- [ ] **Step 2: Check semantic invariants without network execution**

Verify five default threads, five-second default ramp-up, duration 600, scheduler enabled, Forever business loop, login Once Only, CSV references, `person_id=1`, all required extractors and processors, enabled View Results Tree, disabled Simple Data Writer, and exactly the three approved assertion groups. Check that session/report/token IDs are not copied from the capture as runtime constants.

- [ ] **Step 3: Request independent `jmx_validator` review**

Ask the validator to compare the JMX against the approved Markdown and SAZ, inspect undefined/unused variables, extractor scope, assertion scope, multipart/body fidelity, and listener states. The validator must not run the scenario.

- [ ] **Step 4: Resolve every blocking validator finding through `jmx_generator`**

Apply corrections only through the approved scenario JSON and tree generator, rerun Tasks 3–4, and record the final PASS/FAIL with commands and evidence in `reports/validation_report.md`.
