import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
ASSEMBLER_PATH = SCRIPTS_DIR / "assemble_scenario.py"
GENERATOR_PATH = SCRIPTS_DIR / "generate_jmx_tree.py"


def load_assembler():
    if not ASSEMBLER_PATH.exists():
        raise AssertionError("assemble_scenario.py has not been implemented")
    spec = importlib.util.spec_from_file_location("assemble_scenario", ASSEMBLER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def valid_manifest(children):
    return {
        "test_plan": {"name": "Fragmented Plan"},
        "thread_groups": [
            {
                "name": "Users",
                "threads": "${__P(concurrency,1)}",
                "rampup": "${__P(rampup,1)}",
                "duration": "${__P(duration,60)}",
                "children": children,
            }
        ],
    }


class AssembleScenarioTests(unittest.TestCase):
    def test_object_include_replaces_include_node(self):
        assembler = load_assembler()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_json(root / "manifest.json", valid_manifest([
                {"$include": "fragments/request.json"}
            ]))
            write_json(root / "fragments/request.json", {
                "type": "http_sampler",
                "name": "GET Home",
                "method": "GET",
                "path": "/home",
            })

            result = assembler.assemble(root / "manifest.json")

            self.assertEqual(result["thread_groups"][0]["children"][0]["name"], "GET Home")

    def test_array_include_splices_elements_in_order(self):
        assembler = load_assembler()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_json(root / "manifest.json", valid_manifest([
                {"type": "debug_sampler", "name": "Before"},
                {"$include": "fragments/requests.json"},
                {"type": "debug_sampler", "name": "After"},
            ]))
            write_json(root / "fragments/requests.json", [
                {"type": "debug_sampler", "name": "First"},
                {"type": "debug_sampler", "name": "Second"},
            ])

            result = assembler.assemble(root / "manifest.json")

            names = [node["name"] for node in result["thread_groups"][0]["children"]]
            self.assertEqual(names, ["Before", "First", "Second", "After"])

    def test_nested_include_is_resolved_relative_to_including_fragment(self):
        assembler = load_assembler()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_json(root / "manifest.json", valid_manifest([
                {"$include": "fragments/transaction.json"}
            ]))
            write_json(root / "fragments/transaction.json", {
                "type": "transaction_controller",
                "name": "Business",
                "children": [{"$include": "steps/request.json"}],
            })
            write_json(root / "fragments/steps/request.json", {
                "type": "http_sampler",
                "name": "Nested GET",
                "method": "GET",
                "path": "/nested",
            })

            result = assembler.assemble(root / "manifest.json")

            nested = result["thread_groups"][0]["children"][0]["children"][0]
            self.assertEqual(nested["name"], "Nested GET")

    def test_missing_include_reports_including_file(self):
        assembler = load_assembler()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_json(root / "manifest.json", valid_manifest([
                {"$include": "fragments/missing.json"}
            ]))

            with self.assertRaisesRegex(ValueError, r"missing\.json.*manifest\.json"):
                assembler.assemble(root / "manifest.json")

    def test_include_cycle_reports_complete_chain(self):
        assembler = load_assembler()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_json(root / "manifest.json", {"$include": "a.json"})
            write_json(root / "a.json", {"$include": "b.json"})
            write_json(root / "b.json", {"$include": "a.json"})

            with self.assertRaisesRegex(ValueError, r"a\.json.*b\.json.*a\.json"):
                assembler.assemble(root / "manifest.json")

    def test_include_cannot_escape_manifest_root(self):
        assembler = load_assembler()
        with tempfile.TemporaryDirectory() as temp_dir:
            parent = Path(temp_dir)
            root = parent / "scenario"
            write_json(root / "manifest.json", {"$include": "../outside.json"})
            write_json(parent / "outside.json", valid_manifest([
                {"type": "debug_sampler", "name": "Outside"}
            ]))

            with self.assertRaisesRegex(ValueError, r"outside manifest root"):
                assembler.assemble(root / "manifest.json")

    def test_absolute_include_path_is_rejected(self):
        assembler = load_assembler()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            included = root / "request.json"
            write_json(included, {"type": "debug_sampler", "name": "Request"})
            write_json(root / "manifest.json", {"$include": str(included.resolve())})

            with self.assertRaisesRegex(ValueError, r"outside manifest root"):
                assembler.assemble(root / "manifest.json")

    def test_include_object_cannot_mix_other_fields(self):
        assembler = load_assembler()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_json(root / "manifest.json", valid_manifest([
                {"$include": "request.json", "enabled": True}
            ]))
            write_json(root / "request.json", {
                "type": "debug_sampler",
                "name": "Request",
            })

            with self.assertRaisesRegex(ValueError, r"\$include.*only field"):
                assembler.assemble(root / "manifest.json")

    def test_validate_rejects_invalid_final_thread_group_structure(self):
        assembler = load_assembler()
        invalid_scenarios = [
            {"test_plan": {}, "thread_groups": []},
            {"test_plan": {}, "thread_groups": [{"name": "Users", "children": []}]},
        ]
        for scenario in invalid_scenarios:
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                write_json(root / "manifest.json", scenario)
                with self.assertRaisesRegex(ValueError, r"thread_groups.*must not be empty|children.*must not be empty"):
                    assembler.validate_scenario(assembler.assemble(root / "manifest.json"))

    def test_cli_validation_failure_preserves_existing_output(self):
        load_assembler()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = root / "manifest.json"
            output_path = root / "assembled.json"
            write_json(manifest_path, {"test_plan": {}, "thread_groups": []})
            output_path.write_text("existing output\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ASSEMBLER_PATH),
                    "--manifest",
                    str(manifest_path),
                    "--output",
                    str(output_path),
                    "--validate",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output_path.read_text(encoding="utf-8"), "existing output\n")

    def test_cli_assembly_generates_valid_jmx_with_existing_generator(self):
        load_assembler()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = root / "scenario/manifest.json"
            scenario_path = root / "assembled.json"
            jmx_path = root / "plan.jmx"
            write_json(manifest_path, valid_manifest([
                {"$include": "fragments/requests.json"}
            ]))
            write_json(manifest_path.parent / "fragments/requests.json", [
                {
                    "type": "http_sampler",
                    "name": "GET Home",
                    "method": "GET",
                    "path": "/home",
                }
            ])

            assemble_result = subprocess.run(
                [
                    sys.executable,
                    str(ASSEMBLER_PATH),
                    "--manifest",
                    str(manifest_path),
                    "--output",
                    str(scenario_path),
                    "--validate",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(assemble_result.returncode, 0, assemble_result.stderr)
            self.assertIn("Scenario assembly validation passed", assemble_result.stdout)

            generate_result = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR_PATH),
                    "--scenario",
                    str(scenario_path),
                    "--output",
                    str(jmx_path),
                    "--validate",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(generate_result.returncode, 0, generate_result.stderr)
            ET.parse(jmx_path)


if __name__ == "__main__":
    unittest.main()
