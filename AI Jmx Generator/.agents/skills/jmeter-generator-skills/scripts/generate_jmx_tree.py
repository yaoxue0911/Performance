#!/usr/bin/env python3
"""Generate a JMeter JMX plan from an explicitly nested JSON scenario."""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from jmx_tree_components import JMXComponentBuilder


COMPONENT_FACTORIES: dict[str, Callable[..., ET.Element]] = {
    "http_defaults": JMXComponentBuilder.build_http_defaults,
    "header_manager": JMXComponentBuilder.build_header_manager,
    "cookie_manager": JMXComponentBuilder.build_cookie_manager,
    "cache_manager": JMXComponentBuilder.build_cache_manager,
    "csv_data_set": JMXComponentBuilder.build_csv_data_set,
    "jdbc_connection_config": JMXComponentBuilder.build_jdbc_connection_config,
    "http_sampler": JMXComponentBuilder.build_http_sampler,
    "debug_sampler": JMXComponentBuilder.build_debug_sampler,
    "jdbc_sampler": JMXComponentBuilder.build_jdbc_sampler,
    "if_controller": JMXComponentBuilder.build_if_controller,
    "transaction_controller": JMXComponentBuilder.build_transaction_controller,
    "once_only_controller": JMXComponentBuilder.build_once_only_controller,
    "loop_controller": JMXComponentBuilder.build_loop_controller,
    "foreach_controller": JMXComponentBuilder.build_foreach_controller,
    "constant_timer": JMXComponentBuilder.build_constant_timer,
    "gaussian_timer": JMXComponentBuilder.build_gaussian_timer,
    "uniform_timer": JMXComponentBuilder.build_uniform_timer,
    "synchronizing_timer": JMXComponentBuilder.build_synchronizing_timer,
    "json_extractor": JMXComponentBuilder.build_json_extractor,
    "boundary_extractor": JMXComponentBuilder.build_boundary_extractor,
    "regex_extractor": JMXComponentBuilder.build_regex_extractor,
    "css_extractor": JMXComponentBuilder.build_css_extractor,
    "xpath_extractor": JMXComponentBuilder.build_xpath_extractor,
    "response_assertion": JMXComponentBuilder.build_response_assertion,
    "duration_assertion": JMXComponentBuilder.build_duration_assertion,
    "json_assertion": JMXComponentBuilder.build_json_assertion,
    "jsr223_postprocessor": JMXComponentBuilder.build_jsr223_postprocessor,
    "jsr223_preprocessor": JMXComponentBuilder.build_jsr223_preprocessor,
    "user_parameters": JMXComponentBuilder.build_user_parameters,
    "user_defined_variables": JMXComponentBuilder.build_user_defined_variables,
    "result_collector": JMXComponentBuilder.build_result_collector,
    "view_results_tree": JMXComponentBuilder.build_view_results_tree,
    "simple_data_writer": JMXComponentBuilder.build_simple_data_writer,
    "backend_listener_influxdb": JMXComponentBuilder.build_backend_listener_influxdb,
}

CONTROLLER_TYPES = {
    "if_controller",
    "transaction_controller",
    "once_only_controller",
    "loop_controller",
    "foreach_controller",
}


