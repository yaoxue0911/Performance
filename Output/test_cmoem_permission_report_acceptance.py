#!/usr/bin/env python3
import csv
import json
import pathlib
import xml.etree.ElementTree as ET


OUTPUT = pathlib.Path(__file__).resolve().parent
JMX = OUTPUT / "CMOEM_permission_report.jmx"
SCENARIO = OUTPUT / "CMOEM_permission_report.scenario.json"
PLAN = OUTPUT / "CMOEM_permission_report_stage1_plan.md"
CSV = OUTPUT / "CMOEM case id.csv"


def prop(element, name):
    node = element.find(f".//stringProp[@name='{name}']")
    assert node is not None, f"missing property {name}"
    return node.text or ""


def paired_hash(parent, element):
    children = list(parent)
    index = children.index(element)
    assert index + 1 < len(children) and children[index + 1].tag == "hashTree"
    return children[index + 1]


def main():
    for path in (JMX, SCENARIO, PLAN, CSV):
        assert path.exists(), f"missing artifact: {path.name}"

    with CSV.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows and rows[0] == ["case_id"]
    assert len(rows) > 1
    assert all(len(row) == 1 and row[0].isdigit() for row in rows[1:])

    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
    assert "$include" not in json.dumps(scenario)

    root = ET.parse(JMX).getroot()
    group = root.find(".//ThreadGroup")
    assert group is not None
    assert prop(group, "ThreadGroup.num_threads") == "${__P(concurrency,1)}"
    assert prop(group, "ThreadGroup.ramp_time") == "${__P(rampup,1)}"

    defaults = root.find(".//ConfigTestElement[@testname='HTTP Request Defaults']")
    assert defaults is not None
    assert prop(defaults, "HTTPSampler.domain") == "${__P(target_host,10.1.3.248)}"
    assert prop(defaults, "HTTPSampler.port") == "${__P(target_port,80)}"
    assert prop(defaults, "HTTPSampler.protocol") == "${__P(protocol,http)}"

    once = root.find(".//OnceOnlyController")
    loop = root.find(".//LoopController")
    assert once is not None and loop is not None
    thread_tree = paired_hash(root.find(".//TestPlan/../hashTree"), group)
    assert len(paired_hash(thread_tree, once).findall(".//HTTPSamplerProxy")) == 4
    loop_tree = paired_hash(thread_tree, loop)
    transactions = loop_tree.findall("./TransactionController")
    assert [item.get("testname") for item in transactions] == [
        "Modify case permission",
        "Add investigation report",
    ]
    open_case = loop_tree.findall("./HTTPSamplerProxy")
    assert len(open_case) == 1
    assert prop(open_case[0], "HTTPSampler.path") == (
        "/InfoRMS30/AspSoft/Dispatcher.aspx?nextPID=inquireIncidentSummary"
        "&case_id=${case_id}"
    )
    csv_config = root.find(".//CSVDataSet")
    assert csv_config is not None
    assert prop(csv_config, "filename") == "CMOEM case id.csv"

    samplers = root.findall(".//HTTPSamplerProxy")
    assert len(samplers) == 20
    xml = JMX.read_text(encoding="utf-8")
    assert "/InfoRMS30/" in xml
    assert "/RMS/" not in xml
    assert "hcrms.csitech.com" not in xml
    assert "1100260052" not in xml and "3466" not in xml
    assert "case_id=${case_id}" in xml
    assert "POSS MARIHUAN &gt;25G" in xml
    assert "24:21-20A(4)" in xml
    assert "SHOPLIFTING 4TH DEGREE" not in xml
    assert "listPopupChargeSub" not in xml
    assert "WUFPWFVFHzUwOUE0QzAwM0UyMkZQWDJYSjI" in xml
    assert "INVESTIGATION_NO" in xml and "2026000001" in xml
    assert "region_id=100000" in xml
    assert "ctl00$ContentPlaceHolder1$btnSave" in xml
    assert not root.findall(".//ResponseAssertion")
    assert len(root.findall(".//ResultCollector")) == 2

    print("CMOEM permission/report acceptance checks passed")


if __name__ == "__main__":
    main()
