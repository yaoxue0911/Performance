#!/usr/bin/env python3
import pathlib
import csv
import xml.etree.ElementTree as ET


OUTPUT = pathlib.Path(__file__).resolve().parent
JMX = OUTPUT / "HC_permission_report.jmx"
SCENARIO = OUTPUT / "HC_permission_report.scenario.json"
PLAN = OUTPUT / "HC_permission_report_stage1_plan.md"
CSV = OUTPUT / "case id.csv"


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

    # Contract: JMeter receives a real UTF-8 CSV, not an Excel workbook that
    # merely has a .csv suffix. Every data row must be one numeric case ID.
    with CSV.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows and rows[0] == ["case_id"]
    assert len(rows) > 1, "case id.csv has no case ID rows"
    assert all(len(row) == 1 and row[0].isdigit() for row in rows[1:])
    root = ET.parse(JMX).getroot()

    groups = root.findall(".//ThreadGroup")
    assert len(groups) == 1
    group = groups[0]
    assert prop(group, "ThreadGroup.num_threads") == "${__P(concurrency,1)}"
    assert prop(group, "ThreadGroup.ramp_time") == "${__P(rampup,1)}"
    assert prop(group, "ThreadGroup.duration") == "${__P(duration,600)}"

    once = root.findall(".//OnceOnlyController")
    assert len(once) == 1
    group_hash = paired_hash(root.find(".//TestPlan/../hashTree"), group)
    once_hash = paired_hash(group_hash, once[0])
    assert len(once_hash.findall(".//HTTPSamplerProxy")) == 4

    loops = root.findall(".//LoopController")
    assert len(loops) == 1
    loop_hash = paired_hash(group_hash, loops[0])
    direct_loop_samplers = loop_hash.findall("./HTTPSamplerProxy")
    assert len(direct_loop_samplers) == 1
    open_case = direct_loop_samplers[0]
    assert open_case.get("testname") == "Open case incident summary"
    assert prop(open_case, "HTTPSampler.method") == "GET"
    assert prop(open_case, "HTTPSampler.path") == (
        "/RMS/AspSoft/Dispatcher.aspx?nextPID=inquireIncidentSummary"
        "&case_id=${case_id}"
    )

    loop_elements = list(loop_hash)
    open_case_index = loop_elements.index(open_case)
    transactions = loop_hash.findall("./TransactionController")
    assert [item.get("testname") for item in transactions] == [
        "Modify case permission",
        "Add investigation report",
    ]
    assert open_case_index < loop_elements.index(transactions[0])

    csv_config = root.find(".//CSVDataSet")
    assert csv_config is not None
    assert prop(csv_config, "filename") == "case id.csv"
    assert prop(csv_config, "variableNames") == "case_id"

    samplers = root.findall(".//HTTPSamplerProxy")
    assert len(samplers) == 20
    xml = JMX.read_text(encoding="utf-8")
    assert "2000009882" not in xml and "2000009883" not in xml
    assert "case_id=${case_id}" in xml
    assert "SHOPLIFTING 4TH DEGREE &gt;$200&lt; $75,000" in xml
    assert "2C:20-11C(3)" in xml
    assert "listPopupChargeSub" not in xml
    assert "sa01" in xml and "QyQhMTk5MCFuZjAkaGFyMzIwMjY=" in xml

    assert not root.findall(".//ResponseAssertion")
    assert not root.findall(".//DurationAssertion")
    assert not root.findall(".//JSONPathAssertion")
    assert len(root.findall(".//ResultCollector")) == 2

    print("HC permission/report acceptance checks passed")


if __name__ == "__main__":
    main()
