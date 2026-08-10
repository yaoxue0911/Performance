#!/usr/bin/env python3
"""Build the RI concurrent user-password-change JMeter plan from the SAZ."""

from __future__ import annotations

import re
import urllib.parse
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SAZ = ROOT / "RI change user password.saz"
OUTPUT = ROOT / "Output" / "RI_Change_User_Password.jmx"


def sp(name: str, value: str = "") -> ET.Element:
    node = ET.Element("stringProp", {"name": name})
    node.text = value
    return node


def bp(name: str, value: bool) -> ET.Element:
    node = ET.Element("boolProp", {"name": name})
    node.text = "true" if value else "false"
    return node


def pair(parent: ET.Element, element: ET.Element) -> ET.Element:
    parent.append(element)
    tree = ET.Element("hashTree")
    parent.append(tree)
    return tree


def java_hash(value: str) -> str:
    result = 0
    for character in value:
        result = (31 * result + ord(character)) & 0xFFFFFFFF
    if result >= 0x80000000:
        result -= 0x100000000
    return str(result)


def read_request_params(session: int) -> list[tuple[str, str]]:
    with zipfile.ZipFile(SAZ) as archive:
        raw = archive.read(f"raw/{session:02d}_c.txt").decode("utf-8", "replace")
    _, separator, body = raw.partition("\r\n\r\n")
    if not separator:
        _, _, body = raw.partition("\n\n")
    return urllib.parse.parse_qsl(body, keep_blank_values=True)


def replace_params(
    captured: list[tuple[str, str]], replacements: dict[str, str]
) -> list[tuple[str, str]]:
    return [(name, replacements.get(name, value)) for name, value in captured]


def argument(name: str, value: str) -> ET.Element:
    node = ET.Element("elementProp", {"name": name, "elementType": "HTTPArgument"})
    node.extend(
        [
            bp("HTTPArgument.always_encode", True),
            sp("Argument.value", value),
            sp("Argument.metadata", "="),
            bp("HTTPArgument.use_equals", True),
            sp("Argument.name", name),
        ]
    )
    return node


def sampler(name: str, path: str, method: str, params=None) -> ET.Element:
    node = ET.Element(
        "HTTPSamplerProxy",
        {
            "guiclass": "HttpTestSampleGui",
            "testclass": "HTTPSamplerProxy",
            "testname": name,
            "enabled": "true",
        },
    )
    arguments = ET.Element(
        "elementProp",
        {
            "name": "HTTPsampler.Arguments",
            "elementType": "Arguments",
            "guiclass": "HTTPArgumentsPanel",
            "testclass": "Arguments",
            "enabled": "true",
        },
    )
    collection = ET.SubElement(arguments, "collectionProp", {"name": "Arguments.arguments"})
    for param_name, param_value in params or []:
        collection.append(argument(param_name, param_value))
    node.extend(
        [
            arguments,
            sp("HTTPSampler.domain"),
            sp("HTTPSampler.port"),
            sp("HTTPSampler.protocol"),
            sp("HTTPSampler.contentEncoding", "UTF-8"),
            sp("HTTPSampler.path", path),
            sp("HTTPSampler.method", method),
            bp("HTTPSampler.follow_redirects", True),
            bp("HTTPSampler.auto_redirects", False),
            bp("HTTPSampler.use_keepalive", True),
            bp("HTTPSampler.DO_MULTIPART_POST", False),
            bp("HTTPSampler.postBodyRaw", False),
            sp("HTTPSampler.embedded_url_re"),
            sp("HTTPSampler.connect_timeout", "${__P(connect_timeout,10000)}"),
            sp("HTTPSampler.response_timeout", "${__P(response_timeout,30000)}"),
        ]
    )
    return node


def header_manager(name: str, headers: list[tuple[str, str]]) -> ET.Element:
    node = ET.Element(
        "HeaderManager",
        {
            "guiclass": "HeaderPanel",
            "testclass": "HeaderManager",
            "testname": name,
            "enabled": "true",
        },
    )
    collection = ET.SubElement(node, "collectionProp", {"name": "HeaderManager.headers"})
    for header_name, value in headers:
        header = ET.SubElement(collection, "elementProp", {"name": "", "elementType": "Header"})
        header.extend([sp("Header.name", header_name), sp("Header.value", value)])
    return node


