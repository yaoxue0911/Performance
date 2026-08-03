#!/usr/bin/env python3
"""One-time PA40 JMX assembler.

The bundled generate_jmx.py --build command creates the base JMeter document.
This script then adds structures the CLI cannot express: nested controllers,
sampler-scoped elements, CSS/header correlations, multipart raw data, and the
runtime STX/ETX object payload.
"""

from __future__ import annotations

import re
import json
import subprocess
import sys
import tempfile
import urllib.parse
import zipfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "Output" / "PA40_Incident_Report_5Users_3Loops.jmx"
SAZ = ROOT / "PA40_Incident report.saz"
CSV = "pa40_incident_users.csv"
GENERATOR = ROOT / "AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/generate_jmx.py"


def prop(tag: str, name: str, value) -> ET.Element:
    e = ET.Element(tag, {"name": name})
    e.text = str(value).lower() if isinstance(value, bool) else str(value)
    return e


def string(name: str, value="") -> ET.Element:
    return prop("stringProp", name, value)


def boolean(name: str, value: bool) -> ET.Element:
    return prop("boolProp", name, value)


def integer(name: str, value: int) -> ET.Element:
    return prop("intProp", name, value)


def pair(parent: ET.Element, element: ET.Element, children: ET.Element | None = None) -> ET.Element:
    parent.append(element)
    tree = children if children is not None else ET.Element("hashTree")
    parent.append(tree)
    return tree


def named(tag: str, gui: str, testclass: str, name: str) -> ET.Element:
    return ET.Element(tag, {
        "guiclass": gui,
        "testclass": testclass,
        "testname": name,
        "enabled": "true",
    })


def controller(tag: str, gui: str, name: str, props=()) -> ET.Element:
    e = named(tag, gui, tag, name)
    for item in props:
        e.append(item)
    return e


def transaction(name: str) -> ET.Element:
    return controller("TransactionController", "TransactionControllerGui", name, (
        boolean("TransactionController.include_timers", False),
        boolean("TransactionController.parent", True),
    ))


def loop_controller() -> ET.Element:
    return controller("LoopController", "LoopControlPanel", "Create Incident Report", (
        boolean("LoopController.continue_forever", False),
        string("LoopController.loops", "${__P(report_loops,3)}"),
    ))


def once_controller() -> ET.Element:
    return controller("OnceOnlyController", "OnceOnlyControllerGui", "Login Once Per User")


def if_abort_controller() -> tuple[ET.Element, ET.Element]:
    c = controller("IfController", "IfControllerPanel", "Abort Current Report Iteration On Correlation Failure", (
        string("IfController.condition", "${__groovy(vars.get('iteration_failed') == 'true')}"),
        boolean("IfController.evaluateAll", False),
        boolean("IfController.useExpression", True),
    ))
    h = ET.Element("hashTree")
    action = named("TestAction", "TestActionGui", "TestAction", "Go to next iteration of Current Loop")
    action.append(integer("ActionProcessor.action", 5))
    action.append(integer("ActionProcessor.target", 0))
    action.append(string("ActionProcessor.duration", "0"))
    pair(h, action)
    return c, h


def add_abort_check(parent: ET.Element) -> None:
    c, h = if_abort_controller()
    pair(parent, c, h)


def add_assertion_failure_gate(parent: ET.Element, name: str, include_iteration_failed: bool = False) -> None:
    terms = ["vars.get('JMeterThread.last_sample_ok') != 'true'"]
    if include_iteration_failed:
        terms.append("vars.get('iteration_failed') == 'true'")
    c = controller("IfController", "IfControllerPanel", name, (
        string("IfController.condition", "${__groovy(" + " || ".join(terms) + ")}"),
        boolean("IfController.evaluateAll", False),
        boolean("IfController.useExpression", True),
    ))
    h = ET.Element("hashTree")
    action = named("TestAction", "TestActionGui", "TestAction", "Skip Remaining State Calls - Next Report")
    action.extend([integer("ActionProcessor.action", 5), integer("ActionProcessor.target", 0),
                   string("ActionProcessor.duration", "0")])
    pair(h, action)
    pair(parent, c, h)


def add_login_stop_check(parent: ET.Element) -> None:
    c = controller("IfController", "IfControllerPanel", "Stop User When Login Correlation Fails", (
        string("IfController.condition", "${__groovy(vars.get('iteration_failed') == 'true')}"),
        boolean("IfController.evaluateAll", False), boolean("IfController.useExpression", True),
    ))
    h = ET.Element("hashTree")
    action = named("TestAction", "TestActionGui", "TestAction", "Stop Current Thread - Login Correlation Failed")
    action.extend([integer("ActionProcessor.action", 1), integer("ActionProcessor.target", 0),
                   string("ActionProcessor.duration", "0")])
    pair(h, action)
    pair(parent, c, h)


def http_defaults() -> ET.Element:
    e = named("ConfigTestElement", "HttpDefaultsGui", "ConfigTestElement", "HTTP Request Defaults")
    args = ET.Element("elementProp", {"name": "HTTPsampler.Arguments", "elementType": "Arguments",
                                      "guiclass": "HTTPArgumentsPanel", "testclass": "Arguments"})
    args.append(ET.Element("collectionProp", {"name": "Arguments.arguments"}))
    e.extend([args, string("HTTPSampler.domain", "${target_host}"),
              string("HTTPSampler.port", "${target_port}"),
              string("HTTPSampler.protocol", "${protocol}"),
              string("HTTPSampler.contentEncoding", "UTF-8"), string("HTTPSampler.path", ""),
              string("HTTPSampler.concurrentPool", "6")])
    return e


def cookie_manager() -> ET.Element:
    e = named("CookieManager", "CookiePanel", "CookieManager", "HTTP Cookie Manager")
    e.extend([ET.Element("collectionProp", {"name": "CookieManager.cookies"}),
              boolean("CookieManager.clearEachIteration", False),
              boolean("CookieManager.controlledByThreadGroup", True)])
    return e


def cache_manager() -> ET.Element:
    e = named("CacheManager", "CacheManagerGui", "CacheManager", "HTTP Cache Manager")
    e.extend([boolean("clearEachIteration", False), boolean("useExpires", True), string("maxCacheSize", "5000")])
    return e


