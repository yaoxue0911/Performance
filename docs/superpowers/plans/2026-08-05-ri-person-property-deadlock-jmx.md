# RI Person / Property Deadlock JMX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate and validate a JMeter JMX that uses two independent accounts to add Person and Property records concurrently to the same user-supplied Case.

**Architecture:** A single Test Plan contains two parallel Thread Groups with separate Cookie Managers. The Person group dynamically generates only first/last names; the Property group reloads the add form each iteration and randomly extracts an existing `c_person_id`; both groups share the User Defined Variable `case_id` and default to ten business iterations.

**Tech Stack:** Apache JMeter 5.x JMX XML, Python 3 generator helpers, `AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/generate_jmx.py`, ASP.NET WebForms response correlation, `jmx_validator` agent.

## Global Constraints

- Use the approved architecture in `Output/RI_Add_Person_Property_Deadlock_Test_Plan.md`.
- Do not use CSV or CSV Data Set Config.
- Put `case_id`, `person_username`, `person_password`, `property_username`, and `property_password` in JMX User Defined Variables.
- Use two different accounts and isolated Cookie Managers.
- Default `person_loops` and `property_loops` to `10`.
- Add no Response, JSON, Duration, or other Assertion elements.
- Person first/last name are dynamic; all other Person business values remain as recorded in the SAZ.
- Property `c_person_id` is randomly extracted from the current add-property response; all other Property business values remain as recorded in the SAZ.
- Do not add a cross-thread synchronization barrier, JSR223 processor, or Critical Section Controller.
- All Parameter-style POST arguments set `HTTPArgument.always_encode=true`; all HTTP samplers follow redirects.

---

### Task 1: Freeze the Approved Architecture

**Files:**
- Modify: `Output/RI_Add_Person_Property_Deadlock_Test_Plan.md`
- Test: `reports/validation_report.md`

**Interfaces:**
- Consumes: the user-approved no-assertion, ten-loop requirements.
- Produces: an architecture whose default loop properties are exactly `${__P(person_loops,10)}` and `${__P(property_loops,10)}`.

- [ ] **Step 1: Write the failing architecture checks**

```bash
rg -n '\$\{__P\((person|property)_loops,100\)\}|Assertion' Output/RI_Add_Person_Property_Deadlock_Test_Plan.md
```

Expected before the edit: the command finds the old `100` defaults and only the explicitly labelled recommendation section for assertions.

- [ ] **Step 2: Change both default loop values to ten and record that assertions are disabled**

Replace every `${__P(person_loops,100)}` with `${__P(person_loops,10)}` and every `${__P(property_loops,100)}` with `${__P(property_loops,10)}`. Preserve the assertion recommendation history but state unambiguously that no assertions will be generated.

- [ ] **Step 3: Re-run the architecture checks**

```bash
rg -n '\$\{__P\(person_loops,10\)\}|\$\{__P\(property_loops,10\)\}' Output/RI_Add_Person_Property_Deadlock_Test_Plan.md
rg -n '\$\{__P\((person|property)_loops,100\)\}' Output/RI_Add_Person_Property_Deadlock_Test_Plan.md
```

Expected: the first command finds both ten-loop properties; the second command returns no matches.

- [ ] **Step 4: Have `jmx_validator` revalidate the architecture**

Expected: `reports/validation_report.md` reports PASS and confirms no assertion is authorized.

### Task 2: Generate the Two-Process JMX

**Files:**
- Create: `Output/generate_ri_person_property_deadlock_jmx.py`
- Create: `Output/RI_Add_Person_Property_Deadlock.jmx`
- Read: `RI_add person and property.saz`
- Read: `AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/generate_jmx.py`

**Interfaces:**
- Consumes: the approved architecture and exact request/form data from SAZ sessions 003–017, 031, 043, 049, 068–089, 094–106, 125, 128, and 131.
- Produces: `build(output_path: pathlib.Path) -> None`, which creates the complete JMX deterministically except for runtime JMeter functions.

- [ ] **Step 1: Write failing XML contract checks before the generator exists**

```bash
test -f Output/RI_Add_Person_Property_Deadlock.jmx
python -c "import xml.etree.ElementTree as E; E.parse('Output/RI_Add_Person_Property_Deadlock.jmx')"
```

Expected: FAIL because the JMX does not exist.

- [ ] **Step 2: Implement the generator through the repository JMX builder**

Create `build(output_path)` and use the repository generator/building primitives wherever they can express the required elements. Add focused XML helper functions only for unsupported components such as CSS extractors, User Parameters, per-form WebForms argument mapping, two parallel Thread Groups, and per-thread Cookie Managers.

The generated User Defined Variables must contain these exact names:

```text
target_protocol=https
target_host=rirmsint.csitech.com
target_port=443
case_id=
person_username=
person_password=
property_username=
property_password=
```

The two Loop Controllers must use these exact functions:

```text
${__P(person_loops,10)}
${__P(property_loops,10)}
```

The Property form extractor must use selector `input[ObjectName="c_person_id"]`, attribute `value`, match number `0`, and default `PERSON_NOT_FOUND`.

- [ ] **Step 3: Generate the JMX**

```bash
python Output/generate_ri_person_property_deadlock_jmx.py
```

Expected: exit 0 and `Output/RI_Add_Person_Property_Deadlock.jmx` created.

- [ ] **Step 4: Run the XML and structural contract checks**

```bash
python -c "import xml.etree.ElementTree as E; E.parse('Output/RI_Add_Person_Property_Deadlock.jmx')"
rg -n 'Add Person Process|Add Property Process|person_username|property_username|property_person_id|PERSON_NOT_FOUND|__P\(person_loops,10\)|__P\(property_loops,10\)' Output/RI_Add_Person_Property_Deadlock.jmx
```

Expected: XML parsing succeeds and every required structure is found.

### Task 3: Validate the JMX and Correct Generator Defects

**Files:**
- Modify: `Output/generate_ri_person_property_deadlock_jmx.py`
- Regenerate: `Output/RI_Add_Person_Property_Deadlock.jmx`
- Modify: `reports/validation_report.md`

**Interfaces:**
- Consumes: the generated JMX from Task 2.
- Produces: a validator PASS covering variables, extractor scope, hard-coded IDs/tokens, assertions, thread-group parallelism, and XML/JMeter compatibility.

- [ ] **Step 1: Run `jmx_validator` against the generated JMX**

Expected checks: all referenced variables are defined; all extracted values are consumed; Case/Person IDs and WebForms values are not hard-coded; no Assertion elements exist; the two Thread Groups are parallel and have isolated Cookie Managers; both default business loops equal ten.

- [ ] **Step 2: Fix every blocker only in the generator**

Do not hand-edit the generated JMX. Update `Output/generate_ri_person_property_deadlock_jmx.py`, regenerate the JMX, and preserve all approved architecture choices.

- [ ] **Step 3: Repeat validation until PASS**

Expected: `reports/validation_report.md` concludes PASS with no unresolved blockers.

- [ ] **Step 4: Run final local verification**

```bash
python Output/generate_ri_person_property_deadlock_jmx.py
python -c "import xml.etree.ElementTree as E; root=E.parse('Output/RI_Add_Person_Property_Deadlock.jmx').getroot(); assert len(root.findall('.//ThreadGroup')) == 2; assert not root.findall('.//ResponseAssertion'); assert not root.findall('.//DurationAssertion'); print('PASS')"
git diff --check
```

Expected: generator exits 0, verification prints `PASS`, and `git diff --check` has no output.
