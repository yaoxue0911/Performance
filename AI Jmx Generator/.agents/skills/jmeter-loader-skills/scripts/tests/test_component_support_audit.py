import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
AUDIT_PATH = SCRIPTS_DIR / "audit_component_support.py"


def load_audit_module():
    if not AUDIT_PATH.exists():
        raise AssertionError("audit_component_support.py has not been implemented")
    spec = importlib.util.spec_from_file_location("audit_component_support", AUDIT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ComponentSupportAuditTests(unittest.TestCase):
    def test_contract_comparison_reports_both_directions(self):
        audit = load_audit_module()

        result = audit.compare_contract(
            {"http_sampler", "missing_node"},
            {"http_sampler", "extra_node"},
        )

        self.assertEqual(result.contract_gaps, {"missing_node"})
        self.assertEqual(result.undocumented_registrations, {"extra_node"})

    def test_reference_catalog_separates_registered_and_reference_only(self):
        audit = load_audit_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            references = Path(temp_dir)
            (references / "component_reference.md").write_text(
                """# Components
## Samplers
### 1. HTTP Request
### 2. TCP Sampler
## Controllers
### 1. While Controller
## Pre Processors
### 1. User Parameters
## Configuration Elements
### 1. User Defined Variables
### Parameters
""",
                encoding="utf-8",
            )
            (references / "other.md").write_text(
                "HTTP Request and User Parameters are discussed here.\n",
                encoding="utf-8",
            )

            entries = audit.catalog_reference_components(
                references,
                {"http_sampler", "user_parameters", "user_defined_variables"},
            )

        by_name = {entry.display_name: entry for entry in entries}
        self.assertEqual(by_name["HTTP Request"].status, "REGISTERED")
        self.assertEqual(by_name["HTTP Request"].node_type, "http_sampler")
        self.assertEqual(by_name["User Parameters"].status, "REGISTERED")
        self.assertEqual(by_name["User Defined Variables"].status, "REGISTERED")
        self.assertEqual(
            by_name["User Defined Variables"].node_type,
            "user_defined_variables",
        )
        self.assertEqual(by_name["TCP Sampler"].status, "REFERENCE_ONLY")
        self.assertEqual(by_name["While Controller"].status, "REFERENCE_ONLY")
        self.assertNotIn("Parameters", by_name)
        self.assertIn("other.md", by_name["User Parameters"].sources)

    def test_repository_schema_contract_matches_real_registry(self):
        audit = load_audit_module()
        skill_root = SCRIPTS_DIR.parent

        registered = audit.load_registered_types()
        declared = audit.load_contract_types(
            skill_root / "references" / "scenario-schema.md"
        )

        self.assertIn("user_parameters", registered)
        self.assertIn("user_parameters", declared)
        self.assertEqual(declared, registered)


if __name__ == "__main__":
    unittest.main()
