# PA40 Incident Report JMX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a runnable JMeter JMX from `PA40_Incident report.saz` for 5 concurrent users, each logging in once and creating 3 incident reports, with the two user-approved assertions.

**Architecture:** Keep authentication in a Once Only Controller and the complete report-creation chain in a three-iteration Loop Controller. Correlate all session/report identifiers from responses, source user identity fields from a five-row CSV, and validate the generated XML and JMeter semantics independently.

**Tech Stack:** Apache JMeter 5.6.x JMX XML, HTTP samplers, CSS/JSON/regex extractors, Groovy JSR223 processors, CSV Data Set Config.

## Global Constraints

- Source capture: `PA40_Incident report.saz`.
- Load: 5 threads, 5-second ramp-up, 3 report iterations per thread, 15 expected reports.
- Login executes once per thread; cookies persist across the three report iterations.
- Add only these assertions: CreateIntake JSON `message == OK` plus positive `report_id`; Intake auto_confirm HTTP 200 plus response body exactly `WF`.
- Preserve multipart boundaries and dynamically correlate tokens, FormGUID, case/report/object IDs.
- Do not modify the pre-existing untracked `PA40_Incident_Report/` directory.
- Do not commit because the worktree contains unrelated user changes.

---

### Task 1: Record the approved assertions in the architecture

**Files:**
- Modify: `Output/PA40_Incident_Report_Test_Plan.md`

**Interfaces:**
- Consumes: the approved stage-1 architecture and user assertion requirements.
- Produces: the authoritative architecture used by the generator.

- [ ] **Step 1: Replace the two assertion recommendations with enabled assertion nodes**

Add a JSON Assertion below `POST ...CreateIntake` that requires `$.message` to equal `OK` and `$.report_id` to exist and be a positive integer. Add response-code and response-body assertions below `POST Intake?action=auto_confirm&save_data=1`, requiring HTTP 200 and trimmed body `WF`.

- [ ] **Step 2: Keep every other assertion disabled as a recommendation**

Verify the architecture does not authorize login, Inbox, popup, workflow, or duration assertions.

### Task 2: Generate the JMX

**Files:**
- Create: `Output/PA40_Incident_Report_5Users_3Loops.jmx`
- Use: `Output/pa40_incident_users.csv`
- Read: `PA40_Incident report.saz`
- Read: `Output/PA40_Incident_Report_Test_Plan.md`

**Interfaces:**
- Consumes: SAZ request/response bodies, the approved architecture, and CSV variables `username,password,staff_id,region_id`.
- Produces: a complete JMeter test plan with response correlations and only the approved assertions.

- [ ] **Step 1: Build the test-plan tree**

Generate HTTP defaults, Cookie/Cache/Header managers, CSV Data Set Config, Thread Group, Once Only login flow, three-iteration report flow, transaction controllers, scoped timers, result collector, and all retained business samplers.

- [ ] **Step 2: Implement correlations and runtime values**

Use response extractors for CSRF tokens, timestamps, FormGUID, MappingKey, case/object/report IDs, and charge candidates. Generate person/vehicle/narrative/rnd values once per report iteration and construct STX/ETX payloads in Groovy with `(char)0x02` and `(char)0x03`.

- [ ] **Step 3: Add the approved assertions**

CreateIntake must fail unless `message` is `OK` and `report_id` is a positive integer. Intake auto_confirm must fail unless the response code is 200 and the trimmed body is `WF`. Do not add any other assertion.

### Task 3: Verify the generated artifact

**Files:**
- Validate: `Output/PA40_Incident_Report_5Users_3Loops.jmx`
- Create or update: `reports/validation_report.md`

**Interfaces:**
- Consumes: the generated JMX and approved architecture.
- Produces: evidence that the JMX is structurally valid and matches the workload and assertion scope.

- [ ] **Step 1: Run XML and JMeter non-execution validation**

Parse the XML and, when JMeter is installed, run a non-GUI load/parse check that does not send traffic to the target environment. Do not execute the real performance scenario.

- [ ] **Step 2: Check semantic invariants**

Verify 5 default threads, 5-second ramp-up, business loop count 3, login Once Only Controller, five-row CSV, no hard-coded session/report tokens, required extractors, scoped timers, JTL collector, and exactly the two approved assertion groups.

- [ ] **Step 3: Run independent validator review**

Use `jmx_validator` to inspect undefined/unused variables, extractor scope, suspicious constants, JSR223 necessity, and unauthorized assertions. Update the JMX only through `jmx_generator` if the validator reports blockers, then repeat validation to PASS.