def add_headers(tree: ET.Element, name: str, headers: list[tuple[str, str]]) -> None:
    pair(tree, header_manager(name, headers))


def css_extractor(
    refname: str, selector: str, *, scope: str = "parent", default: str = "NOT_FOUND"
) -> ET.Element:
    node = ET.Element(
        "HtmlExtractor",
        {
            "guiclass": "HtmlExtractorGui",
            "testclass": "HtmlExtractor",
            "testname": f"CSS Extractor - {refname}",
            "enabled": "true",
        },
    )
    node.extend(
        [
            sp("HtmlExtractor.refname", refname),
            sp("HtmlExtractor.expr", selector),
            sp("HtmlExtractor.attribute", "value"),
            sp("HtmlExtractor.default", default),
            bp("HtmlExtractor.default_empty_value", False),
            sp("HtmlExtractor.match_number", "1"),
            sp("Sample.scope", scope),
        ]
    )
    return node


def regex_extractor(refname: str, regex: str) -> ET.Element:
    node = ET.Element(
        "RegexExtractor",
        {
            "guiclass": "RegexExtractorGui",
            "testclass": "RegexExtractor",
            "testname": f"Random search-result user - {refname}",
            "enabled": "true",
        },
    )
    node.extend(
        [
            bp("RegexExtractor.useHeaders", False),
            sp("RegexExtractor.refname", refname),
            sp("RegexExtractor.regex", regex),
            sp("RegexExtractor.template", "$1$"),
            sp("RegexExtractor.default", "NOT_FOUND"),
            sp("RegexExtractor.match_number", "0"),
            sp("Sample.scope", "all"),
        ]
    )
    return node


def user_parameters() -> ET.Element:
    values = [
        ("new_password", "RhodeIsland2024!${__Random(100,999,)}"),
        ("request_rnd", "${__Random(100000000,999999999,)}"),
    ]
    node = ET.Element(
        "UserParameters",
        {
            "guiclass": "UserParametersGui",
            "testclass": "UserParameters",
            "testname": "Generate password and request cache-buster per iteration",
            "enabled": "true",
        },
    )
    names = ET.SubElement(node, "collectionProp", {"name": "UserParameters.names"})
    thread_values = ET.SubElement(
        node, "collectionProp", {"name": "UserParameters.thread_values"}
    )
    row = ET.SubElement(thread_values, "collectionProp", {"name": java_hash("password values")})
    for variable, value in values:
        names.append(sp(java_hash(variable), variable))
        row.append(sp(java_hash(variable + value), value))
    node.append(bp("UserParameters.per_iteration", True))
    return node


def transaction(name: str) -> ET.Element:
    node = ET.Element(
        "TransactionController",
        {
            "guiclass": "TransactionControllerGui",
            "testclass": "TransactionController",
            "testname": name,
            "enabled": "true",
        },
    )
    node.extend(
        [
            bp("TransactionController.include_timers", False),
            bp("TransactionController.parent", True),
        ]
    )
    return node


def add_sampler(
    tree: ET.Element,
    name: str,
    path: str,
    method: str,
    params=None,
    headers=None,
    extractors=None,
) -> None:
    sampler_tree = pair(tree, sampler(name, path, method, params))
    if headers:
        add_headers(sampler_tree, f"Headers - {name}", headers)
    for extractor in extractors or []:
        pair(sampler_tree, extractor)


