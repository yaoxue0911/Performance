import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
GENERATOR_PATH = SCRIPTS_DIR / "generate_jmx_tree.py"
COMPONENTS_PATH = SCRIPTS_DIR / "jmx_tree_components.py"


def load_generator():
    if not GENERATOR_PATH.exists():
        raise AssertionError("generate_jmx_tree.py has not been implemented")
    spec = importlib.util.spec_from_file_location("generate_jmx_tree", GENERATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def nested_scenario():
    return {
        "test_plan": {"name": "Nested Login Plan"},
        "thread_groups": [
            {
                "name": "Users",
                "threads": "${__P(concurrency,10)}",
                "rampup": "${__P(rampup,10)}",
                "duration": "${__P(duration,60)}",
                "children": [
                    {"type": "cookie_manager", "clear_each_iteration": False},
                    {
                        "type": "once_only_controller",
                        "name": "Login Once Per Thread",
                        "children": [
                            {
                                "type": "transaction_controller",
                                "name": "Login Transaction",
                                "children": [
                                    {
                                        "type": "http_sampler",
                                        "name": "GET Login",
                                        "method": "GET",
                                        "path": "/RMS/Login.aspx",
                                    },
                                    {
                                        "type": "http_sampler",
                                        "name": "GET Home - Verify Login",
                                        "method": "GET",
                                        "path": "/RMS/HomeA.aspx",
                                        "children": [
                                            {
                                                "type": "response_assertion",
                                                "name": "Authenticated Page",
                                                "test_field": "Assertion.response_data",
                                                "patterns": ["/RMS/Logout.aspx"],
                                                "test_type": 16,
                                            }
                                        ],
                                    },
                                ],
                            }
                        ],
                    },
                    {
                        "type": "transaction_controller",
                        "name": "Business Iteration",
                        "children": [
                            {
                                "type": "http_sampler",
                                "name": "POST Create Person",
                                "method": "POST",
                                "path": "/RMS/Person",
                                "params": [{"name": "firstName", "value": "${firstName}"}],
                            }
                        ],
                    },
                ],
            }
        ],
    }


class TreeGeneratorTests(unittest.TestCase):
    def test_once_only_contains_login_and_excludes_business_request(self):
        generator = load_generator()
        root = ET.fromstring(generator.build_jmx(nested_scenario()))

        once = root.find(".//OnceOnlyController")
        self.assertIsNotNone(once)
        parent = next(p for p in root.iter() if once in list(p))
        once_index = list(parent).index(once)
        once_tree = list(parent)[once_index + 1]

        nested_names = [e.get("testname") for e in once_tree.iter("HTTPSamplerProxy")]
        self.assertEqual(nested_names, ["GET Login", "GET Home - Verify Login"])
        self.assertNotIn("POST Create Person", nested_names)

    def test_sampler_children_are_rendered_in_sampler_hash_tree(self):
        generator = load_generator()
        root = ET.fromstring(generator.build_jmx(nested_scenario()))
        sampler = next(
            e for e in root.iter("HTTPSamplerProxy")
            if e.get("testname") == "GET Home - Verify Login"
        )
        parent = next(p for p in root.iter() if sampler in list(p))
        sampler_index = list(parent).index(sampler)
        sampler_tree = list(parent)[sampler_index + 1]

        assertion = sampler_tree.find("ResponseAssertion")
        self.assertIsNotNone(assertion)
        self.assertEqual(assertion.get("testname"), "Authenticated Page")

    def test_empty_once_only_controller_is_rejected(self):
        generator = load_generator()
        scenario = nested_scenario()
        scenario["thread_groups"][0]["children"][1]["children"] = []

        with self.assertRaisesRegex(ValueError, "once_only_controller.*children"):
            generator.build_jmx(scenario)

    def test_unknown_node_type_is_rejected_with_location(self):
        generator = load_generator()
        scenario = nested_scenario()
        scenario["thread_groups"][0]["children"].append({"type": "mystery"})

        with self.assertRaisesRegex(ValueError, r"thread_groups\[0\].children\[3\].*mystery"):
            generator.build_jmx(scenario)

    def test_cli_reads_json_and_writes_parseable_jmx(self):
        load_generator()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            scenario_path = temp_path / "scenario.json"
            output_path = temp_path / "plan.jmx"
            scenario_path.write_text(json.dumps(nested_scenario()), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR_PATH),
                    "--scenario",
                    str(scenario_path),
                    "--output",
                    str(output_path),
                    "--validate",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("JMX structure validation passed", result.stdout)
            self.assertIn("View Results Tree", result.stdout)
            self.assertIn("Simple Data Writer", result.stdout)
            self.assertIn("正式负载测试", result.stdout)
            ET.parse(output_path)

    def test_cli_runs_without_legacy_generate_jmx_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            isolated_generator = temp_path / GENERATOR_PATH.name
            isolated_components = temp_path / COMPONENTS_PATH.name
            scenario_path = temp_path / "scenario.json"
            output_path = temp_path / "plan.jmx"
            shutil.copy2(GENERATOR_PATH, isolated_generator)
            if COMPONENTS_PATH.exists():
                shutil.copy2(COMPONENTS_PATH, isolated_components)
            scenario_path.write_text(json.dumps(nested_scenario()), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(isolated_generator),
                    "--scenario",
                    str(scenario_path),
                    "--output",
                    str(output_path),
                    "--validate",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            ET.parse(output_path)

    def test_cli_has_no_template_mode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "plan.jmx"
            result = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR_PATH),
                    "--template",
                    "base.jmx",
                    "--output",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output_path.exists())
            self.assertIn("--scenario", result.stderr)

    def test_css_and_xpath_extractors_render_under_sampler(self):
        generator = load_generator()
        scenario = nested_scenario()
        home = scenario["thread_groups"][0]["children"][1]["children"][0]["children"][1]
        home["children"] = [
            {
                "type": "css_extractor",
                "name": "Extract CSRF",
                "refname": "csrf",
                "expression": "input[name='__RequestVerificationToken']",
                "attribute": "value",
                "match_number": "1",
                "default_value": "NOT_FOUND",
                "scope": "all",
            },
            {
                "type": "xpath_extractor",
                "name": "Extract VIEWSTATE",
                "refname": "viewstate",
                "xpath_query": "//*[@name='__VIEWSTATE']/@value",
                "match_number": "1",
                "default_value": "NOT_FOUND",
                "scope": "parent",
                "use_tidy": True,
            },
        ]

        root = ET.fromstring(generator.build_jmx(scenario))
        css = root.find(".//HtmlExtractor")
        xpath = root.find(".//XPathExtractor")

        self.assertIsNotNone(css)
        self.assertEqual(css.get("testname"), "Extract CSRF")
        self.assertEqual(css.findtext("stringProp[@name='HtmlExtractor.refname']"), "csrf")
        self.assertEqual(css.findtext("stringProp[@name='HtmlExtractor.expr']"), "input[name='__RequestVerificationToken']")
        self.assertEqual(css.findtext("stringProp[@name='Sample.scope']"), "all")
        self.assertIsNotNone(xpath)
        self.assertEqual(xpath.get("testname"), "Extract VIEWSTATE")
        self.assertEqual(xpath.findtext("stringProp[@name='XPathExtractor.xpathQuery']"), "//*[@name='__VIEWSTATE']/@value")
        self.assertEqual(xpath.findtext("boolProp[@name='XPathExtractor.tolerant']"), "true")
        self.assertEqual(xpath.findtext("stringProp[@name='Sample.scope']"), "parent")

    def test_jdbc_connection_and_sampler_render_as_separate_nodes(self):
        generator = load_generator()
        scenario = nested_scenario()
        scenario["thread_groups"][0]["children"].extend([
            {
                "type": "jdbc_connection_config",
                "name": "Application Database",
                "pool_name": "app_db",
                "database_url": "jdbc:h2:mem:test",
                "driver_class": "org.h2.Driver",
                "username": "sa",
                "password": "",
            },
            {
                "type": "jdbc_sampler",
                "name": "Select Person",
                "pool_name": "app_db",
                "query_type": "Prepared Select Statement",
                "query": "SELECT person_id FROM person WHERE last_name = ?",
                "query_arguments": "${lastName}",
                "query_argument_types": "VARCHAR",
                "variable_names": "person_id",
                "result_variable": "person_rows",
                "query_timeout": "30",
                "result_set_handler": "Store as String",
            },
        ])

        root = ET.fromstring(generator.build_jmx(scenario))
        connection = root.find(".//JDBCDataSource")
        sampler = root.find(".//JDBCSampler")

        self.assertIsNotNone(connection)
        self.assertEqual(connection.findtext("stringProp[@name='dataSource']"), "app_db")
        self.assertEqual(connection.findtext("stringProp[@name='dbUrl']"), "jdbc:h2:mem:test")
        self.assertEqual(connection.findtext("stringProp[@name='driver']"), "org.h2.Driver")
        self.assertIsNotNone(sampler)
        self.assertEqual(sampler.findtext("stringProp[@name='dataSource']"), "app_db")
        self.assertEqual(sampler.findtext("stringProp[@name='queryType']"), "Prepared Select Statement")
        self.assertEqual(sampler.findtext("stringProp[@name='queryArgumentsTypes']"), "VARCHAR")
        self.assertEqual(sampler.findtext("stringProp[@name='queryTimeout']"), "30")

    def test_jdbc_sampler_rejects_unsupported_query_type_with_location(self):
        generator = load_generator()
        scenario = nested_scenario()
        scenario["thread_groups"][0]["children"].append({
            "type": "jdbc_sampler",
            "name": "Bad JDBC",
            "pool_name": "app_db",
            "query_type": "Delete Everything",
            "query": "DELETE FROM person",
        })

        with self.assertRaisesRegex(ValueError, r"thread_groups\[0\].children\[3\].*query_type"):
            generator.build_jmx(scenario)

    def test_jdbc_sampler_rejects_argument_type_count_mismatch(self):
        generator = load_generator()
        scenario = nested_scenario()
        scenario["thread_groups"][0]["children"].append({
            "type": "jdbc_sampler",
            "name": "Bad Arguments",
            "pool_name": "app_db",
            "query_type": "Prepared Select Statement",
            "query": "SELECT * FROM person WHERE first_name = ? AND last_name = ?",
            "query_arguments": "${firstName},${lastName}",
            "query_argument_types": "VARCHAR",
        })

        with self.assertRaisesRegex(ValueError, r"thread_groups\[0\].children\[3\].*argument"):
            generator.build_jmx(scenario)

    def test_explicit_debug_and_load_listeners_use_distinct_profiles(self):
        generator = load_generator()
        scenario = nested_scenario()
        scenario["thread_groups"][0]["children"].extend([
            {"type": "view_results_tree"},
            {"type": "simple_data_writer"},
        ])

        root = ET.fromstring(generator.build_jmx(scenario))
        listeners = root.findall(".//ResultCollector")
        debug = next(item for item in listeners if item.get("guiclass") == "ViewResultsFullVisualizer")
        load = next(item for item in listeners if item.get("guiclass") == "SimpleDataWriter")

        self.assertEqual(debug.get("enabled"), "true")
        self.assertEqual(debug.findtext("stringProp[@name='filename']"), "${__P(debug_result_file,debug.jtl)}")
        self.assertEqual(debug.findtext("objProp/value/responseData"), "true")
        self.assertEqual(debug.findtext("objProp/value/samplerData"), "true")
        self.assertEqual(debug.findtext("objProp/value/responseHeaders"), "true")
        self.assertEqual(debug.findtext("objProp/value/requestHeaders"), "true")
        self.assertEqual(debug.findtext("objProp/value/xml"), "true")
        self.assertEqual(load.get("enabled"), "false")
        self.assertEqual(load.findtext("stringProp[@name='filename']"), "${__P(load_result_file,load.jtl)}")
        self.assertEqual(load.findtext("objProp/value/responseData"), "false")
        self.assertEqual(load.findtext("objProp/value/responseHeaders"), "false")
        self.assertEqual(load.findtext("objProp/value/xml"), "false")


if __name__ == "__main__":
    unittest.main()