def _require_object(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{location} must be an object")
    return value


def _require_list(value: Any, location: str, *, nonempty: bool = False) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{location} must be an array")
    if nonempty and not value:
        raise ValueError(f"{location} must not be empty")
    return value


def _build_component(node: dict[str, Any], location: str) -> tuple[ET.Element, list[Any]]:
    node_type = node.get("type")
    if not isinstance(node_type, str) or not node_type:
        raise ValueError(f"{location}.type must be a non-empty string")
    if node_type not in COMPONENT_FACTORIES:
        raise ValueError(f"{location} has unsupported type '{node_type}'")

    raw_children = node.get("children", [])
    children = _require_list(raw_children, f"{location}.children")
    if node_type in CONTROLLER_TYPES and not children:
        raise ValueError(f"{location} {node_type} requires non-empty children")

    kwargs = {
        key: value
        for key, value in node.items()
        if key not in {"type", "children", "enabled"}
    }
    requested_name = kwargs.get("name")
    factory = COMPONENT_FACTORIES[node_type]

    # Some component factories do not expose a name argument. The tree schema
    # still allows every node to have a meaningful JMeter test name.
    if node_type not in {
        "http_sampler",
        "jdbc_sampler",
        "jdbc_connection_config",
        "transaction_controller",
        "response_assertion",
        "css_extractor",
        "xpath_extractor",
        "view_results_tree",
        "simple_data_writer",
    }:
        kwargs.pop("name", None)

    try:
        element = factory(**kwargs)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid configuration at {location}: {exc}") from exc

    if requested_name is not None:
        element.set("testname", str(requested_name))
    if "enabled" in node:
        element.set("enabled", "true" if node["enabled"] else "false")
    return element, children


def _render_children(parent_hash: ET.Element, children: list[Any], location: str) -> None:
    for index, raw_node in enumerate(children):
        node_location = f"{location}[{index}]"
        node = _require_object(raw_node, node_location)
        element, nested_children = _build_component(node, node_location)
        nested_hash = ET.Element("hashTree")
        parent_hash.append(element)
        parent_hash.append(nested_hash)
        _render_children(nested_hash, nested_children, f"{node_location}.children")


def _validate_hash_tree_pairs(tree: ET.Element, location: str) -> None:
    children = list(tree)
    if len(children) % 2 != 0:
        raise ValueError(f"{location} contains an unpaired JMeter element")
    for index in range(0, len(children), 2):
        paired_tree = children[index + 1]
        if paired_tree.tag != "hashTree":
            raise ValueError(f"{location}[{index}] is not followed by hashTree")
        _validate_hash_tree_pairs(paired_tree, f"{location}[{index + 1}]")


def validate_scenario(scenario: Any) -> dict[str, Any]:
    scenario_obj = _require_object(scenario, "scenario")
    _require_object(scenario_obj.get("test_plan", {}), "test_plan")
    thread_groups = _require_list(
        scenario_obj.get("thread_groups"), "thread_groups", nonempty=True
    )
    for index, raw_group in enumerate(thread_groups):
        group = _require_object(raw_group, f"thread_groups[{index}]")
        _require_list(
            group.get("children"),
            f"thread_groups[{index}].children",
            nonempty=True,
        )
    return scenario_obj


def build_jmx(scenario: dict[str, Any]) -> str:
    scenario = validate_scenario(scenario)
    test_plan_config = dict(scenario.get("test_plan", {}))

    root = ET.Element(
        "jmeterTestPlan",
        {"version": "1.2", "properties": "5.0", "jmeter": "5.6.3"},
    )
    root_hash = ET.SubElement(root, "hashTree")
    test_plan = JMXComponentBuilder.build_test_plan(**test_plan_config)
    test_plan_hash = ET.Element("hashTree")
    root_hash.append(test_plan)
    root_hash.append(test_plan_hash)

    for index, raw_group in enumerate(scenario["thread_groups"]):
        group = dict(raw_group)
        group_children = group.pop("children")
        try:
            thread_group = JMXComponentBuilder.build_thread_group(**group)
        except TypeError as exc:
            raise ValueError(
                f"Invalid configuration at thread_groups[{index}]: {exc}"
            ) from exc
        thread_group_hash = ET.Element("hashTree")
        test_plan_hash.append(thread_group)
        test_plan_hash.append(thread_group_hash)
        _render_children(
            thread_group_hash,
            group_children,
            f"thread_groups[{index}].children",
        )

    _validate_hash_tree_pairs(test_plan_hash, "test_plan.hashTree")
    ET.indent(root, space="  ")
    xml = ET.tostring(root, encoding="unicode", xml_declaration=False)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml + "\n"


def load_scenario(path: str | Path) -> dict[str, Any]:
    scenario_path = Path(path)
    try:
        with scenario_path.open("r", encoding="utf-8") as handle:
            return validate_scenario(json.load(handle))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {scenario_path} at line {exc.lineno}, column {exc.colno}"
        ) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a JMeter JMX file from a nested JSON scenario"
    )
    parser.add_argument("--scenario", required=True, help="Nested scenario JSON file")
    parser.add_argument("--output", "-o", required=True, help="Output JMX file")
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Print confirmation after structural validation",
    )
    args = parser.parse_args(argv)

    try:
        content = build_jmx(load_scenario(args.scenario))
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        if args.validate:
            print("JMX structure validation passed")
        print(f"Generated JMX: {output_path}")
        print(
            "监听器提示：调试时启用 View Results Tree 以保存完整响应数据；"
            "正式负载测试前禁用它，并启用 Simple Data Writer。"
        )
        return 0
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