def http_defaults() -> ET.Element:
    node = ET.Element(
        "ConfigTestElement",
        {
            "guiclass": "HttpDefaultsGui",
            "testclass": "ConfigTestElement",
            "testname": "HTTP Request Defaults",
            "enabled": "true",
        },
    )
    arguments = ET.Element(
        "elementProp",
        {
            "name": "HTTPsampler.Arguments",
            "elementType": "Arguments",
            "guiclass": "HTTPArgumentsPanel",
            "testclass": "Arguments",
            "enabled": "true",
        },
    )
    ET.SubElement(arguments, "collectionProp", {"name": "Arguments.arguments"})
    node.extend(
        [
            arguments,
            sp("HTTPSampler.domain", "${__P(target_host,rirmsint.csitech.com)}"),
            sp("HTTPSampler.port", "${__P(target_port,443)}"),
            sp("HTTPSampler.protocol", "${__P(protocol,https)}"),
            sp("HTTPSampler.contentEncoding", "UTF-8"),
            sp("HTTPSampler.path"),
            sp("HTTPSampler.concurrentPool", "6"),
            bp("HTTPSampler.embedded_url_re", False),
        ]
    )
    return node


def result_collector() -> ET.Element:
    node = ET.Element(
        "ResultCollector",
        {
            "guiclass": "SimpleDataWriter",
            "testclass": "ResultCollector",
            "testname": "Write performance results to JTL",
            "enabled": "true",
        },
    )
    node.append(bp("ResultCollector.error_logging", False))
    obj = ET.SubElement(node, "objProp")
    ET.SubElement(obj, "name").text = "saveConfig"
    value = ET.SubElement(obj, "value", {"class": "SampleSaveConfiguration"})
    settings = {
        "time": True,
        "latency": True,
        "timestamp": True,
        "success": True,
        "label": True,
        "code": True,
        "message": True,
        "threadName": True,
        "dataType": True,
        "encoding": False,
        "assertions": False,
        "subresults": True,
        "responseData": False,
        "samplerData": False,
        "xml": False,
        "fieldNames": True,
        "responseHeaders": False,
        "requestHeaders": False,
        "responseDataOnError": False,
        "saveAssertionResultsFailureMessage": True,
        "bytes": True,
        "sentBytes": True,
        "url": True,
        "threadCounts": True,
        "idleTime": True,
        "connectTime": True,
    }
    for setting, enabled in settings.items():
        ET.SubElement(value, setting).text = "true" if enabled else "false"
    ET.SubElement(value, "assertionsResultsToSave").text = "0"
    node.append(sp("filename", "${__P(result_file,Output/RI_Change_User_Password.jtl)}"))
    return node