def csv_data_set() -> ET.Element:
    e = named("CSVDataSet", "TestBeanGUI", "CSVDataSet", "CSV Data Set Config - PA40 Users")
    e.extend([string("delimiter", ","), string("fileEncoding", "UTF-8"), string("filename", CSV),
              boolean("ignoreFirstLine", True), boolean("quotedData", True), boolean("recycle", False),
              string("shareMode", "shareMode.all"), boolean("stopThread", True),
              string("variableNames", "username,password,staff_id,region_id")])
    return e


def header_manager(headers: list[tuple[str, str]], name="HTTP Header Manager") -> ET.Element:
    e = named("HeaderManager", "HeaderPanel", "HeaderManager", name)
    coll = ET.Element("collectionProp", {"name": "HeaderManager.headers"})
    for hname, value in headers:
        hp = ET.Element("elementProp", {"name": "", "elementType": "Header"})
        hp.extend([string("Header.name", hname), string("Header.value", value)])
        coll.append(hp)
    e.append(coll)
    return e


def uniform_timer(name: str) -> ET.Element:
    e = named("UniformRandomTimer", "UniformRandomTimerGui", "UniformRandomTimer", name)
    e.extend([string("ConstantTimer.delay", "${__P(think_time_min_ms,300)}"),
              string("RandomTimer.range", "${__P(think_time_range_ms,700)}")])
    return e


def http_argument(name: str, value: str, always_encode=True) -> ET.Element:
    e = ET.Element("elementProp", {"name": name, "elementType": "HTTPArgument"})
    e.extend([boolean("HTTPArgument.always_encode", always_encode), string("Argument.value", value),
              string("Argument.metadata", "="), boolean("HTTPArgument.use_equals", True),
              string("Argument.name", name)])
    return e


def http_sampler(name: str, method: str, path: str, params: list[tuple[str, str]], raw_body: str | None) -> ET.Element:
    e = named("HTTPSamplerProxy", "HttpTestSampleGui", "HTTPSamplerProxy", name)
    args = ET.Element("elementProp", {"name": "HTTPsampler.Arguments", "elementType": "Arguments",
                                      "guiclass": "HTTPArgumentsPanel", "testclass": "Arguments"})
    coll = ET.Element("collectionProp", {"name": "Arguments.arguments"})
    if raw_body is not None:
        coll.append(http_argument("", raw_body, False))
    else:
        for key, value in params:
            coll.append(http_argument(key, value, True))
    args.append(coll)
    e.extend([args, string("HTTPSampler.domain", ""), string("HTTPSampler.port", ""),
              string("HTTPSampler.protocol", ""), string("HTTPSampler.contentEncoding", "UTF-8"),
              string("HTTPSampler.path", path), string("HTTPSampler.method", method),
              boolean("HTTPSampler.follow_redirects", True), boolean("HTTPSampler.auto_redirects", False),
              boolean("HTTPSampler.use_keepalive", True), boolean("HTTPSampler.DO_MULTIPART_POST", False),
              boolean("HTTPSampler.postBodyRaw", raw_body is not None),
              string("HTTPSampler.embedded_url_re", ""), string("HTTPSampler.connect_timeout", ""),
              string("HTTPSampler.response_timeout", "")])
    return e


def css_extractor(ref: str, selector: str, attribute="value", scope="parent", default="NOT_FOUND") -> ET.Element:
    e = named("HtmlExtractor", "HtmlExtractorGui", "HtmlExtractor", f"CSS Extractor - {ref}")
    e.extend([string("HtmlExtractor.refname", ref), string("HtmlExtractor.expr", selector),
              string("HtmlExtractor.attribute", attribute), string("HtmlExtractor.default", default),
              boolean("HtmlExtractor.default_empty_value", False), string("HtmlExtractor.match_number", "1"),
              string("Sample.scope", scope)])
    return e


def regex_extractor(ref: str, regex: str, match="1", headers=False, scope="parent") -> ET.Element:
    e = named("RegexExtractor", "RegexExtractorGui", "RegexExtractor", f"Regex Extractor - {ref}")
    e.extend([string("RegexExtractor.useHeaders", "true" if headers else "false"),
              string("RegexExtractor.refname", ref), string("RegexExtractor.regex", regex),
              string("RegexExtractor.template", "$1$"), string("RegexExtractor.match_number", match),
              string("RegexExtractor.default", "NOT_FOUND"), string("Sample.scope", scope)])
    return e


def json_extractor(ref: str, path: str, match="1") -> ET.Element:
    e = named("JSONPostProcessor", "JSONPostProcessorGui", "JSONPostProcessor", f"JSON Extractor - {ref}")
    e.extend([string("JSONPostProcessor.referenceNames", ref), string("JSONPostProcessor.jsonPathExprs", path),
              string("JSONPostProcessor.match_numbers", match), string("JSONPostProcessor.default_values", "NOT_FOUND"),
              boolean("JSONPostProcessor.compute_concat", False), string("Sample.scope", "parent")])
    return e


def jsr223(tag: str, name: str, script: str) -> ET.Element:
    gui = "TestBeanGUI"
    e = named(tag, gui, tag, name)
    e.extend([string("scriptLanguage", "groovy"), string("parameters", ""), string("filename", ""),
              string("cacheKey", name), string("script", script)])
    return e


def json_assertion(name: str, path: str, expected: str, regex: bool) -> ET.Element:
    e = named("JSONPathAssertion", "JSONPathAssertionGui", "JSONPathAssertion", name)
    e.extend([string("JSON_PATH", path), string("EXPECTED_VALUE", expected), boolean("JSONVALIDATION", True),
              boolean("EXPECT_NULL", False), boolean("INVERT", False), boolean("ISREGEX", regex)])
    return e


def response_assertion(name: str, field: str, pattern: str, test_type: int) -> ET.Element:
    e = named("ResponseAssertion", "AssertionGui", "ResponseAssertion", name)
    coll = ET.Element("collectionProp", {"name": "Asserter.test_strings"})
    coll.append(string(f"assertion_{name}", pattern))
    e.extend([coll, string("Assertion.custom_message", ""), string("Assertion.test_field", field),
              boolean("Assertion.assume_success", False), integer("Assertion.test_type", test_type)])
    return e


