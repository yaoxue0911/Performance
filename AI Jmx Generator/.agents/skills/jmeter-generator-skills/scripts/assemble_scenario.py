#!/usr/bin/env python3
"""Assemble one JMeter Scenario JSON file from safe recursive fragments."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


class _Expansion:
    """Mark an include result so a containing array can splice list values."""

    def __init__(self, value: Any) -> None:
        self.value = value


def _load_json(path: Path, including_path: Path | None = None) -> Any:
    if not path.is_file():
        if including_path is None:
            raise ValueError(f"JSON file does not exist: {path}")
        raise ValueError(f"Included file does not exist: {path} (included from {including_path})")
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {path} at line {exc.lineno}, column {exc.colno}"
        ) from exc


def _inside_root(path: Path, root_dir: Path) -> bool:
    return path == root_dir or root_dir in path.parents


def resolve(
    value: Any,
    source_path: Path,
    root_dir: Path,
    stack: tuple[Path, ...],
) -> Any:
    """Resolve include nodes; return an expansion marker only for an include node."""
    if isinstance(value, dict):
        if "$include" in value:
            if set(value) != {"$include"}:
                raise ValueError(f"$include must be the only field in {source_path}")
            include_value = value["$include"]
            if not isinstance(include_value, str) or not include_value:
                raise ValueError(f"$include must be a non-empty relative path in {source_path}")
            include_path = Path(include_value)
            if include_path.is_absolute():
                raise ValueError(f"Included file is outside manifest root: {include_path}")
            target = (source_path.parent / include_path).resolve()
            if not _inside_root(target, root_dir):
                raise ValueError(f"Included file is outside manifest root: {target}")
            if target in stack:
                chain = " -> ".join(str(path) for path in (*stack, target))
                raise ValueError(f"Include cycle detected: {chain}")
            included = _load_json(target, source_path)
            resolved = resolve(included, target, root_dir, (*stack, target))
            if isinstance(resolved, _Expansion):
                resolved = resolved.value
            return _Expansion(resolved)

        result: dict[str, Any] = {}
        for key, item in value.items():
            resolved = resolve(item, source_path, root_dir, stack)
            result[key] = resolved.value if isinstance(resolved, _Expansion) else resolved
        return result

    if isinstance(value, list):
        result: list[Any] = []
        for item in value:
            resolved = resolve(item, source_path, root_dir, stack)
            if isinstance(resolved, _Expansion):
                if isinstance(resolved.value, list):
                    result.extend(resolved.value)
                else:
                    result.append(resolved.value)
            else:
                result.append(resolved)
        return result

    return value


def assemble(manifest_path: Path) -> dict[str, Any]:
    """Read and fully resolve a manifest without validating Scenario semantics."""
    manifest = manifest_path.resolve()
    root_dir = manifest.parent
    raw = _load_json(manifest)
    resolved = resolve(raw, manifest, root_dir, (manifest,))
    if isinstance(resolved, _Expansion):
        resolved = resolved.value
    return resolved


def validate_scenario(scenario: Any) -> dict[str, Any]:
    """Validate the minimum final structure required by the JMX generator."""
    if not isinstance(scenario, dict):
        raise ValueError("scenario must be an object")
    thread_groups = scenario.get("thread_groups")
    if not isinstance(thread_groups, list):
        raise ValueError("thread_groups must be an array")
    if not thread_groups:
        raise ValueError("thread_groups must not be empty")
    for index, group in enumerate(thread_groups):
        if not isinstance(group, dict):
            raise ValueError(f"thread_groups[{index}] must be an object")
        children = group.get("children")
        if not isinstance(children, list):
            raise ValueError(f"thread_groups[{index}].children must be an array")
        if not children:
            raise ValueError(f"thread_groups[{index}].children must not be empty")
    return scenario


def _write_json_atomically(value: Any, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(output_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Assemble a JMeter Scenario JSON file from recursive fragments"
    )
    parser.add_argument("--manifest", required=True, help="Root Scenario manifest JSON")
    parser.add_argument("--output", "-o", required=True, help="Assembled Scenario JSON")
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate final thread_groups and children before writing",
    )
    args = parser.parse_args(argv)

    try:
        scenario = assemble(Path(args.manifest))
        if args.validate:
            validate_scenario(scenario)
        output_path = Path(args.output)
        _write_json_atomically(scenario, output_path)
        if args.validate:
            print("Scenario assembly validation passed")
        print(f"Assembled Scenario: {output_path}")
        return 0
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