def build() -> ET.ElementTree:
    login_params = replace_params(
        read_request_params(2),
        {
            "__VIEWSTATE": "${login_viewstate}",
            "__VIEWSTATEGENERATOR": "${login_viewstate_generator}",
        },
    )
    disclaimer_params = replace_params(
        read_request_params(5),
        {
            "__VIEWSTATE": "${index_viewstate}",
            "__VIEWSTATEGENERATOR": "${index_viewstate_generator}",
            "__EVENTVALIDATION": "${index_event_validation}",
        },
    )
    search_params = replace_params(
        read_request_params(12),
        {
            "__VIEWSTATE": "${search_viewstate}",
            "__VIEWSTATEGENERATOR": "${search_viewstate_generator}",
            "ctl00$ContentPlaceHolder1$ctl00$doubleEntryTimeStamp": "${search_double_entry_timestamp}",
        },
    )
    update_params = replace_params(
        read_request_params(21),
        {
            "__VIEWSTATE": "${update_viewstate}",
            "__VIEWSTATEGENERATOR": "${update_viewstate_generator}",
            "__EVENTVALIDATION": "${update_event_validation}",
            "ctl00$ContentPlaceHolder1$ctl00$login_id~|authen_update~|E": "${selected_login_id}",
            "ctl00$ContentPlaceHolder1$ctl00$pwd~|authen_update~|E": "${new_password}",
            "ctl00$ContentPlaceHolder1$ctl00$staff_id~|authen_update~|D": "${selected_staff_id}",
            "ctl00$ContentPlaceHolder1$ctl00$login_status~|authen_update~|E": "${selected_login_status}",
            "ctl00$ContentPlaceHolder1$ctl00$doubleEntryTimeStamp": "${update_double_entry_timestamp}",
        },
    )

    root = ET.Element(
        "jmeterTestPlan", {"version": "1.2", "properties": "5.0", "jmeter": "5.4.1"}
    )
    root_tree = ET.SubElement(root, "hashTree")
    plan = ET.Element(
        "TestPlan",
        {
            "guiclass": "TestPlanGui",
            "testclass": "TestPlan",
            "testname": "RI Concurrent Random User Password Change",
            "enabled": "true",
        },
    )
    plan.extend(
        [
            sp(
                "TestPlan.comments",
                "Generates concurrent RMS password-change load. Monitor other applications externally for impact. No assertions by request.",
            ),
            bp("TestPlan.functional_mode", False),
            bp("TestPlan.tearDown_on_shutdown", True),
            bp("TestPlan.serialize_threadgroups", False),
        ]
    )
    variables = ET.Element(
        "elementProp",
        {
            "name": "TestPlan.user_defined_variables",
            "elementType": "Arguments",
            "guiclass": "ArgumentsPanel",
            "testclass": "Arguments",
            "testname": "User Defined Variables",
            "enabled": "true",
        },
    )
    ET.SubElement(variables, "collectionProp", {"name": "Arguments.arguments"})
    plan.extend([variables, sp("TestPlan.user_define_classpath")])
    plan_tree = pair(root_tree, plan)

    thread_group = ET.Element(
        "ThreadGroup",
        {
            "guiclass": "ThreadGroupGui",
            "testclass": "ThreadGroup",
            "testname": "Concurrent password changes",
            "enabled": "true",
        },
    )
    controller = ET.Element(
        "elementProp",
        {
            "name": "ThreadGroup.main_controller",
            "elementType": "LoopController",
            "guiclass": "LoopControlPanel",
            "testclass": "LoopController",
            "testname": "Loop Controller",
            "enabled": "true",
        },
    )
    controller.extend([bp("LoopController.continue_forever", False), sp("LoopController.loops", "-1")])
    thread_group.extend(
        [
            sp("ThreadGroup.on_sample_error", "continue"),
            controller,
            sp("ThreadGroup.num_threads", "${__P(concurrency,10)}"),
            sp("ThreadGroup.ramp_time", "${__P(rampup,10)}"),
            bp("ThreadGroup.scheduler", True),
            sp("ThreadGroup.duration", "${__P(duration,60)}"),
            sp("ThreadGroup.delay", "${__P(delay,0)}"),
            bp("ThreadGroup.same_user_on_next_iteration", True),
        ]
    )
    tg_tree = pair(plan_tree, thread_group)

    pair(tg_tree, http_defaults())
    cookie = ET.Element(
        "CookieManager",
        {
            "guiclass": "CookiePanel",
            "testclass": "CookieManager",
            "testname": "Per-thread RMS cookies",
            "enabled": "true",
        },
    )
    ET.SubElement(cookie, "collectionProp", {"name": "CookieManager.cookies"})
    cookie.extend([bp("CookieManager.clearEachIteration", False), bp("CookieManager.controlledByThreadGroup", True)])
    pair(tg_tree, cookie)
    cache = ET.Element(
        "CacheManager",
        {
            "guiclass": "CacheManagerGui",
            "testclass": "CacheManager",
            "testname": "HTTP Cache Manager",
            "enabled": "true",
        },
    )
    cache.extend([bp("clearEachIteration", False), bp("useExpires", True), sp("maxCacheSize", "5000")])
    pair(tg_tree, cache)
    pair(
        tg_tree,
        header_manager(
            "Common browser headers",
            [
                ("Accept-Language", "en-US,en;q=0.9"),
                ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
                (
                    "User-Agent",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/150.0.0.0 Safari/537.36",
                ),
            ],
        ),
    )

    once = ET.Element(
        "OnceOnlyController",
        {
            "guiclass": "OnceOnlyControllerGui",
            "testclass": "OnceOnlyController",
            "testname": "Login and initialize RMS once per thread",
            "enabled": "true",
        },
    )
    once_tree = pair(tg_tree, once)
    login_tree = pair(once_tree, transaction("Login and initialize session"))
    base = "${__P(protocol,https)}://${__P(target_host,rirmsint.csitech.com)}"
    add_sampler(
        login_tree,
        "GET /RMS/Login.aspx",
        "/RMS/Login.aspx",
        "GET",
        headers=[("Referer", f"{base}/RMS/Login.aspx"), ("Upgrade-Insecure-Requests", "1")],
        extractors=[
            css_extractor("login_viewstate", "input#__VIEWSTATE"),
            css_extractor("login_viewstate_generator", "input#__VIEWSTATEGENERATOR"),
        ],
    )
    add_sampler(
        login_tree,
        "POST /RMS/Login.aspx",
        "/RMS/Login.aspx",
        "POST",
        params=login_params,
        headers=[
            ("Content-Type", "application/x-www-form-urlencoded"),
            ("Origin", base),
            ("Referer", f"{base}/RMS/Login.aspx"),
            ("Upgrade-Insecure-Requests", "1"),
        ],
        extractors=[
            css_extractor("index_viewstate", "input#__VIEWSTATE", scope="all"),
            css_extractor("index_viewstate_generator", "input#__VIEWSTATEGENERATOR", scope="all"),
            css_extractor("index_event_validation", "input#__EVENTVALIDATION", scope="all"),
        ],
    )
    add_sampler(
        login_tree,
        "GET /RMS/AspSoft/Disclaimer/Disclaimer.htm",
        "/RMS/AspSoft/Disclaimer/Disclaimer.htm?rnd=0.07606956060256631",
        "GET",
        headers=[("Referer", f"{base}/RMS/Index.aspx")],
    )
    add_sampler(
        login_tree,
        "POST /RMS/DisclaimerRedirect.aspx",
        "/RMS/DisclaimerRedirect.aspx?division_id=3",
        "POST",
        params=disclaimer_params,
        headers=[
            ("Content-Type", "application/x-www-form-urlencoded"),
            ("Origin", base),
            ("Referer", f"{base}/RMS/Index.aspx"),
            ("Upgrade-Insecure-Requests", "1"),
        ],
    )
    add_sampler(
        login_tree,
        "GET /RMS/HomeA.aspx",
        "/RMS/HomeA.aspx?division_id=3",
        "GET",
        headers=[("Referer", f"{base}/RMS/Index.aspx")],
    )

    pair(tg_tree, user_parameters())
    business_tree = pair(tg_tree, transaction("Search random user and change password"))
    add_sampler(
        business_tree,
        "GET /RMS/aspsoft/dispatcher.aspx - searchUser",
        "/RMS/aspsoft/dispatcher.aspx?nextPID=searchUser",
        "GET",
        headers=[("Referer", f"{base}/RMS/HomeA.aspx")],
        extractors=[
            css_extractor("search_viewstate", "input#__VIEWSTATE"),
            css_extractor("search_viewstate_generator", "input#__VIEWSTATEGENERATOR"),
            css_extractor(
                "search_double_entry_timestamp",
                "input#ctl00_ContentPlaceHolder1_ctl00_doubleEntryTimeStamp",
            ),
        ],
    )
    add_sampler(
        business_tree,
        "POST /RMS/aspsoft/dispatcher.aspx - searchUser",
        "/RMS/aspsoft/dispatcher.aspx?nextPID=searchUser",
        "POST",
        params=search_params,
        headers=[
            ("Content-Type", "application/x-www-form-urlencoded"),
            ("Origin", base),
            ("Referer", f"{base}/RMS/aspsoft/dispatcher.aspx?nextPID=searchUser"),
            ("Upgrade-Insecure-Requests", "1"),
        ],
        extractors=[
            regex_extractor(
                "selected_staff_id",
                r"Dispatcher\.aspx\?staff_id=([0-9]+)&amp;nextPID=inquireUser",
            )
        ],
    )
    inquire_path = "/RMS/AspSoft/Dispatcher.aspx?staff_id=${selected_staff_id}&nextPID=inquireUser"
    add_sampler(
        business_tree,
        "GET /RMS/AspSoft/Dispatcher.aspx - inquireUser",
        inquire_path,
        "GET",
        headers=[("Referer", f"{base}/RMS/AspSoft/Dispatcher.aspx?PID=searchUser&nextPID=listUser")],
    )
    update_path = (
        "/RMS/AspSoft/PopUpDispatcher.aspx?staff_id=${selected_staff_id}"
        "&nextPID=updateUser&rnd=${request_rnd}"
    )
    add_sampler(
        business_tree,
        "GET /RMS/AspSoft/PopUpDispatcher.aspx - updateUser",
        update_path,
        "GET",
        headers=[("Referer", f"{base}{inquire_path}")],
        extractors=[
            css_extractor("update_viewstate", "input#__VIEWSTATE"),
            css_extractor("update_viewstate_generator", "input#__VIEWSTATEGENERATOR"),
            css_extractor("update_event_validation", "input#__EVENTVALIDATION"),
            css_extractor("selected_login_id", 'input[ObjectName="login_id"]'),
            css_extractor("selected_login_status", 'input[ObjectName="login_status"]'),
            css_extractor(
                "update_double_entry_timestamp",
                "input#ctl00_ContentPlaceHolder1_ctl00_doubleEntryTimeStamp",
            ),
        ],
    )
    add_sampler(
        business_tree,
        "POST /RMS/AspSoft/PopUpDispatcher.aspx - updateUser",
        update_path,
        "POST",
        params=update_params,
        headers=[
            ("Content-Type", "application/x-www-form-urlencoded"),
            ("Origin", base),
            ("Referer", f"{base}{update_path}"),
            ("Upgrade-Insecure-Requests", "1"),
        ],
    )
    add_sampler(
        business_tree,
        "GET /RMS/AspSoft/Dispatcher.aspx - refresh inquireUser",
        inquire_path,
        "GET",
        headers=[("Referer", f"{base}{inquire_path}")],
    )
    pair(plan_tree, result_collector())
    return ET.ElementTree(root)


