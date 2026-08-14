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
SKILL_PATH = SCRIPTS_DIR.parent / "SKILL.md"


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
    def test_skill_keeps_jmeter_builtin_function_quick_reference(self):
        skill_text = SKILL_PATH.read_text(encoding="utf-8")

        self.assertIn("## JMeter 内置函数速查", skill_text)
        for function_name in (
            "`__P`",
            "`__property`",
            "`__Random`",
            "`__RandomString`",
            "`__UUID`",
            "`__jexl3`",
            "`__groovy`",
        ):
            self.assertIn(function_name, skill_text)

    def test_http_defaults_use_jmeter_properties_for_all_runtime_fields(self):
        generator = load_generator()
        scenario = nested_scenario()
        scenario["thread_groups"][0]["children"].insert(
            0, {"type": "http_defaults"}
        )

        root = ET.fromstring(generator.build_jmx(scenario))
        defaults = root.find(".//ConfigTestElement[@guiclass='HttpDefaultsGui']")

        self.assertIsNotNone(defaults)
        self.assertEqual(
            defaults.findtext("stringProp[@name='HTTPSampler.domain']"),
            "${__P(target_host,localhost)}",
        )
        self.assertEqual(
            defaults.findtext("stringProp[@name='HTTPSampler.port']"),
            "${__P(target_port,80)}",
        )
        self.assertEqual(
            defaults.findtext("stringProp[@name='HTTPSampler.protocol']"),
            "${__P(protocol,http)}",
        )
        self.assertEqual(
            defaults.findtext("stringProp[@name='HTTPSampler.contentEncoding']"),
            "${__P(content_encoding,UTF-8)}",
        )
        self.assertEqual(
            defaults.findtext("stringProp[@name='HTTPSampler.path']"),
            "${__P(base_path,/)}",
        )

    def test_http_defaults_reject_literal_runtime_fields(self):
        generator = load_generator()
        scenario = nested_scenario()
        scenario["thread_groups"][0]["children"].insert(
            0,
            {
                "type": "http_defaults",
                "host": "example.invalid",
                "protocol": "https",
            },
        )

        with self.assertRaisesRegex(
            ValueError,
            r"thread_groups\[0\]\.children\[0\].*host.*\$\{__P",
        ):
            generator.build_jmx(scenario)

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

    def test_user_parameters_render_natively_at_loop_scope(self):
        generator = load_generator()
        scenario = nested_scenario()
        original_business = scenario["thread_groups"][0]["children"][2]
        user_parameters_node = {
            "type": "user_parameters",
            "name": "Per-report dynamic data",
            "per_iteration": True,
            "parameters": [
                {"name": "firstName", "values": ["TEST${__Random(1000,9999)}"]},
                {"name": "lastName", "values": ["TEST${__Random(1000,9999)}"]},
            ],
        }
        scenario["thread_groups"][0]["children"][2] = {
            "type": "loop_controller",
            "name": "Business Iteration",
            "loops": "-1",
            "children": [user_parameters_node, original_business],
        }

        root = ET.fromstring(generator.build_jmx(scenario))
        user_parameters = root.find(".//UserParameters")

        self.assertIsNotNone(user_parameters)
        self.assertEqual(user_parameters.get("testname"), "Per-report dynamic data")
        self.assertEqual(user_parameters.get("guiclass"), "UserParametersGui")
        self.assertEqual(user_parameters.get("testclass"), "UserParameters")
        self.assertEqual(
            [item.text for item in user_parameters.findall(
                "collectionProp[@name='UserParameters.names']/stringProp"
            )],
            ["firstName", "lastName"],
        )
        self.assertEqual(
            user_parameters.findtext("boolProp[@name='UserParameters.per_iteration']"),
            "true",
        )
        loop = root.find(".//LoopController[@testname='Business Iteration']")
        parent = next(item for item in root.iter() if loop in list(item))
        loop_tree = list(parent)[list(parent).index(loop) + 1]
        self.assertEqual(list(loop_tree)[0].tag, "UserParameters")

    def test_user_parameters_transpose_user_value_columns(self):
        generator = load_generator()
        scenario = nested_scenario()
        scenario["thread_groups"][0]["children"].append({
            "type": "user_parameters",
            "per_iteration": False,
            "parameters": [
                {"name": "username", "values": ["alice", "bob"]},
                {"name": "region", "values": ["east", "west"]},
            ],
        })

        root = ET.fromstring(generator.build_jmx(scenario))
        user_parameters = root.find(".//UserParameters")
        columns = user_parameters.findall(
            "collectionProp[@name='UserParameters.thread_values']/collectionProp"
        )

        self.assertEqual(
            [[value.text for value in column.findall("stringProp")] for column in columns],
            [["alice", "east"], ["bob", "west"]],
        )
        self.assertEqual(
            user_parameters.findtext("boolProp[@name='UserParameters.per_iteration']"),
            "false",
        )

    def test_user_parameters_reject_invalid_parameter_tables_with_location(self):
        generator = load_generator()
        invalid_tables = [
            [],
            [{"name": "", "values": ["x"]}],
            [{"name": "same", "values": ["x"]}, {"name": "same", "values": ["y"]}],
            [{"name": "x", "values": []}],
            [{"name": "x", "values": [1]}],
            [{"name": "x", "values": ["a", "b"]}, {"name": "y", "values": ["c"]}],
        ]

        for parameters in invalid_tables:
            with self.subTest(parameters=parameters):
                scenario = nested_scenario()
                scenario["thread_groups"][0]["children"].append({
                    "type": "user_parameters",
                    "parameters": parameters,
                })
                with self.assertRaisesRegex(
                    ValueError,
                    r"thread_groups\[0\]\.children\[3\].*parameters",
                ):
                    generator.build_jmx(scenario)

    def test_user_defined_variables_render_as_independent_scoped_node(self):
        generator = load_generator()
        scenario = nested_scenario()
        scenario["thread_groups"][0]["children"].insert(1, {
            "type": "user_defined_variables",
            "name": "Thread-scoped constants",
            "variables": {
                "division_id": "3",
                "master_location_id": "19198",
            },
        })

        root = ET.fromstring(generator.build_jmx(scenario))
        variables = root.find(".//Arguments[@testname='Thread-scoped constants']")

        self.assertIsNotNone(variables)
        self.assertEqual(variables.get("guiclass"), "ArgumentsPanel")
        self.assertEqual(variables.get("testclass"), "Arguments")
        arguments = variables.findall(
            "collectionProp[@name='Arguments.arguments']/elementProp"
        )
        self.assertEqual(
            [item.findtext("stringProp[@name='Argument.name']") for item in arguments],
            ["division_id", "master_location_id"],
        )
        self.assertEqual(
            [item.findtext("stringProp[@name='Argument.value']") for item in arguments],
            ["3", "19198"],
        )
        thread_group = root.find(".//ThreadGroup")
        parent = next(item for item in root.iter() if thread_group in list(item))
        thread_tree = list(parent)[list(parent).index(thread_group) + 1]
        self.assertIn(variables, list(thread_tree))

    def test_user_defined_variables_reject_invalid_maps_with_location(self):
        generator = load_generator()
        invalid_maps = [
            {},
            {"": "value"},
            {"name": 123},
        ]

        for variables in invalid_maps:
            with self.subTest(variables=variables):
                scenario = nested_scenario()
                scenario["thread_groups"][0]["children"].append({
                    "type": "user_defined_variables",
                    "variables": variables,
                })
                with self.assertRaisesRegex(
                    ValueError,
                    r"thread_groups\[0\]\.children\[3\].*variables",
                ):
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

    def test_regex_extractor_renders_explicit_redirect_scope(self):
        generator = load_generator()
        scenario = nested_scenario()
        home = scenario["thread_groups"][0]["children"][1]["children"][0]["children"][1]
        home["children"] = [
            {
                "type": "regex_extractor",
                "name": "Extract redirect value",
                "refname": "redirect_value",
                "regex": r"value=(\d+)",
                "scope": "all",
            }
        ]

        root = ET.fromstring(generator.build_jmx(scenario))
        extractor = root.find(".//RegexExtractor")

        self.assertIsNotNone(extractor)
        self.assertEqual(
            extractor.findtext("stringProp[@name='Sample.scope']"),
            "all",
        )

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
