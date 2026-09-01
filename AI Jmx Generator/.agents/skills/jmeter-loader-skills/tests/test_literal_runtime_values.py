import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from generate_jmx_tree import build_jmx  # noqa: E402


class LiteralRuntimeValuesTest(unittest.TestCase):
    def test_component_defaults_are_direct_values(self):
        xml = build_jmx(
            {
                "test_plan": {"name": "Literal values"},
                "thread_groups": [
                    {
                        "name": "Users",
                        "children": [
                            {"type": "http_defaults"},
                            {"type": "constant_timer"},
                            {"type": "gaussian_timer"},
                            {"type": "uniform_timer"},
                            {"type": "synchronizing_timer"},
                            {"type": "view_results_tree"},
                            {"type": "simple_data_writer"},
                        ],
                    }
                ],
            }
        )

        root = ET.fromstring(xml)
        properties = {
            element.attrib["name"]: element.text
            for element in root.iter()
            if element.tag in {"stringProp", "intProp", "longProp"}
            and "name" in element.attrib
        }

        self.assertEqual("10", properties["ThreadGroup.num_threads"])
        self.assertEqual("10", properties["ThreadGroup.ramp_time"])
        self.assertEqual("60", properties["ThreadGroup.duration"])
        self.assertEqual("-1", properties["LoopController.loops"])
        self.assertEqual("0", properties["ThreadGroup.delay"])
        self.assertEqual("localhost", properties["HTTPSampler.domain"])
        self.assertEqual("80", properties["HTTPSampler.port"])
        self.assertEqual("http", properties["HTTPSampler.protocol"])
        self.assertEqual("UTF-8", properties["HTTPSampler.contentEncoding"])
        self.assertEqual("/", properties["HTTPSampler.path"])
        self.assertEqual("1000", properties["ConstantTimer.delay"])
        self.assertEqual("500", properties["RandomTimer.range"])
        self.assertEqual("10", properties["groupSize"])
        self.assertEqual("0", properties["timeoutInMs"])
        self.assertNotIn("${", xml)

        filenames = [
            element.text
            for element in root.iter("stringProp")
            if element.attrib.get("name") == "filename"
        ]
        self.assertEqual(["debug.jtl", "load.jtl"], filenames)

    def test_numeric_load_fields_require_integers(self):
        scenario = {
            "test_plan": {"name": "Invalid values"},
            "thread_groups": [
                {
                    "name": "Users",
                    "threads": "ten",
                    "children": [{"type": "http_defaults"}],
                }
            ],
        }

        with self.assertRaisesRegex(ValueError, "threads must be a concrete integer"):
            build_jmx(scenario)

    def test_http_defaults_require_direct_strings(self):
        scenario = {
            "test_plan": {"name": "Invalid values"},
            "thread_groups": [
                {
                    "name": "Users",
                    "children": [
                        {
                            "type": "http_defaults",
                            "host": "${dynamic_host}",
                            "port": 443,
                            "protocol": "https",
                            "encoding": "UTF-8",
                            "path": "/",
                        }
                    ],
                }
            ],
        }

        with self.assertRaisesRegex(ValueError, "host must be a direct string"):
            build_jmx(scenario)

    def test_all_numeric_runtime_fields_reject_strings(self):
        group_cases = (
            ("threads", "10"),
            ("rampup", "10"),
            ("duration", "60"),
            ("loops", "-1"),
            ("delay", "0"),
        )
        child_cases = (
            ({"type": "http_defaults", "port": "443"}, "port"),
            ({"type": "constant_timer", "delay_ms": "1000"}, "delay_ms"),
            ({"type": "gaussian_timer", "delay_ms": "1000"}, "delay_ms"),
            ({"type": "gaussian_timer", "range_ms": "300"}, "range_ms"),
            ({"type": "uniform_timer", "delay_ms": "1000"}, "delay_ms"),
            ({"type": "uniform_timer", "range_ms": "500"}, "range_ms"),
            ({"type": "synchronizing_timer", "group_size": "10"}, "group_size"),
            ({"type": "synchronizing_timer", "timeout_ms": "0"}, "timeout_ms"),
            ({"type": "loop_controller", "loops": "5", "children": [{"type": "debug_sampler"}]}, "loops"),
        )

        for field_name, value in group_cases:
            with self.subTest(field=field_name):
                group = {
                    "name": "Users",
                    field_name: value,
                    "children": [{"type": "http_defaults"}],
                }
                with self.assertRaisesRegex(
                    ValueError,
                    f"{field_name} must be a concrete integer",
                ):
                    build_jmx(
                        {
                            "test_plan": {"name": "Invalid values"},
                            "thread_groups": [group],
                        }
                    )

        for child, field_name in child_cases:
            with self.subTest(type=child["type"], field=field_name):
                with self.assertRaisesRegex(
                    ValueError,
                    f"{field_name} must be a concrete integer",
                ):
                    build_jmx(
                        {
                            "test_plan": {"name": "Invalid values"},
                            "thread_groups": [
                                {
                                    "name": "Users",
                                    "children": [child],
                                }
                            ],
                        }
                    )


if __name__ == "__main__":
    unittest.main()