def validate(tree: ET.ElementTree) -> None:
    root = tree.getroot()
    forbidden = {
        "ResponseAssertion",
        "JSONPathAssertion",
        "DurationAssertion",
        "XPathAssertion",
        "HTMLAssertion",
        "SizeAssertion",
    }
    present = {node.tag for node in root.iter()} & forbidden
    if present:
        raise RuntimeError(f"Assertions are forbidden: {sorted(present)}")
    samplers = list(root.iter("HTTPSamplerProxy"))
    if len(samplers) != 11:
        raise RuntimeError(f"Expected 11 HTTP samplers, found {len(samplers)}")
    for sample in samplers:
        follow = sample.find("./boolProp[@name='HTTPSampler.follow_redirects']")
        if follow is None or follow.text != "true":
            raise RuntimeError(f"Follow redirects disabled for {sample.get('testname')}")
    regex = root.find(".//RegexExtractor[stringProp='selected_staff_id']")
    if regex is None:
        raise RuntimeError("Random selected_staff_id extractor is missing")
    match = regex.find("./stringProp[@name='RegexExtractor.match_number']")
    scope = regex.find("./stringProp[@name='Sample.scope']")
    if match is None or match.text != "0" or scope is None or scope.text != "all":
        raise RuntimeError("selected_staff_id must use Match No 0 with all-sample scope")
    xml_text = ET.tostring(root, encoding="unicode")
    for forbidden_text in ("signalr", "GetAllIncomingCallCount", "GetCfsParTimerCount", "DebugService", "EngineService"):
        if forbidden_text in xml_text:
            raise RuntimeError(f"Background/non-business traffic leaked into plan: {forbidden_text}")
    if "RhodeIsland2024!${__Random(100,999,)}" not in xml_text:
        raise RuntimeError("Required three-digit random password expression is missing")
    if "staff_region_id~|~|A" not in xml_text or ">104900<" not in xml_text:
        raise RuntimeError("Captured search criteria were not preserved")


def main() -> None:
    if not SAZ.exists():
        raise SystemExit(f"SAZ not found: {SAZ}")
    tree = build()
    validate(tree)
    ET.indent(tree, space="  ")
    tree.write(OUTPUT, encoding="UTF-8", xml_declaration=True)
    ET.parse(OUTPUT)
    print(f"Generated {OUTPUT}")


if __name__ == "__main__":
    main()