def result_collector() -> ET.Element:
    e = named("ResultCollector", "SimpleDataWriter", "ResultCollector", "Simple Data Writer - PA40 JTL")
    e.append(boolean("ResultCollector.error_logging", False))
    obj = ET.Element("objProp")
    n = ET.Element("name"); n.text = "saveConfig"; obj.append(n)
    value = ET.Element("value", {"class": "SampleSaveConfiguration"})
    for tag, val in (("time", True), ("latency", True), ("timestamp", True), ("success", True),
                     ("label", True), ("code", True), ("message", True), ("threadName", True),
                     ("dataType", True), ("encoding", False), ("assertions", True), ("subresults", True),
                     ("responseData", False), ("samplerData", False), ("xml", False), ("fieldNames", True),
                     ("responseHeaders", False), ("requestHeaders", False), ("responseDataOnError", False),
                     ("saveAssertionResultsFailureMessage", True), ("assertionsResultsToSave", "0"),
                     ("bytes", True), ("sentBytes", True), ("url", True), ("threadCounts", True),
                     ("idleTime", True), ("connectTime", True)):
        child = ET.Element(tag); child.text = str(val).lower() if isinstance(val, bool) else str(val); value.append(child)
    obj.append(value); e.append(obj)
    e.extend([string("filename", "${__P(result_file,PA40_Incident_Report.jtl)}"), boolean("useGroupName", False),
              boolean("saveHeaders", False)])
    return e


def set_test_plan_variables(test_plan: ET.Element) -> None:
    values = {
        "protocol": "${__P(protocol,https)}",
        "target_host": "${__P(target_host,parms42test.csitech.com)}",
        "target_port": "${__P(target_port,443)}",
        "division_id": "3",
        "template_id": "1318",
        "report_type": "C",
        "indicator_type": "1",
        "inbox_sub_id": "10030101",
    }
    udv = test_plan.find("elementProp[@name='TestPlan.user_defined_variables']")
    if udv is None:
        raise RuntimeError("generate_jmx --build did not create TestPlan UDV")
    coll = udv.find("collectionProp[@name='Arguments.arguments']")
    coll.clear()
    coll.set("name", "Arguments.arguments")
    for key, value in values.items():
        arg = ET.Element("elementProp", {"name": key, "elementType": "Argument"})
        arg.extend([string("Argument.name", key), string("Argument.value", value), string("Argument.metadata", "=")])
        coll.append(arg)


def validate_arguments_and_http_defaults(root: ET.Element) -> None:
    arguments = root.findall(".//elementProp[@elementType='Arguments']")
    if not arguments:
        raise RuntimeError("No Arguments elements generated")
    for element in arguments:
        coll = element.find("collectionProp")
        if coll is None or coll.get("name") != "Arguments.arguments":
            raise RuntimeError(f"Invalid Arguments collection in {element.get('name')}")
    test_plan = root.find("./hashTree/TestPlan")
    udv = test_plan.find("elementProp[@name='TestPlan.user_defined_variables']/collectionProp[@name='Arguments.arguments']")
    defined = {
        arg.find("stringProp[@name='Argument.name']").text
        for arg in udv.findall("elementProp[@elementType='Argument']")
    }
    defaults = root.find(".//ConfigTestElement[@testname='HTTP Request Defaults']")
    required = {
        defaults.find("stringProp[@name='HTTPSampler.protocol']").text.strip("${}"),
        defaults.find("stringProp[@name='HTTPSampler.domain']").text.strip("${}"),
        defaults.find("stringProp[@name='HTTPSampler.port']").text.strip("${}"),
    }
    if not required <= defined:
        raise RuntimeError(f"HTTP Defaults reference undefined UDV variables: {required - defined}")
    if "home_csrf" in ET.tostring(root, encoding="unicode"):
        raise RuntimeError("Unused home_csrf definition/reference remains")
    candidates = []
    for sampler in root.findall(".//HTTPSamplerProxy"):
        path = sampler.find("stringProp[@name='HTTPSampler.path']")
        if path is not None: candidates.append(("URL", path.text or ""))
    for header in root.findall(".//elementProp[@elementType='Header']"):
        hname = header.find("stringProp[@name='Header.name']")
        hvalue = header.find("stringProp[@name='Header.value']")
        if hname is not None and (hname.text or "").lower() == "referer":
            candidates.append(("Referer", "" if hvalue is None else (hvalue.text or "")))
    for kind, value in candidates:
        query = value.split("?", 1)[1].split("#", 1)[0] if "?" in value else ""
        if sum(1 for part in query.split("&") if part.split("=", 1)[0].lower() == "rnd") > 1:
            raise RuntimeError(f"Duplicate rnd keys in {kind}: {value}")


def read_response(zf: zipfile.ZipFile, sid: int) -> tuple[str, str]:
    raw = zf.read(f"raw/{sid:02d}_s.txt").decode("utf-8", "replace").replace("\r\n", "\n")
    return raw.partition("\n\n")[::2]


class InputCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.inputs: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "input":
            self.inputs.append({key: value or "" for key, value in attrs})


