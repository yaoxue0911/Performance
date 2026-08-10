#!/usr/bin/env python3
"""Generate the approved RI Person/Property lock-contention JMX.

The repository ``generate_jmx.py --build`` command creates the base JMeter
document.  This one-time assembler then uses its ``JMXComponentBuilder`` for
all supported elements.  Focused XML helpers are required because the bundled
builder cannot express two independently nested Thread Groups, CSS extractors,
User Parameters, sampler-scoped timers, or ``always_encode=true`` arguments.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import tempfile
import urllib.parse
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "Output" / "RI_Add_Person_Property_Deadlock.jmx"
SAZ = ROOT / "RI_add person and property.saz"
REPOSITORY_GENERATOR = (
    ROOT
    / "AI Jmx Generator/.agents/skills/jmeter-loader-skills/scripts/generate_jmx.py"
)

CAPTURED_CASE_ID = "2000011166"
CAPTURED_PERSON_ID = "2000137319"
FORBIDDEN_NON_ASSERTION_TAGS = {
    "CSVDataSet",
    "CriticalSectionController",
    "SyncTimer",
    "Synchronizer",
}


def load_repository_generator():
    spec = importlib.util.spec_from_file_location(
        "repository_generate_jmx", REPOSITORY_GENERATOR
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load repository generator: {REPOSITORY_GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REPO = load_repository_generator()
CB = REPO.JMXComponentBuilder
JG = REPO.JMXGenerator


def pair(
    parent: ET.Element, element: ET.Element, children: ET.Element | None = None
) -> ET.Element:
    parent.append(element)
    tree = children if children is not None else ET.Element("hashTree")
    parent.append(tree)
    return tree


def string(name: str, value: str = "") -> ET.Element:
    return CB._string_prop(name, value)


def boolean(name: str, value: bool) -> ET.Element:
    return CB._bool_prop(name, value)


def java_hash(value: str) -> str:
    result = 0
    for character in value:
        result = (31 * result + ord(character)) & 0xFFFFFFFF
    if result >= 0x80000000:
        result -= 0x100000000
    return str(result)


def set_test_plan_variables(test_plan: ET.Element) -> None:
    values = {
        "target_protocol": "https",
        "target_host": "rirmsint.csitech.com",
        "target_port": "443",
        "case_id": "",
        "person_username": "",
        "person_password": "",
        "property_username": "",
        "property_password": "",
    }
    collection = test_plan.find(
        "./elementProp[@name='TestPlan.user_defined_variables']"
        "/collectionProp[@name='Arguments.arguments']"
    )
    if collection is None:
        raise RuntimeError("Repository generator did not create TestPlan UDV")
    collection.clear()
    collection.set("name", "Arguments.arguments")
    for name, value in values.items():
        argument = CB._element_prop(name, "Argument")
        argument.extend(
            [string("Argument.name", name), string("Argument.value", value), string("Argument.metadata", "=")]
        )
        collection.append(argument)


def invoke_repository_generator(base_path: Path) -> None:
    command = [
        sys.executable,
        str(REPOSITORY_GENERATOR),
        "--build",
        "--output",
        str(base_path),
        "--validate",
        "--param",
        "test_plan_name=RI Same Case Person-Property Lock Contention",
        "--param",
        "thread_group_name=Repository Builder Bootstrap",
        "--param",
        "concurrency=1",
        "--param",
        "rampup=0",
        "--param",
        "duration=60",
        "--param",
        "on_sample_error=continue",
        "--config",
        "type=http_defaults,host=${target_host},port=${target_port},protocol=${target_protocol}",
        "--http-sampler",
        "name=Repository Builder Bootstrap,path=/,method=GET",
    ]
    subprocess.run(command, cwd=ROOT, check=True)


def read_client(zf: zipfile.ZipFile, session_id: int) -> tuple[dict[str, str], str]:
    raw = zf.read(f"raw/{session_id:03d}_c.txt").decode("utf-8", "replace")
    header_text, separator, body = raw.partition("\r\n\r\n")
    if not separator:
        header_text, _, body = raw.partition("\n\n")
    lines = header_text.replace("\r\n", "\n").split("\n")
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" in line:
            name, value = line.split(":", 1)
            headers[name.strip()] = value.strip()
    return headers, body


def session_params(zf: zipfile.ZipFile, session_id: int) -> list[tuple[str, str]]:
    _, body = read_client(zf, session_id)
    return urllib.parse.parse_qsl(body, keep_blank_values=True)


def runtime_value(value: str) -> str:
    return (
        value.replace(CAPTURED_CASE_ID, "${case_id}")
        .replace("\x02", "${__char(2)}")
        .replace("https://rirmsint.csitech.com", "${target_protocol}://${target_host}")
    )


def params_for(
    zf: zipfile.ZipFile,
    session_id: int,
    replacements: dict[str, str] | None = None,
) -> list[tuple[str, str]]:
    replacements = replacements or {}
    result: list[tuple[str, str]] = []
    for name, captured_value in session_params(zf, session_id):
        value = replacements.get(name, runtime_value(captured_value))
        result.append((name, value))
    return result


def request_headers(
    zf: zipfile.ZipFile, session_id: int, rnd_variable: str | None = None
) -> list[dict[str, str]]:
    captured, _ = read_client(zf, session_id)
    keep = {
        "Accept",
        "Content-Type",
        "Origin",
        "Referer",
        "Upgrade-Insecure-Requests",
        "User-Agent",
        "X-Requested-With",
    }
    headers: list[dict[str, str]] = []
    for name, original in captured.items():
        if name not in keep:
            continue
        value = runtime_value(original)
        if rnd_variable:
            value = re.sub(r"([?&](?:MN_)?rnd=)[^&#]+", rf"\1${{{rnd_variable}}}", value)
        headers.append({"name": name, "value": value})
    return headers


def css_extractor(
    refname: str,
    selector: str,
    *,
    attribute: str = "value",
    match_number: str = "1",
    default: str = "NOT_FOUND",
    scope: str = "parent",
) -> ET.Element:
    element = ET.Element(
        "HtmlExtractor",
        {
            "guiclass": "HtmlExtractorGui",
            "testclass": "HtmlExtractor",
            "testname": f"CSS Extractor - {refname}",
            "enabled": "true",
        },
    )
    element.extend(
        [
            string("HtmlExtractor.refname", refname),
            string("HtmlExtractor.expr", selector),
            string("HtmlExtractor.attribute", attribute),
            string("HtmlExtractor.default", default),
            boolean("HtmlExtractor.default_empty_value", False),
            string("HtmlExtractor.match_number", match_number),
            string("Sample.scope", scope),
        ]
    )
    return element


def user_parameters(name: str, values: list[tuple[str, str]]) -> ET.Element:
    element = ET.Element(
        "UserParameters",
        {
            "guiclass": "UserParametersGui",
            "testclass": "UserParameters",
            "testname": name,
            "enabled": "true",
        },
    )
    names = ET.Element("collectionProp", {"name": "UserParameters.names"})
    thread_values = ET.Element(
        "collectionProp", {"name": "UserParameters.thread_values"}
    )
    row = ET.Element("collectionProp", {"name": java_hash(name + " values")})
    for variable, value in values:
        names.append(string(java_hash(variable), variable))
        row.append(string(java_hash(variable + value), value))
    thread_values.append(row)
    element.extend([names, thread_values, boolean("UserParameters.per_iteration", True)])
    return element


def configure_thread_group(
    name: str, threads: str, duration: str = "${__P(duration,60)}"
) -> tuple[ET.Element, ET.Element]:
    group = CB.build_thread_group(
        name=name,
        threads=threads,
        rampup="${__P(rampup,0)}",
        duration=duration,
        loops="1",
        on_sample_error="continue",
        same_user=True,
        delay="0",
    )
    main = group.find("./elementProp[@name='ThreadGroup.main_controller']")
    if main is None:
        raise RuntimeError("Repository ThreadGroup builder omitted main controller")
    continue_forever = main.find("./boolProp[@name='LoopController.continue_forever']")
    if continue_forever is not None:
        continue_forever.text = "false"
    return group, ET.Element("hashTree")


def add_thread_configs(parent: ET.Element, cookie_name: str) -> None:
    defaults = CB.build_http_defaults(
        host="${target_host}",
        port="${target_port}",
        protocol="${target_protocol}",
        encoding="UTF-8",
    )
    pair(parent, defaults)
    cookies = CB.build_cookie_manager(clear_each_iteration=False)
    cookies.set("testname", cookie_name)
    pair(parent, cookies)
    pair(parent, CB.build_cache_manager(clear_each_iteration=False, use_expires=True))
    common = CB.build_header_manager(
        [
            {"name": "Accept-Language", "value": "en-US,en;q=0.9"},
            {
                "name": "User-Agent",
                "value": "Apache-JMeter RI Person-Property Lock Contention Test",
            },
        ]
    )
    common.set("testname", f"{cookie_name} Common Headers")
    pair(parent, common)


def add_postprocessor(parent: ET.Element, processor: ET.Element) -> None:
    pair(parent, processor)


def add_http_sampler(
    parent: ET.Element,
    zf: zipfile.ZipFile,
    session_id: int,
    name: str,
    method: str,
    path: str,
    *,
    params: list[tuple[str, str]] | None = None,
    processors: list[ET.Element] | None = None,
    timer: ET.Element | None = None,
    rnd_variable: str | None = None,
) -> ET.Element:
    dictionaries = (
        [{"name": key, "value": value} for key, value in params]
        if params is not None
        else None
    )
    sampler = CB.build_http_sampler(
        name=name,
        method=method,
        path=path,
        encoding="UTF-8",
        params=dictionaries,
        follow_redirects=True,
        use_keepalive=True,
    )
    for argument in sampler.findall(
        "./elementProp[@name='HTTPsampler.Arguments']/collectionProp/elementProp"
    ):
        always_encode = argument.find("./boolProp[@name='HTTPArgument.always_encode']")
        if always_encode is None:
            argument.insert(0, boolean("HTTPArgument.always_encode", True))
        else:
            always_encode.text = "true"

    children = ET.Element("hashTree")
    if timer is not None:
        pair(children, timer)
    headers = request_headers(zf, session_id, rnd_variable)
    if headers:
        manager = CB.build_header_manager(headers)
        manager.set("testname", f"Headers - {name}")
        pair(children, manager)
    for processor in processors or []:
        add_postprocessor(children, processor)
    pair(parent, sampler, children)
    return sampler


def transaction(parent: ET.Element, name: str) -> ET.Element:
    return pair(parent, CB.build_transaction_controller(name=name, parent=True, include_timers=False))


def once_only(parent: ET.Element, name: str) -> ET.Element:
    element = CB.build_once_only_controller()
    element.set("testname", name)
    return pair(parent, element)


def loop(parent: ET.Element, name: str, loops: str) -> ET.Element:
    element = CB.build_loop_controller(loops=loops)
    element.set("testname", name)
    return pair(parent, element)


def if_controller(parent: ET.Element, name: str, condition: str) -> ET.Element:
    element = CB.build_if_controller(condition=condition, evaluate_all=False)
    element.set("testname", name)
    return pair(parent, element)


def webform_extractors(prefix: str, *, eventvalidation: bool, scope: str) -> list[ET.Element]:
    extractors = [
        css_extractor(f"{prefix}_viewstate", "input#__VIEWSTATE", scope=scope),
        css_extractor(
            f"{prefix}_viewstategenerator", "input#__VIEWSTATEGENERATOR", scope=scope
        ),
    ]
    if eventvalidation:
        extractors.append(
            css_extractor(
                f"{prefix}_eventvalidation", "input#__EVENTVALIDATION", scope=scope
            )
        )
    return extractors


def form_extractors(prefix: str, *, eventvalidation: bool, scope: str) -> list[ET.Element]:
    result = webform_extractors(prefix, eventvalidation=eventvalidation, scope=scope)
    result.append(
        css_extractor(
            f"{prefix}_double_entry_timestamp",
            "input[id$='doubleEntryTimeStamp']",
            scope=scope,
        )
    )
    return result


def add_login_flow(
    parent: ET.Element,
    zf: zipfile.ZipFile,
    *,
    account_prefix: str,
    username_variable: str,
    password_variable: str,
) -> None:
    login_tree = transaction(parent, f"{account_prefix.title()} Account Login")
    add_http_sampler(
        login_tree,
        zf,
        3,
        "GET /RMS/Login.aspx",
        "GET",
        "/RMS/Login.aspx",
        processors=webform_extractors(
            f"login_{account_prefix}", eventvalidation=False, scope="parent"
        ),
    )
    login_params = params_for(
        zf,
        5,
        {
            "__VIEWSTATE": f"${{login_{account_prefix}_viewstate}}",
            "__VIEWSTATEGENERATOR": f"${{login_{account_prefix}_viewstategenerator}}",
            "txtUserName": f"${{{username_variable}}}",
            "txtPassword": f"${{{password_variable}}}",
        },
    )
    add_http_sampler(
        login_tree,
        zf,
        5,
        "POST /RMS/Login.aspx",
        "POST",
        "/RMS/Login.aspx",
        params=login_params,
        processors=webform_extractors(
            f"{account_prefix}_disclaimer", eventvalidation=True, scope="all"
        ),
    )
    add_http_sampler(
        login_tree,
        zf,
        14,
        "GET /RMS/AspSoft/Disclaimer/Disclaimer.htm",
        "GET",
        "/RMS/AspSoft/Disclaimer/Disclaimer.htm?rnd=${__Random(100000000,999999999,)}",
    )
    disclaimer_params = params_for(
        zf,
        15,
        {
            "__VIEWSTATE": f"${{{account_prefix}_disclaimer_viewstate}}",
            "__VIEWSTATEGENERATOR": f"${{{account_prefix}_disclaimer_viewstategenerator}}",
            "__EVENTVALIDATION": f"${{{account_prefix}_disclaimer_eventvalidation}}",
        },
    )
    add_http_sampler(
        login_tree,
        zf,
        15,
        "POST /RMS/DisclaimerRedirect.aspx",
        "POST",
        "/RMS/DisclaimerRedirect.aspx?division_id=3",
        params=disclaimer_params,
    )
    add_http_sampler(
        login_tree,
        zf,
        17,
        "GET /RMS/HomeA.aspx",
        "GET",
        "/RMS/HomeA.aspx?division_id=3",
    )


def add_open_case_flow(
    parent: ET.Element, zf: zipfile.ZipFile, process: str, include_property_list: bool
) -> None:
    tree = transaction(parent, f"Open Case for {process}")
    add_http_sampler(
        tree,
        zf,
        31,
        "GET /RMS/AspSoft/Dispatcher.aspx - Incident Summary",
        "GET",
        "/RMS/AspSoft/Dispatcher.aspx?nextPID=inquireIncidentSummary&case_id=${case_id}",
    )
    add_http_sampler(
        tree,
        zf,
        43,
        "GET /RMS/Aspsoft/Dispatcher.aspx - Case Contacts",
        "GET",
        "/RMS/Aspsoft/Dispatcher.aspx?nextPID=showCaseContact&case_id=${case_id}&division_id=3",
    )
    if include_property_list:
        add_http_sampler(
            tree,
            zf,
            100,
            "GET /RMS/Aspsoft/Dispatcher.aspx - Property List",
            "GET",
            "/RMS/Aspsoft/Dispatcher.aspx?nextPID=listCaseProperty&case_id=${case_id}&division_id=3",
            processors=form_extractors(
                "property_list", eventvalidation=False, scope="all"
            ),
        )


def add_person_business_loop(parent: ET.Element, zf: zipfile.ZipFile) -> None:
    person_loop = loop(parent, "Add Person Loop", "${__P(person_loops,10)}")
    pair(
        person_loop,
        user_parameters(
            "Generate Dynamic Person Name",
            [
                (
                    "lastName",
                    "TESTL${__time(yyyyMMddHHmmssSSS,)}${__threadNum}${__Random(1000,9999,)}",
                ),
                (
                    "firstName",
                    "TESTF${__time(yyyyMMddHHmmssSSS,)}${__threadNum}${__Random(1000,9999,)}",
                ),
                ("person_request_rnd", "${__Random(100000000,999999999,)}"),
                ("mn_rnd", "${__Random(100000000,999999999,)}"),
            ],
        ),
    )

    add_tree = transaction(person_loop, "Add Person")
    person_processors = form_extractors(
        "person_form", eventvalidation=True, scope="all"
    ) + [
        css_extractor(
            "driver_license_state_row_id",
            'select[ObjectName="driver_license_state"]',
            attribute="row_id",
            default="ROW_ID_NOT_FOUND",
            scope="all",
        ),
        css_extractor(
            "pob_state_row_id",
            'select[ObjectName="pob_state"]',
            attribute="row_id",
            default="ROW_ID_NOT_FOUND",
            scope="all",
        ),
    ]
    add_http_sampler(
        add_tree,
        zf,
        49,
        "GET /RMS/Aspsoft/PopUpDispatcher.aspx - Add Person Form",
        "GET",
        "/RMS/Aspsoft/PopUpDispatcher.aspx?nextPID=addCaseVW&case_id=${case_id}&rnd=${person_request_rnd}",
        processors=person_processors,
        timer=CB.build_constant_timer("${__P(iteration_delay_ms,0)}"),
        rnd_variable="person_request_rnd",
    )
    add_http_sampler(
        add_tree,
        zf,
        68,
        "POST /RMS/Aspsoft/engineservice.ashx - Driver License State Dropdown",
        "POST",
        "/RMS/Aspsoft/engineservice.ashx?action=dropdown&row_id=${driver_license_state_row_id}",
        params=params_for(zf, 68),
        rnd_variable="person_request_rnd",
    )
    add_http_sampler(
        add_tree,
        zf,
        69,
        "POST /RMS/Aspsoft/engineservice.ashx - Place of Birth State Dropdown",
        "POST",
        "/RMS/Aspsoft/engineservice.ashx?action=dropdown&row_id=${pob_state_row_id}",
        params=params_for(zf, 69),
        rnd_variable="person_request_rnd",
    )
    add_http_sampler(
        add_tree,
        zf,
        75,
        "POST /RMS/Include/CommonModule/Remote.ashx - City List",
        "POST",
        "/RMS/Include/CommonModule/Remote.ashx?action=GET_CITY_LIST",
        params=params_for(zf, 75),
        rnd_variable="person_request_rnd",
    )
    add_http_sampler(
        add_tree,
        zf,
        77,
        "GET /RMS/Include/RMS/IDReaderHandler.ashx",
        "GET",
        "/RMS/Include/RMS/IDReaderHandler.ashx?action=IDREADEREABLE",
        rnd_variable="person_request_rnd",
    )
    add_http_sampler(
        add_tree,
        zf,
        78,
        "POST /RMS/AspSoft/MasterName.aspx - Set Session",
        "POST",
        "/RMS/AspSoft/MasterName.aspx?PageID=SearchMasterNameSys_MasterPerson&action=setsession&rnd=${mn_rnd}",
        params=params_for(zf, 78, {"MN_rnd": "${mn_rnd}"}),
        rnd_variable="person_request_rnd",
    )
    add_http_sampler(
        add_tree,
        zf,
        79,
        "GET /RMS/AspSoft/MasterName.aspx - Search Dynamic Person",
        "GET",
        "/RMS/AspSoft/MasterName.aspx?PageID=SearchMasterNameSys_MasterPerson"
        "&FromObjects=last_name,first_name,middle_name,suffix_name,dob"
        "&last_name=${lastName}&first_name=${firstName}&middle_name=&suffix_name=&dob="
        "&paramsSource=session&MN_rnd=${mn_rnd}&rnd=${person_request_rnd}",
        rnd_variable="person_request_rnd",
    )
    add_http_sampler(
        add_tree,
        zf,
        86,
        "POST /RMS/AspSoft/MasterName.aspx - Remove Session",
        "POST",
        "/RMS/AspSoft/MasterName.aspx?PageID=SearchMasterNameSys_MasterPerson&action=removesession&MN_rnd=${mn_rnd}",
        params=params_for(zf, 86),
        rnd_variable="person_request_rnd",
    )
    add_http_sampler(
        add_tree,
        zf,
        87,
        "GET /RMS/aspsoft/engineservice.ashx - Server Date Time",
        "GET",
        "/RMS/aspsoft/engineservice.ashx?action=getserverdatetime&rnd=${person_request_rnd}",
        rnd_variable="person_request_rnd",
    )
    person_replacements = {
        "__VIEWSTATE": "${person_form_viewstate}",
        "__VIEWSTATEGENERATOR": "${person_form_viewstategenerator}",
        "__EVENTVALIDATION": "${person_form_eventvalidation}",
        "ctl00$ContentPlaceHolder1$ctl00$last_name~|person_add~|A": "${lastName}",
        "ctl00$ContentPlaceHolder1$ctl00$first_name~|person_add~|A": "${firstName}",
        "ctl00$ContentPlaceHolder1$ctl00$doubleEntryTimeStamp": "${person_form_double_entry_timestamp}",
    }
    add_http_sampler(
        add_tree,
        zf,
        89,
        "POST /RMS/Aspsoft/PopUpDispatcher.aspx - Save Person",
        "POST",
        "/RMS/Aspsoft/PopUpDispatcher.aspx?nextPID=addCaseVW&case_id=${case_id}&rnd=${person_request_rnd}",
        params=params_for(zf, 89, person_replacements),
        rnd_variable="person_request_rnd",
    )

    refresh = transaction(person_loop, "Refresh Person List")
    add_http_sampler(
        refresh,
        zf,
        94,
        "GET /RMS/Aspsoft/Dispatcher.aspx - Refresh Case Contacts",
        "GET",
        "/RMS/Aspsoft/Dispatcher.aspx?nextPID=showCaseContact&case_id=${case_id}&division_id=3",
    )
    add_http_sampler(
        refresh,
        zf,
        99,
        "POST /RMS/AspSoft/EngineService.ashx - Refresh Person Tab Count",
        "POST",
        "/RMS/AspSoft/EngineService.ashx?menu_id=1&action=ShowCountInTab"
        "&nextPID=showCaseContact&case_id=${case_id}&division_id=3&check_menu=1"
        "&rnd=${person_request_rnd}",
        params=params_for(zf, 99),
        rnd_variable="person_request_rnd",
    )


def add_property_business_loop(parent: ET.Element, zf: zipfile.ZipFile) -> None:
    property_loop = loop(parent, "Add Property Loop", "${__P(property_loops,10)}")
    pair(
        property_loop,
        user_parameters(
            "Generate Property Request Cachebuster",
            [("property_request_rnd", "${__Random(100000000,999999999,)}")],
        ),
    )
    load_tree = transaction(property_loop, "Load Property Form and Select Existing Person")
    property_processors = form_extractors(
        "property_form", eventvalidation=True, scope="all"
    ) + [
        css_extractor(
            "property_person_id",
            'input[ObjectName="c_person_id"]',
            attribute="value",
            match_number="0",
            default="PERSON_NOT_FOUND",
            scope="all",
        ),
        css_extractor(
            "property_sub_type_row_id",
            'select[ObjectName="property_sub_type"]',
            attribute="row_id",
            default="ROW_ID_NOT_FOUND",
            scope="all",
        ),
    ]
    add_http_sampler(
        load_tree,
        zf,
        106,
        "GET /RMS/Aspsoft/PopUpDispatcher.aspx - Add Property Form",
        "GET",
        "/RMS/Aspsoft/PopUpDispatcher.aspx?nextPID=addCaseProperty&case_id=${case_id}"
        "&rnd=${property_request_rnd}",
        processors=property_processors,
        timer=CB.build_constant_timer("${__P(iteration_delay_ms,0)}"),
        rnd_variable="property_request_rnd",
    )
    add_http_sampler(
        load_tree,
        zf,
        125,
        "POST /RMS/Aspsoft/engineservice.ashx - Property Subtype Dropdown",
        "POST",
        "/RMS/Aspsoft/engineservice.ashx?action=dropdown&row_id=${property_sub_type_row_id}",
        params=params_for(zf, 125),
        rnd_variable="property_request_rnd",
    )

    save_condition = (
        '${__jexl3("${property_person_id}" != "PERSON_NOT_FOUND" && '
        '"${property_person_id}" != "",)}'
    )
    save_branch = if_controller(
        property_loop, "Existing Person Candidate", save_condition
    )
    save_tree = transaction(save_branch, "Add Property")
    property_replacements = {
        "__VIEWSTATE": "${property_form_viewstate}",
        "__VIEWSTATEGENERATOR": "${property_form_viewstategenerator}",
        "__EVENTVALIDATION": "${property_form_eventvalidation}",
        "c_person_id": "${property_person_id}",
        "ctl00$ContentPlaceHolder1$ctl00$doubleEntryTimeStamp": "${property_form_double_entry_timestamp}",
    }
    add_http_sampler(
        save_tree,
        zf,
        128,
        "POST /RMS/Aspsoft/PopUpDispatcher.aspx - Save Property",
        "POST",
        "/RMS/Aspsoft/PopUpDispatcher.aspx?nextPID=addCaseProperty&case_id=${case_id}"
        "&rnd=${property_request_rnd}",
        params=params_for(zf, 128, property_replacements),
        rnd_variable="property_request_rnd",
    )

    missing_condition = (
        '${__jexl3("${property_person_id}" == "PERSON_NOT_FOUND" || '
        '"${property_person_id}" == "",)}'
    )
    missing_branch = if_controller(
        property_loop, "No Person Candidate", missing_condition
    )
    debug = CB.build_debug_sampler(
        display_jmeter_vars=False,
        display_jmeter_props=False,
        display_system_props=False,
    )
    debug.set("testname", "No Existing Person - Property Save Skipped")
    pair(missing_branch, debug)

    refresh = transaction(property_loop, "Refresh Property List")
    list_replacements = {
        "__VIEWSTATE": "${property_list_viewstate}",
        "__VIEWSTATEGENERATOR": "${property_list_viewstategenerator}",
        "ctl00$ContentPlaceHolder1$ctl00$doubleEntryTimeStamp": "${property_list_double_entry_timestamp}",
    }
    add_http_sampler(
        refresh,
        zf,
        131,
        "POST /RMS/Aspsoft/Dispatcher.aspx - Refresh Property List",
        "POST",
        "/RMS/Aspsoft/Dispatcher.aspx?nextPID=listCaseProperty&case_id=${case_id}&division_id=3",
        params=params_for(zf, 131, list_replacements),
        processors=form_extractors(
            "property_list", eventvalidation=False, scope="all"
        ),
    )
    count_tree = transaction(property_loop, "Refresh Property Tab Count")
    add_http_sampler(
        count_tree,
        zf,
        136,
        "POST /RMS/AspSoft/EngineService.ashx - Refresh Property Tab Count",
        "POST",
        "/RMS/AspSoft/EngineService.ashx?menu_id=1&action=ShowCountInTab"
        "&nextPID=listCaseProperty&case_id=${case_id}&division_id=3&check_menu=1"
        "&rnd=${property_request_rnd}",
        params=params_for(zf, 136),
        rnd_variable="property_request_rnd",
    )


def add_result_collector(parent: ET.Element) -> None:
    collector = CB.build_result_collector(
        filename="${__P(result_file,RI_Add_Person_Property_Deadlock_${__time(yyyyMMdd_HHmmss,)}.jtl)}",
        error_logging=False,
    )
    collector.set("guiclass", "SimpleDataWriter")
    collector.set("testname", "Simple Data Writer - RI Person Property JTL")
    pair(parent, collector)


def validate_generated(root: ET.Element) -> None:
    groups = root.findall(".//ThreadGroup")
    if len(groups) != 2:
        raise RuntimeError(f"Expected two Thread Groups, found {len(groups)}")
    present = {
        element.tag
        for element in root.iter()
        if element.tag.endswith("Assertion")
        or element.tag.startswith("JSR223")
        or (element.get("testclass") or "").startswith("JSR223")
        or element.tag in FORBIDDEN_NON_ASSERTION_TAGS
    }
    if present:
        raise RuntimeError(f"Forbidden JMX elements: {sorted(present)}")
    for sampler in root.findall(".//HTTPSamplerProxy"):
        follow = sampler.find("./boolProp[@name='HTTPSampler.follow_redirects']")
        if follow is None or follow.text != "true":
            raise RuntimeError(f"Follow Redirects disabled: {sampler.get('testname')}")
        for argument in sampler.findall(
            "./elementProp[@name='HTTPsampler.Arguments']/collectionProp/elementProp"
        ):
            encoded = argument.find("./boolProp[@name='HTTPArgument.always_encode']")
            if encoded is None or encoded.text != "true":
                raise RuntimeError(
                    f"always_encode disabled: {sampler.get('testname')}"
                )
    content = ET.tostring(root, encoding="unicode")
    for captured in (CAPTURED_CASE_ID, CAPTURED_PERSON_ID):
        if captured in content:
            raise RuntimeError(f"Captured dynamic ID remains: {captured}")


def build(output_path: Path) -> None:
    if not SAZ.is_file():
        raise FileNotFoundError(SAZ)
    if not REPOSITORY_GENERATOR.is_file():
        raise FileNotFoundError(REPOSITORY_GENERATOR)

    with tempfile.TemporaryDirectory(prefix="ri_person_property_jmx_") as temp_dir:
        base = Path(temp_dir) / "repository_base.jmx"
        invoke_repository_generator(base)
        tree = ET.parse(base)

    root = tree.getroot()
    test_plan = root.find("./hashTree/TestPlan")
    test_plan_tree = root.find("./hashTree/hashTree")
    if test_plan is None or test_plan_tree is None:
        raise RuntimeError("Repository generator produced an incomplete JMeter tree")
    test_plan.set("testname", "RI Same Case Person-Property Lock Contention")
    test_plan.find("./boolProp[@name='TestPlan.serialize_threadgroups']").text = "false"
    set_test_plan_variables(test_plan)
    test_plan_tree.clear()

    with zipfile.ZipFile(SAZ) as zf:
        person_group, person_tree = configure_thread_group(
            "Add Person Process", "${__P(person_threads,1)}"
        )
        pair(test_plan_tree, person_group, person_tree)
        add_thread_configs(person_tree, "Person Session")
        person_once = once_only(person_tree, "Person Login and Open Case Once")
        add_login_flow(
            person_once,
            zf,
            account_prefix="person",
            username_variable="person_username",
            password_variable="person_password",
        )
        add_open_case_flow(person_once, zf, "Person", include_property_list=False)
        add_person_business_loop(person_tree, zf)

        property_group, property_tree = configure_thread_group(
            "Add Property Process", "${__P(property_threads,1)}"
        )
        pair(test_plan_tree, property_group, property_tree)
        add_thread_configs(property_tree, "Property Session")
        property_once = once_only(property_tree, "Property Login and Open Case Once")
        add_login_flow(
            property_once,
            zf,
            account_prefix="property",
            username_variable="property_username",
            password_variable="property_password",
        )
        add_open_case_flow(property_once, zf, "Property", include_property_list=True)
        add_property_business_loop(property_tree, zf)

    add_result_collector(test_plan_tree)
    validate_generated(root)
    ET.indent(tree, space="  ")
    content = ET.tostring(root, encoding="unicode", xml_declaration=False)
    document = '<?xml version="1.0" encoding="UTF-8"?>\n' + content + "\n"
    if not JG.validate_jmx(document):
        raise RuntimeError("Repository JMX validator rejected generated document")
    JG.save_to_file(document, str(output_path))
    print(f"Generated {output_path}")


def main() -> int:
    build(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
