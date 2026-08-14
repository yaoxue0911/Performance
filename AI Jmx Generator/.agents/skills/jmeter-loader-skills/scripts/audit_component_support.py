#!/usr/bin/env python3
"""Audit tree-generator support against its contract and JMeter references."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from generate_jmx_tree import COMPONENT_FACTORIES


DISPLAY_TO_NODE = {
    "http request defaults": "http_defaults",
    "http header manager": "header_manager",
    "http cookie manager": "cookie_manager",
    "http cache manager": "cache_manager",
    "csv data set config": "csv_data_set",
    "jdbc connection configuration": "jdbc_connection_config",
    "http request": "http_sampler",
    "debug sampler": "debug_sampler",
    "jdbc request": "jdbc_sampler",
    "if controller": "if_controller",
    "transaction controller": "transaction_controller",
    "once only controller": "once_only_controller",
    "loop controller": "loop_controller",
    "foreach controller": "foreach_controller",
    "constant timer": "constant_timer",
    "gaussian random timer": "gaussian_timer",
    "uniform random timer": "uniform_timer",
    "synchronizing timer": "synchronizing_timer",
    "json extractor": "json_extractor",
    "boundary extractor": "boundary_extractor",
    "regular expression extractor": "regex_extractor",
    "css selector extractor": "css_extractor",
    "xpath extractor": "xpath_extractor",
    "response assertion": "response_assertion",
    "duration assertion": "duration_assertion",
    "json assertion": "json_assertion",
    "jsr223 postprocessor": "jsr223_postprocessor",
    "jsr223 preprocessor": "jsr223_preprocessor",
    "user parameters": "user_parameters",
    "user defined variables": "user_defined_variables",
    "view results tree": "view_results_tree",
    "simple data writer": "simple_data_writer",
    "influxdb backend listener": "backend_listener_influxdb",
}


class ContractResult(NamedTuple):
    contract_gaps: set[str]
    undocumented_registrations: set[str]


class ReferenceComponent(NamedTuple):
    display_name: str
    category: str
    node_type: str | None
    status: str
    sources: tuple[str, ...]


def load_registered_types() -> set[str]:
    return set(COMPONENT_FACTORIES)


def load_contract_types(schema_path: Path) -> set[str]:
    text = schema_path.read_text(encoding="utf-8")
    match = re.search(r"^## 支持的节点\s*$([\s\S]*?)(?=^##\s)", text, re.MULTILINE)
    if not match:
        raise ValueError(f"support contract section not found in {schema_path}")
    node_types: set[str] = set()
    for line in match.group(1).splitlines():
        if line.lstrip().startswith("|"):
            node_types.update(re.findall(r"`([a-z][a-z0-9_]+)`", line))
    if not node_types:
        raise ValueError(f"support contract table is empty in {schema_path}")
    return node_types


def compare_contract(
    declared_types: set[str], registered_types: set[str]
) -> ContractResult:
    return ContractResult(
        contract_gaps=declared_types - registered_types,
        undocumented_registrations=registered_types - declared_types,
    )


def _normalize_display_name(name: str) -> str:
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name)
    name = name.replace("（", "(").split("(", 1)[0]
    return re.sub(r"\s+", " ", name).strip().casefold()


def _component_catalog(reference_path: Path) -> list[tuple[str, str]]:
    current_category = "Uncategorized"
    components: list[tuple[str, str]] = []
    for line in reference_path.read_text(encoding="utf-8").splitlines():
        category = re.match(r"^##\s+(.+?)\s*$", line)
        if category:
            current_category = re.sub(r"^[^、]+、", "", category.group(1)).strip()
            continue
        component = re.match(r"^###\s+\d+\.\s+(.+?)\s*$", line)
        if component:
            display_name = re.sub(r"\s*\([^)]*\)\s*$", "", component.group(1)).strip()
            components.append((display_name, current_category))
    return components


def catalog_reference_components(
    references_dir: Path, registered_types: set[str]
) -> list[ReferenceComponent]:
    catalog_path = references_dir / "component_reference.md"
    if not catalog_path.exists():
        raise ValueError(f"component catalog not found: {catalog_path}")
    reference_texts = {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(references_dir.glob("*.md"))
    }
    entries: list[ReferenceComponent] = []
    seen: set[str] = set()
    for display_name, category in _component_catalog(catalog_path):
        normalized = _normalize_display_name(display_name)
        if normalized in seen:
            continue
        seen.add(normalized)
        node_type = DISPLAY_TO_NODE.get(normalized)
        status = (
            "REGISTERED"
            if node_type is not None and node_type in registered_types
            else "REFERENCE_ONLY"
        )
        sources = tuple(
            filename
            for filename, text in reference_texts.items()
            if display_name.casefold() in text.casefold()
        )
        entries.append(
            ReferenceComponent(
                display_name=display_name,
                category=category,
                node_type=node_type,
                status=status,
                sources=sources,
            )
        )
    return sorted(entries, key=lambda item: (item.category, item.display_name))


def render_report(
    contract: ContractResult,
    declared: set[str],
    registered: set[str],
    references: list[ReferenceComponent],
) -> str:
    registered_refs = [item for item in references if item.status == "REGISTERED"]
    reference_only = [item for item in references if item.status == "REFERENCE_ONLY"]
    lines = [
        "# JMeter Tree Generator Component Audit",
        "",
        "## Explicit support contract",
        "",
        f"- Declared node types: {len(declared)}",
        f"- Registered node types: {len(registered)}",
        f"- Contract gaps: {len(contract.contract_gaps)}",
        f"- Registered but undocumented: {len(contract.undocumented_registrations)}",
        "",
        "### Contract gaps",
        "",
    ]
    lines.extend(
        [f"- `{item}`" for item in sorted(contract.contract_gaps)] or ["- None"]
    )
    lines.extend(["", "### Registered but undocumented", ""])
    lines.extend(
        [f"- `{item}`" for item in sorted(contract.undocumented_registrations)]
        or ["- None"]
    )
    lines.extend(["", "## Registered components mentioned in references", ""])
    for item in registered_refs:
        lines.append(
            f"- **{item.display_name}** → `{item.node_type}`; sources: "
            + ", ".join(f"`{source}`" for source in item.sources)
        )
    lines.extend(["", "## Reference-only components", ""])
    current_category = None
    for item in reference_only:
        if item.category != current_category:
            current_category = item.category
            lines.extend([f"### {current_category}", ""])
        lines.append(
            f"- **{item.display_name}**; sources: "
            + ", ".join(f"`{source}`" for source in item.sources)
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "Contract gaps are generator defects. Reference-only entries are JMeter knowledge coverage and are not support commitments.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-root", type=Path, default=SCRIPT_DIR.parent)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    skill_root = args.skill_root.resolve()
    registered = load_registered_types()
    declared = load_contract_types(skill_root / "references" / "scenario-schema.md")
    contract = compare_contract(declared, registered)
    references = catalog_reference_components(skill_root / "references", registered)
    report = render_report(contract, declared, registered, references)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report)
    if contract.contract_gaps or contract.undocumented_registrations:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