def validate_extractors_against_saz(root: ET.Element, zf: zipfile.ZipFile) -> None:
    regex_sources = {
        "case_id": (11, "body", 1), "FormGUID": (16, "headers", 1),
        "case_location_id": (17, "body", 1), "cfs_id": (17, "body", 1), "org_id": (17, "body", 1),
        "mapping_key": (22, "body", 1), "victim_person_id": (44, "body", 1),
        "victim_contact_id": (44, "body", 1), "victim_location_id": (44, "body", 1),
        "vehicle_id": (53, "body", 1), "case_vehicle_id": (53, "body", 1),
        "charge1_raw": (55, "body", 1), "charge2_raw": (56, "body", 1),
        "inv_njs_id": (58, "body", 2),
    }
    regex_count = 0
    for extractor in root.findall(".//RegexExtractor"):
        ref = extractor.findtext("stringProp[@name='RegexExtractor.refname']")
        if ref not in regex_sources:
            raise RuntimeError(f"No SAZ source registered for regex extractor {ref}")
        sid, part, minimum = regex_sources[ref]
        headers, body = read_response(zf, sid)
        pattern = extractor.findtext("stringProp[@name='RegexExtractor.regex']") or ""
        matches = re.findall(pattern, headers if part == "headers" else body)
        if len(matches) < minimum:
            raise RuntimeError(f"Regex extractor {ref} zero/insufficient match in SAZ sid {sid}: {pattern!r}")
        regex_count += 1

    css_sources = {
        "login_csrf": 1, "disclaimer_csrf": 5, "incident_csrf": 12,
        "police_csrf": 14, "police_doubleEntryTimeStamp": 14, "middle_csrf": 17,
        "victim_csrf": 22, "victim_doubleEntryTimeStamp": 22,
        "vehicle_csrf": 45, "vehicle_doubleEntryTimeStamp": 45,
        "charge_csrf": 54, "charge_doubleEntryTimeStamp": 54, "intake_csrf": 60,
        "workflow_csrf": 85, "final_police_csrf": 89,
    }
    css_count = 0
    for extractor in root.findall(".//HtmlExtractor"):
        ref = extractor.findtext("stringProp[@name='HtmlExtractor.refname']")
        sid = css_sources.get(ref)
        if sid is None:
            raise RuntimeError(f"No SAZ source registered for CSS extractor {ref}")
        selector = extractor.findtext("stringProp[@name='HtmlExtractor.expr']") or ""
        name_match = re.fullmatch(r"input\[name='([^']+)'\]", selector)
        if not name_match:
            raise RuntimeError(f"Unsupported regression CSS selector {selector!r}")
        collector = InputCollector()
        collector.feed(read_response(zf, sid)[1])
        attribute = extractor.findtext("stringProp[@name='HtmlExtractor.attribute']") or "value"
        values = [item.get(attribute, "") for item in collector.inputs if item.get("name") == name_match.group(1)]
        if not any(values):
            raise RuntimeError(f"CSS extractor {ref} zero match/value in SAZ sid {sid}: {selector!r}")
        css_count += 1

    geo = json.loads(read_response(zf, 39)[1])
    addresses = [item for item in geo.get("addressList", []) if item.get("street1") == "6 ACORN BLVD"]
    json_fields = {"geo_location_id": "id", "geo_longitude": "longitude",
                   "geo_latitude": "latitude", "geo_municipality": "municipality"}
    for ref, field in json_fields.items():
        if not addresses or addresses[0].get(field) in (None, ""):
            raise RuntimeError(f"JSON extractor {ref} zero match/value in SAZ sid 39")
    report_id = json.loads(read_response(zf, 59)[1]).get("report_id")
    if not re.fullmatch(r"[1-9][0-9]*", str(report_id or "")):
        raise RuntimeError("JSON extractor report_id is not positive in SAZ sid 59")
    if len(root.findall(".//JSONPostProcessor")) != 5:
        raise RuntimeError("Unexpected JSON extractor count")
    print(f"Extractor regression PASS: regex={regex_count}, css={css_count}, json=5")


def validate_control_flow_and_assertions(root: ET.Element) -> None:
    stops = [e for e in root.findall(".//TestAction")
             if e.get("testname") == "Stop Current Thread - Login Correlation Failed"]
    if len(stops) != 2 or any(e.findtext("intProp[@name='ActionProcessor.action']") != "1" or
                              e.findtext("intProp[@name='ActionProcessor.target']") != "0" for e in stops):
        raise RuntimeError("Login failure TestAction is not Stop Current Thread (action=1,target=0)")

    expected_gates = {
        "handler=CreateIntake": "Gate Failed CreateIntake Assertion",
        "action=auto_confirm": "Gate Failed Auto Confirm Assertion",
    }
    found: set[str] = set()
    for ht in root.findall(".//hashTree"):
        children = list(ht)
        for index, element in enumerate(children):
            if element.tag != "HTTPSamplerProxy":
                continue
            path = element.findtext("stringProp[@name='HTTPSampler.path']") or ""
            for marker, gate_name in expected_gates.items():
                if marker not in path:
                    continue
                if index + 2 >= len(children) or children[index + 2].tag != "IfController" or children[index + 2].get("testname") != gate_name:
                    raise RuntimeError(f"{gate_name} is not immediately after its asserted sampler")
                gate_tree = children[index + 3]
                action = gate_tree.find("TestAction")
                if action is None or action.findtext("intProp[@name='ActionProcessor.action']") != "5":
                    raise RuntimeError(f"{gate_name} does not skip to next current-loop iteration")
                condition = children[index + 2].findtext("stringProp[@name='IfController.condition']") or ""
                if "JMeterThread.last_sample_ok" not in condition:
                    raise RuntimeError(f"{gate_name} does not gate assertion failure")
                found.add(gate_name)
    if found != set(expected_gates.values()):
        raise RuntimeError(f"Missing assertion gates: {set(expected_gates.values()) - found}")
    assertions = root.findall(".//JSONPathAssertion") + root.findall(".//ResponseAssertion")
    if len(assertions) != 4:
        raise RuntimeError(f"Expected exactly 4 assertions, found {len(assertions)}")
    print("Control-flow regression PASS: login_stop=2 action=1; assertion_gates=2 immediate; assertions=4")


def read_request(zf: zipfile.ZipFile, sid: int):
    raw = zf.read(f"raw/{sid:02d}_c.txt").decode("utf-8", "replace").replace("\r\n", "\n")
    head, _, body = raw.partition("\n\n")
    lines = head.splitlines()
    method, url, _ = lines[0].split(" ", 2)
    headers = []
    for line in lines[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            headers.append((k.strip(), v.strip()))
    return method, url, headers, body


TOKEN_BY_SESSION = {
    2: "${login_csrf}", 7: "${disclaimer_csrf}",
    13: "${incident_csrf}", 15: "${police_csrf}", 16: "${police_csrf}", 21: "${middle_csrf}",
    **{sid: "${victim_csrf}" for sid in range(27, 44)}, 44: "${middle_csrf}",
    **{sid: "${vehicle_csrf}" for sid in range(46, 53)}, 53: "${middle_csrf}",
    55: "${charge_csrf}", 56: "${charge_csrf}", 57: "${charge_csrf}", 58: "${middle_csrf}",
    59: "${middle_csrf}", 81: "${intake_csrf}", 84: "${intake_csrf}",
    86: "${workflow_csrf}", 87: "${workflow_csrf}", 88: "${workflow_csrf}",
    90: "${final_police_csrf}",
}


def parameterize_text(text: str, sid: int) -> str:
    replacements = {
        "1100017412": "${case_id}", "4191": "${report_id}",
        "066ba348-3b60-4aab-9227-ef3813fa82f8": "${FormGUID}",
        "InfoVMcTH8d8qNANFsK2U40BjNwSrsLdtvJAOE48xIvXrPaRel2R": "${mapping_key}",
        "inbox_staff_id=1": "inbox_staff_id=${staff_id}", "regionId=100000": "regionId=${region_id}",
        "region_id=100000": "region_id=${region_id}", "last_name=MOSCISKI-LANG": "last_name=${lastName}",
        "first_name=WINNIFRED": "first_name=${firstName}", "ssn=234-79-8709": "ssn=${ssn}",
        "plate_no=T354703": "plate_no=${plateNo}",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"([?&])division_id=3(?=(&|\s|$))", r"\1division_id=${division_id}", text)
    text = re.sub(r"([?&])template_id=1318(?=(&|\s|$))", r"\1template_id=${template_id}", text)
    text = re.sub(r"([?&])report_type=C(?=(&|\s|$))", r"\1report_type=${report_type}", text)
    text = re.sub(r"([?&])indicator_type=1(?=(&|\s|$))", r"\1indicator_type=${indicator_type}", text)
    text = text.replace("inbox_sub_id=10030101", "inbox_sub_id=${inbox_sub_id}")
    rnd_value = "${__Random(100000,999999)}" if sid in (1, 2, 6, 7, 9, 10) else "${request_rnd}"
    text = re.sub(r"([?&])rnd=[^&\s]+", lambda m: m.group(1) + "rnd=" + rnd_value, text)
    if sid in (32, 33, 35):
        text = re.sub(r"MN_rnd=[^&\s]+", "MN_rnd=${victim_name_rnd}", text)
    elif sid in (36, 37, 38):
        text = re.sub(r"MN_rnd=[^&\s]+", "MN_rnd=${victim_ssn_rnd}", text)
    elif sid in (48, 49, 50):
        text = re.sub(r"MN_rnd=[^&\s]+", "MN_rnd=${vehicle_mn_rnd}", text)
    return text


def normalize_rnd_keys(value: str) -> str:
    if "?" not in value:
        return value
    prefix, query_and_fragment = value.split("?", 1)
    query, marker, fragment = query_and_fragment.partition("#")
    seen = False
    kept = []
    for part in query.split("&"):
        if part.split("=", 1)[0].lower() == "rnd":
            if seen:
                continue
            seen = True
        kept.append(part)
    result = prefix + "?" + "&".join(kept)
    return result + (marker + fragment if marker else "")


def parameterize_value(name: str, value: str, sid: int, occurrence: dict[str, int]) -> str:
    lname = name.lower()
    token = TOKEN_BY_SESSION.get(sid)
    if lname in ("__requestverificationtoken",) and token:
        return token
    if sid == 2 and lname == "loginid": return "${username}"
    if sid == 2 and lname == "password": return "${password}"
    if "doubleentrytimestamp" in lname:
        return {16: "${police_doubleEntryTimeStamp}", 43: "${victim_doubleEntryTimeStamp}",
                52: "${vehicle_doubleEntryTimeStamp}", 57: "${charge_doubleEntryTimeStamp}"}.get(sid, value)
    field = name.split("~|", 1)[0].split("$")[-1].lower()
    if field == "last_name" and value: return "${lastName}"
    if field == "first_name" and value: return "${firstName}"
    if field == "ssn" and value: return "${ssn}"
    if field == "plate_no" and value: return "${plateNo}"
    if field in ("template_id", "hdntemplateid") and value == "1318": return "${template_id}"
    if field in ("division_id", "hdndivisionid") and value == "3": return "${division_id}"
    if field in ("case_id", "o_case_id") and value == "1100017412": return "${case_id}"
    if field == "master_location_id" and sid == 43 and value: return "${geo_location_id}"
    if field == "longitude" and sid == 43 and value: return "${geo_longitude}"
    if field == "latitude" and sid == 43 and value: return "${geo_latitude}"
    if field == "municipality" and sid == 43 and value: return "${geo_municipality}"
    if lname == "objects_parameter": return "${objects_parameter}"
    if lname == "objects_data_index": return "${objects_data_index}"
    if lname in ("narrative",): return "${narrative}"
    if sid == 57 and "njs_description" in lname:
        occurrence["desc"] = occurrence.get("desc", 0) + 1
        return "${charge1_description}" if occurrence["desc"] == 1 else "${charge2_description}"
    if sid == 57 and "njs_code" in lname:
        occurrence["code"] = occurrence.get("code", 0) + 1
        return "${charge1_code}" if occurrence["code"] == 1 else "${charge2_code}"
    return parameterize_text(value, sid)


def xml_safe_runtime_value(value: str) -> str:
    """Keep XML 1.0 free of control chars while recreating them at runtime."""
    return value.replace(chr(2), "${__groovy((char)0x02)}").replace(chr(3), "${__groovy((char)0x03)}")


def build_sampler(zf: zipfile.ZipFile, sid: int) -> tuple[ET.Element, ET.Element]:
    method, url, headers, body = read_request(zf, sid)
    parsed = urllib.parse.urlsplit(url)
    path = normalize_rnd_keys(parameterize_text(parsed.path + (("?" + parsed.query) if parsed.query else ""), sid))
    content_type = next((v for k, v in headers if k.lower() == "content-type"), "")
    raw_body = None
    params: list[tuple[str, str]] = []
    occurrence: dict[str, int] = {}
    if body:
        if "application/x-www-form-urlencoded" in content_type:
            for key, value in urllib.parse.parse_qsl(body, keep_blank_values=True):
                params.append((key, xml_safe_runtime_value(parameterize_value(key, value, sid, occurrence))))
        elif "multipart/form-data" in content_type:
            raw_body = parameterize_text(body, sid)
            captured = re.search(r'name="__RequestVerificationToken"\n\n([^\n]+)', raw_body)
            if captured:
                raw_body = raw_body.replace(captured.group(1), "${workflow_csrf}")
        else:
            raw_body = body
    sampler = http_sampler(f"{method} {parsed.path}", method, path, params, raw_body)
    sh = ET.Element("hashTree")
    selected_headers = []
    for key, value in headers:
        low = key.lower()
        if low in ("content-type", "origin", "referer", "x-requested-with", "requestverificationtoken"):
            if low == "requestverificationtoken" and sid in TOKEN_BY_SESSION:
                value = TOKEN_BY_SESSION[sid]
            else:
                value = parameterize_text(value, sid)
                if low == "referer":
                    value = normalize_rnd_keys(value)
            selected_headers.append((key, value))
    if selected_headers:
        pair(sh, header_manager(selected_headers, f"Headers - {method} {parsed.path}"))
    return sampler, sh


INIT_SCRIPT = r'''import java.util.concurrent.ThreadLocalRandom
def r = ThreadLocalRandom.current()
vars.put('iteration_failed', 'false')
vars.put('firstName', 'TEST' + r.nextInt(1000, 10000))
vars.put('lastName', 'TEST' + r.nextInt(1000, 10000))
vars.put('ssn', String.format('%03d-%02d-%04d', r.nextInt(100,1000), r.nextInt(10,100), r.nextInt(1000,10000)))
vars.put('plateNo', 'P' + r.nextInt(100000, 1000000))
def idx = vars.get('__jm__Create Incident Report__idx') ?: '0'
vars.put('narrative', "PERF-${vars.get('username')}-${ctx.getThreadNum()+1}-${idx}-${System.currentTimeMillis()}")
def rnd = { '0.' + String.format('%016d', Math.abs(r.nextLong() % 10000000000000000L)) }
vars.put('request_rnd', rnd())
vars.put('victim_name_rnd', rnd())
vars.put('victim_ssn_rnd', rnd())
vars.put('vehicle_mn_rnd', rnd())'''


CORRELATION_CHECK = r'''def required = (args ?: '').split(',').findAll { it }
if (required.any { def v=vars.get(it); v == null || v == '' || v == 'NOT_FOUND' }) {
    vars.put('iteration_failed', 'true')
}'''


CHARGE_DECODE = r'''import java.net.URLDecoder
import org.apache.commons.lang3.StringEscapeUtils
def raw = vars.get(args)
if (!raw || raw == 'NOT_FOUND') { vars.put('iteration_failed','true'); return }
def decoded = StringEscapeUtils.unescapeHtml4(URLDecoder.decode(raw, 'UTF-8'))
def parts = decoded.split('~', -1)
def prefix = args == 'charge1_raw' ? 'charge1_' : 'charge2_'
if (parts.size() < 2) { vars.put('iteration_failed','true'); return }
vars.put(prefix + 'code', parts[0])
vars.put(prefix + 'description', parts[1])'''


OBJECT_PAYLOAD = r'''import java.nio.charset.StandardCharsets
import java.util.Base64
char stx = (char)0x02
char etx = (char)0x03
def v = { String n -> vars.get(n) }
def p = "ALLCONTACT:CONTACT:person_id#${v('victim_person_id')}#|contact_id#${v('victim_contact_id')}#|location_id#${v('victim_location_id')}#" + etx +
        "VEHICLE::vehicle_id#${v('vehicle_id')}#VEHICLE|case_vehicle_id#${v('case_vehicle_id')}#" + etx +
        "NJS::inv_njs_id#${v('inv_njs_id_1')}#" + stx + "inv_njs_id#${v('inv_njs_id_2')}#" + etx +
        "LOCATION::location_id#${v('case_location_id')}#LOCATION" + etx +
        "CASE:CASE:case_id#${v('case_id')}#|cfs_id#${v('cfs_id')}#|location_id#${v('case_location_id')}#CASE|org_id#${v('org_id')}#ORG"
def d = "ALLCONTACT:CONTACT:person_id:${v('victim_person_id')}:person_id#${v('victim_person_id')}#|contact_id#${v('victim_contact_id')}#|location_id#${v('victim_location_id')}#" + stx +
        "VEHICLE::vehicle_id:${v('vehicle_id')}:vehicle_id#${v('vehicle_id')}#VEHICLE|case_vehicle_id#${v('case_vehicle_id')}#" + stx +
        "NJS::inv_njs_id:${v('inv_njs_id_1')}:inv_njs_id#${v('inv_njs_id_1')}#" + stx +
        "NJS::inv_njs_id:${v('inv_njs_id_2')}:inv_njs_id#${v('inv_njs_id_2')}#" + stx +
        "LOCATION::location_id:${v('case_location_id')}:location_id#${v('case_location_id')}#LOCATION" + stx +
        "CASE:CASE:case_id:${v('case_id')}:case_id#${v('case_id')}#|cfs_id#${v('cfs_id')}#|location_id#${v('case_location_id')}#CASE|org_id#${v('org_id')}#ORG"
vars.put('objects_parameter', Base64.encoder.encodeToString(p.getBytes(StandardCharsets.UTF_8)))
vars.put('objects_data_index', Base64.encoder.encodeToString(d.getBytes(StandardCharsets.UTF_8)))'''


def decorate_sampler(sid: int, sh: ET.Element) -> None:
    def add(e): pair(sh, e)
    if sid == 1:
        add(css_extractor("login_csrf", "input[name='__RequestVerificationToken']")); add(jsr_check("login_csrf"))
    elif sid == 2:
        add(css_extractor("disclaimer_csrf", "input[name='__RequestVerificationToken']", scope="all")); add(jsr_check("disclaimer_csrf"))
    elif sid == 11:
        add(uniform_timer("Think Time - Open Inbox")); add(jsr223("JSR223PreProcessor", "Initialize Per-Report Runtime Values", INIT_SCRIPT))
        add(regex_extractor("case_id", r"inquireIncidentSummary(?:&amp;|&)case_id=(\d+)", match="0"))
        add(jsr223("JSR223PostProcessor", "Check case_id", CORRELATION_CHECK).append(string("parameters", "case_id")) if False else jsr_check("case_id"))
    elif sid == 12:
        add(css_extractor("incident_csrf", "input[name='__RequestVerificationToken']"))
        add(jsr_check("incident_csrf"))
    elif sid == 14:
        add(uniform_timer("Think Time - Open Police Reports"))
        add(css_extractor("police_csrf", "input[name='__RequestVerificationToken']"))
        add(css_extractor("police_doubleEntryTimeStamp", "input[name='doubleEntryTimeStamp']"))
        add(jsr_check("police_csrf,police_doubleEntryTimeStamp"))
    elif sid == 16:
        add(regex_extractor("FormGUID", r"(?i)Location:\s*[^\r\n]*[?&]FormGUID=([^&\r\n]+)", headers=True, scope="all"))
        add(css_extractor("middle_csrf", "input[name='__RequestVerificationToken']", scope="all"))
        add(regex_extractor("case_location_id", r'name="master_id_list~\|list~\|D"[^>]*objectname="master_id_list"[^>]*value="location_id#([0-9]+)#LOCATION"', scope="all"))
        add(regex_extractor("cfs_id", r'name="master_id_list~\|list~\|D"[^>]*objectname="master_id_list"[^>]*value="case_id#[0-9]+#\|cfs_id#([0-9]+)#', scope="all"))
        add(regex_extractor("org_id", r'name="master_id_list~\|list~\|D"[^>]*objectname="master_id_list"[^>]*value="case_id#[0-9]+#\|cfs_id#[0-9]+#\|location_id#[0-9]+#CASE\|org_id#([0-9]+)#ORG"', scope="all"))
        add(jsr_check("FormGUID,middle_csrf,case_location_id,cfs_id,org_id"))
    elif sid == 22:
        add(uniform_timer("Think Time - Add Victim")); add(css_extractor("victim_csrf", "input[name='__RequestVerificationToken']"))
        add(css_extractor("victim_doubleEntryTimeStamp", "input[name='doubleEntryTimeStamp']"))
        add(regex_extractor("mapping_key", r"sessionStorage\.setItem\(\"MappingKey\",\s*\"([^\"]+)\""))
        add(jsr_check("victim_csrf,victim_doubleEntryTimeStamp,mapping_key"))
    elif sid == 39:
        add(json_extractor("geo_location_id", "$.addressList[?(@.street1 == '6 ACORN BLVD')].id"))
        add(json_extractor("geo_longitude", "$.addressList[?(@.street1 == '6 ACORN BLVD')].longitude"))
        add(json_extractor("geo_latitude", "$.addressList[?(@.street1 == '6 ACORN BLVD')].latitude"))
        add(json_extractor("geo_municipality", "$.addressList[?(@.street1 == '6 ACORN BLVD')].municipality"))
        add(jsr_check("geo_location_id,geo_longitude,geo_latitude,geo_municipality"))
    elif sid == 44:
        add(regex_extractor("victim_person_id", r"master_id_list[^>]+value=\"person_id#(\d+)#"))
        add(regex_extractor("victim_contact_id", r"master_id_list[^>]+value=\"person_id#\d+#\|contact_id#(\d+)#"))
        add(regex_extractor("victim_location_id", r"master_id_list[^>]+value=\"person_id#\d+#\|contact_id#\d+#\|location_id#(\d+)#"))
        add(jsr_check("victim_person_id,victim_contact_id,victim_location_id"))
    elif sid == 45:
        add(uniform_timer("Think Time - Add Vehicle")); add(css_extractor("vehicle_csrf", "input[name='__RequestVerificationToken']"))
        add(css_extractor("vehicle_doubleEntryTimeStamp", "input[name='doubleEntryTimeStamp']")); add(jsr_check("vehicle_csrf,vehicle_doubleEntryTimeStamp"))
    elif sid == 53:
        add(regex_extractor("vehicle_id", r"master_id_list[^>]+value=\"vehicle_id#(\d+)#"))
        add(regex_extractor("case_vehicle_id", r"master_id_list[^>]+value=\"vehicle_id#\d+#VEHICLE\|case_vehicle_id#(\d+)#"))
        add(jsr_check("vehicle_id,case_vehicle_id"))
    elif sid == 54:
        add(uniform_timer("Think Time - Add Charges")); add(css_extractor("charge_csrf", "input[name='__RequestVerificationToken']"))
        add(css_extractor("charge_doubleEntryTimeStamp", "input[name='doubleEntryTimeStamp']")); add(jsr_check("charge_csrf,charge_doubleEntryTimeStamp"))
    elif sid in (55, 56):
        ref = "charge1_raw" if sid == 55 else "charge2_raw"
        add(regex_extractor(ref, r"name=\"return_value~\|list~\|D\"[^>]+value=\"([^\"]+)\"", match="0"))
        pp = jsr223("JSR223PostProcessor", f"Decode {ref}", CHARGE_DECODE)
        for p in pp.findall("stringProp"):
            if p.get("name") == "parameters": p.text = ref
        add(pp); add(jsr_check(("charge1_code,charge1_description" if sid == 55 else "charge2_code,charge2_description")))
    elif sid == 58:
        add(regex_extractor("inv_njs_id", r"objectname=\"inv_njs_id\"[^>]+value=\"(\d+)\"", match="-1"))
        add(jsr_check("inv_njs_id_1,inv_njs_id_2"))
    elif sid == 59:
        add(uniform_timer("Think Time - Create Incident Report")); add(jsr223("JSR223PreProcessor", "Build STX ETX Intake Object Payload", OBJECT_PAYLOAD))
        add(json_extractor("report_id", "$.report_id")); add(jsr_check("report_id"))
        add(json_assertion("CreateIntake Message OK", "$.message", "OK", False))
        add(json_assertion("CreateIntake Report ID Is Positive Integer", "$.report_id", "^[1-9][0-9]*$", True))
    elif sid == 60:
        add(css_extractor("intake_csrf", "input[name='__RequestVerificationToken']")); add(jsr_check("intake_csrf"))
    elif sid == 84:
        add(uniform_timer("Think Time - Save Incident Report"))
        add(response_assertion("Auto Confirm HTTP 200", "Assertion.response_code", "200", 8))
        add(response_assertion("Auto Confirm Body WF", "Assertion.response_data", r"(?s)^\s*WF\s*$", 1))
    elif sid == 85:
        add(css_extractor("workflow_csrf", "input[name='__RequestVerificationToken']")); add(jsr_check("workflow_csrf"))
    elif sid == 89:
        add(css_extractor("final_police_csrf", "input[name='__RequestVerificationToken']")); add(jsr_check("final_police_csrf"))


def jsr_check(names: str) -> ET.Element:
    e = jsr223("JSR223PostProcessor", f"Correlation Check - {names}", CORRELATION_CHECK)
    for p in e.findall("stringProp"):
        if p.get("name") == "parameters": p.text = names
    return e


GROUPS = [
    ("Login and Disclaimer", [1, 2, 6, 7, 9, 10]),
    ("Select Active Case", [11, 12, 13]),
    ("Open New Incident Report", [14, 15, 16, 21]),
    ("Add Victim", [22, 27, 28, 29, 32, 33, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44]),
    ("Add Vehicle", [45, 46, 47, 48, 49, 50, 51, 52, 53]),
    ("Add Two PA Charges", [54, 55, 56, 57, 58]),
    ("Create Incident Report", [59, 60, 81]),
    ("Save and Submit Workflow", [84, 85, 86, 87, 88, 89, 90]),
]

LOGIN_CRITICAL_SESSIONS = {1, 2}
BUSINESS_CRITICAL_SESSIONS = {11, 12, 14, 16, 22, 39, 44, 45, 53, 54, 55, 56, 58, 60, 85, 89}


def invoke_base_generator(base: Path) -> None:
    command = [sys.executable, str(GENERATOR), "--build", "--output", str(base), "--validate",
               "--param", "test_plan_name=PA40 Incident Report - 5 Users x 3 Reports",
               "--param", "thread_group_name=Incident Report Users",
               "--param", "concurrency=${__P(concurrency,5)}", "--param", "rampup=${__P(rampup,5)}",
               "--param", "duration=${__P(duration,3600)}", "--param", "on_sample_error=continue",
               "--config", "type=http_defaults,host=${__P(target_host,parms42test.csitech.com)},port=${__P(target_port,443)},protocol=${__P(protocol,https)}",
               "--config", "type=cookie_manager", "--config", "type=cache_manager",
               "--config", f"type=csv_data_set,filename={CSV},variable_names=username|password|staff_id|region_id",
               "--http-sampler", "name=GET /RMS/Login,path=/RMS/Login,method=GET"]
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    if not SAZ.exists(): raise FileNotFoundError(SAZ)
    with tempfile.TemporaryDirectory(prefix="pa40_jmx_") as temp:
        base = Path(temp) / "base.jmx"
        invoke_base_generator(base)
        tree = ET.parse(base)
    root = tree.getroot()
    test_plan = root.find("./hashTree/TestPlan")
    if test_plan is None: raise RuntimeError("generate_jmx --build did not produce TestPlan")
    test_plan.set("testname", "PA40 Incident Report - 5 Users x 3 Reports")
    set_test_plan_variables(test_plan)
    tp_hash = root.find("./hashTree/hashTree")
    tg = tp_hash.find("ThreadGroup") if tp_hash is not None else None
    if tg is None: raise RuntimeError("generate_jmx --build did not produce ThreadGroup")
    tg.set("testname", "Incident Report Users")
    for p in tg.findall("stringProp"):
        name = p.get("name")
        if name == "ThreadGroup.on_sample_error": p.text = "continue"
        elif name == "ThreadGroup.num_threads": p.text = "${__P(concurrency,5)}"
        elif name == "ThreadGroup.ramp_time": p.text = "${__P(rampup,5)}"
        elif name == "ThreadGroup.duration": tg.remove(p)
    main_lc = tg.find("elementProp[@name='ThreadGroup.main_controller']")
    main_lc.find("boolProp[@name='LoopController.continue_forever']").text = "false"
    main_lc.find("stringProp[@name='LoopController.loops']").text = "1"
    scheduler = tg.find("boolProp[@name='ThreadGroup.scheduler']")
    scheduler.text = "false"
    tg_hash = list(tp_hash)[list(tp_hash).index(tg) + 1]
    tg_hash.clear()
    for cfg in (http_defaults(), cookie_manager(), cache_manager(), csv_data_set(),
                header_manager([("Accept-Language", "en-US,en;q=0.9"),
                                ("User-Agent", "Apache-JMeter PA40 Incident Performance Test")], "Global HTTP Headers")):
        pair(tg_hash, cfg)

    with zipfile.ZipFile(SAZ) as zf:
        login_tree = pair(tg_hash, once_controller())
        login_tx = pair(login_tree, transaction(GROUPS[0][0]))
        for sid in GROUPS[0][1]:
            sampler, sh = build_sampler(zf, sid); decorate_sampler(sid, sh); pair(login_tx, sampler, sh)
            if sid in LOGIN_CRITICAL_SESSIONS:
                add_login_stop_check(login_tx)

        loop_tree = pair(tg_hash, loop_controller())
        for name, sessions in GROUPS[1:]:
            tx_tree = pair(loop_tree, transaction(name))
            for sid in sessions:
                sampler, sh = build_sampler(zf, sid); decorate_sampler(sid, sh); pair(tx_tree, sampler, sh)
                if sid == 59:
                    add_assertion_failure_gate(tx_tree, "Gate Failed CreateIntake Assertion", True)
                elif sid == 84:
                    add_assertion_failure_gate(tx_tree, "Gate Failed Auto Confirm Assertion")
                elif sid in BUSINESS_CRITICAL_SESSIONS:
                    add_abort_check(tx_tree)

        validate_extractors_against_saz(root, zf)

    pair(tg_hash, result_collector())
    validate_arguments_and_http_defaults(root)
    validate_control_flow_and_assertions(root)
    ET.indent(tree, space="  ")
    OUTPUT.write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True))
    print(f"Generated {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
