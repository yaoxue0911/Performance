"""JMeter XML component factories used only by the tree generator."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Dict, List


class JMXComponentBuilder:
    """Build individual JMeter elements without assembling their hierarchy."""

    @staticmethod
    def _bool_prop(name: str, value: bool) -> ET.Element:
        element = ET.Element("boolProp", {"name": name})
        element.text = "true" if value else "false"
        return element

    @staticmethod
    def _int_prop(name: str, value: int) -> ET.Element:
        element = ET.Element("intProp", {"name": name})
        element.text = str(value)
        return element

    @staticmethod
    def _string_prop(name: str, value: object) -> ET.Element:
        element = ET.Element("stringProp", {"name": name})
        element.text = str(value)
        return element

    @staticmethod
    def _collection_prop(name: str) -> ET.Element:
        return ET.Element("collectionProp", {"name": name})

    @staticmethod
    def _element_prop(name: str, element_type: str) -> ET.Element:
        return ET.Element("elementProp", {"name": name, "elementType": element_type})

    @staticmethod
    def _named_element(tag: str, gui: str, test_class: str, name: str) -> ET.Element:
        return ET.Element(
            tag,
            {
                "guiclass": gui,
                "testclass": test_class,
                "testname": name,
                "enabled": "true",
            },
        )

    @staticmethod
    def _header(name: str, value: str) -> ET.Element:
        element = JMXComponentBuilder._element_prop("", "Header")
        element.append(JMXComponentBuilder._string_prop("Header.name", name))
        element.append(JMXComponentBuilder._string_prop("Header.value", value))
        return element

    @staticmethod
    def _http_argument(
        name: str,
        value: str,
        use_equals: bool = True,
        always_encode: bool = True,
    ) -> ET.Element:
        element = JMXComponentBuilder._element_prop(name, "HTTPArgument")
        element.append(
            JMXComponentBuilder._bool_prop(
                "HTTPArgument.always_encode", always_encode
            )
        )
        element.append(JMXComponentBuilder._string_prop("Argument.value", value))
        element.append(JMXComponentBuilder._string_prop("Argument.metadata", "="))
        if use_equals:
            element.append(
                JMXComponentBuilder._bool_prop("HTTPArgument.use_equals", True)
            )
            element.append(JMXComponentBuilder._string_prop("Argument.name", name))
        return element

    @staticmethod
    def build_test_plan(
        name: str = "Test Plan",
        comments: str = "",
        functional_mode: bool = False,
        serialize_tg: bool = False,
        variables: Dict[str, str] | None = None,
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "TestPlan", "TestPlanGui", "TestPlan", name
        )
        element.append(JMXComponentBuilder._string_prop("TestPlan.comments", comments))
        element.append(
            JMXComponentBuilder._bool_prop("TestPlan.functional_mode", functional_mode)
        )
        element.append(
            JMXComponentBuilder._bool_prop("TestPlan.tearDown_on_shutdown", True)
        )
        element.append(
            JMXComponentBuilder._bool_prop(
                "TestPlan.serialize_threadgroups", serialize_tg
            )
        )
        variables_element = ET.Element(
            "elementProp",
            {
                "name": "TestPlan.user_defined_variables",
                "elementType": "Arguments",
                "guiclass": "ArgumentsPanel",
                "testclass": "Arguments",
                "testname": "User Defined Variables",
                "enabled": "true",
            },
        )
        arguments = JMXComponentBuilder._collection_prop("Arguments.arguments")
        for key, value in (variables or {}).items():
            argument = JMXComponentBuilder._element_prop(key, "Argument")
            argument.append(JMXComponentBuilder._string_prop("Argument.name", key))
            argument.append(JMXComponentBuilder._string_prop("Argument.value", value))
            argument.append(JMXComponentBuilder._string_prop("Argument.metadata", "="))
            arguments.append(argument)
        variables_element.append(arguments)
        element.append(variables_element)
        element.append(
            JMXComponentBuilder._string_prop("TestPlan.user_define_classpath", "")
        )
        return element

    @staticmethod
    def build_thread_group(
        name: str = "Thread Group",
        threads: str = "${__P(concurrency,10)}",
        rampup: str = "${__P(rampup,10)}",
        duration: str = "${__P(duration,60)}",
        loops: str = "-1",
        on_sample_error: str = "continue",
        same_user: bool = True,
        delay: str = "",
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "ThreadGroup", "ThreadGroupGui", "ThreadGroup", name
        )
        element.append(
            JMXComponentBuilder._string_prop(
                "ThreadGroup.on_sample_error", on_sample_error
            )
        )
        controller = ET.Element(
            "elementProp",
            {
                "name": "ThreadGroup.main_controller",
                "elementType": "LoopController",
                "guiclass": "LoopControlPanel",
                "testclass": "LoopController",
                "testname": "Loop Controller",
                "enabled": "true",
            },
        )
        controller.append(
            JMXComponentBuilder._bool_prop("LoopController.continue_forever", True)
        )
        controller.append(
            JMXComponentBuilder._string_prop("LoopController.loops", loops)
        )
        element.append(controller)
        element.append(
            JMXComponentBuilder._string_prop("ThreadGroup.num_threads", threads)
        )
        element.append(
            JMXComponentBuilder._string_prop("ThreadGroup.ramp_time", rampup)
        )
        element.append(JMXComponentBuilder._bool_prop("ThreadGroup.scheduler", True))
        element.append(
            JMXComponentBuilder._string_prop("ThreadGroup.duration", duration)
        )
        element.append(JMXComponentBuilder._string_prop("ThreadGroup.delay", delay))
        element.append(
            JMXComponentBuilder._bool_prop(
                "ThreadGroup.same_user_on_next_iteration", same_user
            )
        )
        return element

    @staticmethod
    def build_http_defaults(
        host: str = "${__P(target_host,localhost)}",
        port: str = "${__P(target_port,80)}",
        protocol: str = "${__P(protocol,http)}",
        encoding: str = "UTF-8",
        path: str = "",
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "ConfigTestElement",
            "HttpDefaultsGui",
            "ConfigTestElement",
            "HTTP Request Defaults",
        )
        arguments = ET.Element(
            "elementProp",
            {
                "name": "HTTPsampler.Arguments",
                "elementType": "Arguments",
                "guiclass": "HTTPArgumentsPanel",
                "testclass": "Arguments",
                "enabled": "true",
            },
        )
        arguments.append(JMXComponentBuilder._collection_prop("Arguments.arguments"))
        element.append(arguments)
        for prop_name, value in (
            ("HTTPSampler.domain", host),
            ("HTTPSampler.port", port),
            ("HTTPSampler.protocol", protocol),
            ("HTTPSampler.contentEncoding", encoding),
            ("HTTPSampler.path", path),
            ("HTTPSampler.concurrentPool", "6"),
        ):
            element.append(JMXComponentBuilder._string_prop(prop_name, value))
        element.append(
            JMXComponentBuilder._bool_prop("HTTPSampler.embedded_url_re", False)
        )
        return element

    @staticmethod
    def build_header_manager(
        headers: List[Dict[str, str]] | None = None,
    ) -> ET.Element:
        headers = headers or [
            {"name": "Content-Type", "value": "application/json"},
            {"name": "Accept", "value": "application/json"},
        ]
        element = JMXComponentBuilder._named_element(
            "HeaderManager", "HeaderPanel", "HeaderManager", "HTTP Header Manager"
        )
        collection = JMXComponentBuilder._collection_prop("HeaderManager.headers")
        for header in headers:
            collection.append(
                JMXComponentBuilder._header(header["name"], header["value"])
            )
        element.append(collection)
        return element

    @staticmethod
    def build_cookie_manager(clear_each_iteration: bool = False) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "CookieManager", "CookiePanel", "CookieManager", "HTTP Cookie Manager"
        )
        element.append(JMXComponentBuilder._collection_prop("CookieManager.cookies"))
        element.append(
            JMXComponentBuilder._bool_prop(
                "CookieManager.clearEachIteration", clear_each_iteration
            )
        )
        element.append(
            JMXComponentBuilder._bool_prop(
                "CookieManager.controlledByThreadGroup", True
            )
        )
        return element

    @staticmethod
    def build_cache_manager(
        clear_each_iteration: bool = False,
        use_expires: bool = True,
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "CacheManager", "CacheManagerGui", "CacheManager", "HTTP Cache Manager"
        )
        element.append(
            JMXComponentBuilder._bool_prop("clearEachIteration", clear_each_iteration)
        )
        element.append(JMXComponentBuilder._bool_prop("useExpires", use_expires))
        element.append(JMXComponentBuilder._string_prop("maxCacheSize", "5000"))
        return element

    @staticmethod
    def build_csv_data_set(
        filename: str = "testdata.csv",
        variable_names: str = "username,password",
        delimiter: str = ",",
        ignore_first_line: bool = True,
        recycle: bool = True,
        stop_thread: bool = False,
        share_mode: str = "shareMode.thread",
        encoding: str = "",
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "CSVDataSet", "TestBeanGUI", "CSVDataSet", "CSV Data Set Config"
        )
        for prop_name, value in (
            ("delimiter", delimiter),
            ("fileEncoding", encoding),
            ("filename", filename),
        ):
            element.append(JMXComponentBuilder._string_prop(prop_name, value))
        element.append(
            JMXComponentBuilder._bool_prop("ignoreFirstLine", ignore_first_line)
        )
        element.append(JMXComponentBuilder._bool_prop("quotedData", False))
        element.append(JMXComponentBuilder._bool_prop("recycle", recycle))
        element.append(JMXComponentBuilder._string_prop("shareMode", share_mode))
        element.append(JMXComponentBuilder._bool_prop("stopThread", stop_thread))
        element.append(
            JMXComponentBuilder._string_prop("variableNames", variable_names)
        )
        return element

    @staticmethod
    def build_http_sampler(
        name: str = "HTTP Request",
        method: str = "GET",
        path: str = "/",
        host: str = "",
        port: str = "",
        protocol: str = "",
        encoding: str = "",
        body: str = "",
        params: List[Dict[str, object]] | None = None,
        connect_timeout: str = "",
        response_timeout: str = "",
        follow_redirects: bool = True,
        use_keepalive: bool = True,
        post_body_raw: bool = False,
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "HTTPSamplerProxy", "HttpTestSampleGui", "HTTPSamplerProxy", name
        )
        arguments = ET.Element(
            "elementProp",
            {
                "name": "HTTPsampler.Arguments",
                "elementType": "Arguments",
                "guiclass": "HTTPArgumentsPanel",
                "testclass": "Arguments",
                "enabled": "true",
            },
        )
        collection = JMXComponentBuilder._collection_prop("Arguments.arguments")
        if post_body_raw and body:
            collection.append(
                JMXComponentBuilder._http_argument(
                    "", body, use_equals=True, always_encode=False
                )
            )
        else:
            for parameter in params or []:
                collection.append(
                    JMXComponentBuilder._http_argument(
                        str(parameter.get("name", "")),
                        str(parameter.get("value", "")),
                        use_equals=bool(parameter.get("use_equals", True)),
                        always_encode=bool(parameter.get("always_encode", True)),
                    )
                )
        arguments.append(collection)
        element.append(arguments)
        for prop_name, value in (
            ("HTTPSampler.domain", host),
            ("HTTPSampler.port", port),
            ("HTTPSampler.protocol", protocol),
            ("HTTPSampler.contentEncoding", encoding),
            ("HTTPSampler.path", path),
            ("HTTPSampler.method", method),
        ):
            element.append(JMXComponentBuilder._string_prop(prop_name, value))
        element.append(
            JMXComponentBuilder._bool_prop(
                "HTTPSampler.follow_redirects", follow_redirects
            )
        )
        element.append(
            JMXComponentBuilder._bool_prop("HTTPSampler.auto_redirects", False)
        )
        element.append(
            JMXComponentBuilder._bool_prop("HTTPSampler.use_keepalive", use_keepalive)
        )
        element.append(
            JMXComponentBuilder._bool_prop("HTTPSampler.DO_MULTIPART_POST", False)
        )
        if post_body_raw and body:
            element.append(
                JMXComponentBuilder._bool_prop("HTTPSampler.postBodyRaw", True)
            )
        element.append(
            JMXComponentBuilder._string_prop("HTTPSampler.embedded_url_re", "")
        )
        element.append(
            JMXComponentBuilder._string_prop(
                "HTTPSampler.connect_timeout", connect_timeout
            )
        )
        element.append(
            JMXComponentBuilder._string_prop(
                "HTTPSampler.response_timeout", response_timeout
            )
        )
        return element

    @staticmethod
    def build_debug_sampler(
        display_jmeter_vars: bool = True,
        display_jmeter_props: bool = False,
        display_system_props: bool = False,
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "DebugSampler", "TestBeanGUI", "DebugSampler", "Debug Sampler"
        )
        element.append(
            JMXComponentBuilder._bool_prop(
                "displayJMeterProperties", display_jmeter_props
            )
        )
        element.append(
            JMXComponentBuilder._bool_prop(
                "displayJMeterVariables", display_jmeter_vars
            )
        )
        element.append(
            JMXComponentBuilder._bool_prop(
                "displaySystemProperties", display_system_props
            )
        )
        return element

    @staticmethod
    def build_jdbc_connection_config(
        pool_name: str,
        database_url: str,
        driver_class: str,
        name: str = "JDBC Connection Configuration",
        username: str = "",
        password: str = "",
        max_connections: str = "10",
        connection_timeout_ms: str = "10000",
        validation_query: str = "SELECT 1",
        connection_properties: str = "",
        connection_age_ms: str = "5000",
        keep_alive: bool = True,
        auto_commit: bool = True,
        transaction_isolation: str = "DEFAULT",
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "JDBCDataSource", "DataSourcePanelGui", "JDBCDataSource", name
        )
        element.append(JMXComponentBuilder._bool_prop("autocommit", auto_commit))
        for prop_name, value in (
            ("checkQuery", validation_query),
            ("connectionAge", connection_age_ms),
            ("connectionProperties", connection_properties),
            ("dataSource", pool_name),
            ("dbUrl", database_url),
            ("driver", driver_class),
        ):
            element.append(JMXComponentBuilder._string_prop(prop_name, value))
        element.append(JMXComponentBuilder._bool_prop("keepAlive", keep_alive))
        for prop_name, value in (
            ("password", password),
            ("poolMax", max_connections),
            ("timeout", connection_timeout_ms),
            ("transactionIsolation", transaction_isolation),
            ("username", username),
        ):
            element.append(JMXComponentBuilder._string_prop(prop_name, value))
        return element

    @staticmethod
    def build_jdbc_sampler(
        name: str,
        pool_name: str,
        query_type: str,
        query: str,
        query_arguments: str = "",
        query_argument_types: str = "",
        variable_names: str = "",
        result_variable: str = "",
        query_timeout: str = "",
        result_set_handler: str = "Store as String",
    ) -> ET.Element:
        supported_query_types = {
            "Select Statement",
            "Update Statement",
            "Callable Statement",
            "Prepared Select Statement",
            "Prepared Update Statement",
            "Commit",
            "Rollback",
            "AutoCommit(false)",
            "AutoCommit(true)",
        }
        if query_type not in supported_query_types:
            raise ValueError(
                f"query_type must be one of {sorted(supported_query_types)}, got {query_type!r}"
            )

        arguments = [item.strip() for item in query_arguments.split(",") if item.strip()]
        argument_types = [
            item.strip() for item in query_argument_types.split(",") if item.strip()
        ]
        if len(arguments) != len(argument_types):
            raise ValueError(
                "query argument count must match query argument type count"
            )

        element = JMXComponentBuilder._named_element(
            "JDBCSampler", "JDBCTestElementGui", "JDBCSampler", name
        )
        for prop_name, value in (
            ("dataSource", pool_name),
            ("query", query),
            ("queryType", query_type),
            ("variableNames", variable_names),
            ("queryArguments", query_arguments),
            ("queryArgumentsTypes", query_argument_types),
            ("resultVariable", result_variable),
            ("queryTimeout", query_timeout),
            ("resultSetHandler", result_set_handler),
        ):
            element.append(JMXComponentBuilder._string_prop(prop_name, value))
        return element

    @staticmethod
    def build_if_controller(
        condition: str,
        evaluate_all: bool = False,
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "IfController", "IfControllerPanel", "IfController", "If Controller"
        )
        element.append(
            JMXComponentBuilder._string_prop("IfController.condition", condition)
        )
        element.append(
            JMXComponentBuilder._bool_prop(
                "IfController.evaluateAll", evaluate_all
            )
        )
        element.append(
            JMXComponentBuilder._bool_prop("IfController.useExpression", True)
        )
        return element

    @staticmethod
    def build_transaction_controller(
        name: str,
        parent: bool = True,
        include_timers: bool = False,
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "TransactionController",
            "TransactionControllerGui",
            "TransactionController",
            name,
        )
        element.append(
            JMXComponentBuilder._bool_prop(
                "TransactionController.include_timers", include_timers
            )
        )
        element.append(
            JMXComponentBuilder._bool_prop("TransactionController.parent", parent)
        )
        return element

    @staticmethod
    def build_once_only_controller() -> ET.Element:
        return JMXComponentBuilder._named_element(
            "OnceOnlyController",
            "OnceOnlyControllerGui",
            "OnceOnlyController",
            "Once Only Controller",
        )

    @staticmethod
    def build_loop_controller(loops: str = "5") -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "LoopController", "LoopControlPanel", "LoopController", "Loop Controller"
        )
        element.append(
            JMXComponentBuilder._bool_prop("LoopController.continue_forever", False)
        )
        element.append(
            JMXComponentBuilder._string_prop("LoopController.loops", loops)
        )
        return element

    @staticmethod
    def build_foreach_controller(
        input_prefix: str,
        output_var: str,
        start_index: str = "0",
        end_index: str = "-1",
        use_separator: bool = True,
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "ForeachController",
            "ForeachControlPanel",
            "ForeachController",
            "ForEach Controller",
        )
        for prop_name, value in (
            ("ForeachController.inputVal", input_prefix),
            ("ForeachController.startIndex", start_index),
            ("ForeachController.endIndex", end_index),
            ("ForeachController.returnVal", output_var),
        ):
            element.append(JMXComponentBuilder._string_prop(prop_name, value))
        element.append(
            JMXComponentBuilder._bool_prop(
                "ForeachController.useSeparator", use_separator
            )
        )
        return element

    @staticmethod
    def build_constant_timer(
        delay_ms: str = "${__P(think_time,1000)}",
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "ConstantTimer", "ConstantTimerGui", "ConstantTimer", "Constant Timer"
        )
        element.append(
            JMXComponentBuilder._string_prop("ConstantTimer.delay", delay_ms)
        )
        return element

    @staticmethod
    def build_gaussian_timer(
        delay_ms: str = "1000",
        range_ms: str = "300",
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "GaussianRandomTimer",
            "GaussianRandomTimerGui",
            "GaussianRandomTimer",
            "Gaussian Random Timer",
        )
        element.append(
            JMXComponentBuilder._string_prop("ConstantTimer.delay", delay_ms)
        )
        element.append(
            JMXComponentBuilder._string_prop("RandomTimer.range", range_ms)
        )
        return element

    @staticmethod
    def build_uniform_timer(
        delay_ms: str = "1000",
        range_ms: str = "500",
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "UniformRandomTimer",
            "UniformRandomTimerGui",
            "UniformRandomTimer",
            "Uniform Random Timer",
        )
        element.append(
            JMXComponentBuilder._string_prop("ConstantTimer.delay", delay_ms)
        )
        element.append(
            JMXComponentBuilder._string_prop("RandomTimer.range", range_ms)
        )
        return element

    @staticmethod
    def build_synchronizing_timer(
        group_size: str = "10",
        timeout_ms: str = "0",
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "Synchronizer", "SynchronizerGui", "Synchronizer", "Synchronizing Timer"
        )
        element.append(JMXComponentBuilder._string_prop("groupSize", group_size))
        element.append(JMXComponentBuilder._string_prop("timeoutInMs", timeout_ms))
        return element

    @staticmethod
    def build_json_extractor(
        refname: str,
        json_path: str,
        match_number: str = "1",
        default_value: str = "NOT_FOUND",
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "JSONPostProcessor",
            "JSONPostProcessorGui",
            "JSONPostProcessor",
            f"JE_{refname}",
        )
        for prop_name, value in (
            ("JSONPostProcessor.referenceNames", refname),
            ("JSONPostProcessor.jsonPathExprs", json_path),
            ("JSONPostProcessor.match_numbers", match_number),
            ("JSONPostProcessor.default_values", default_value),
        ):
            element.append(JMXComponentBuilder._string_prop(prop_name, value))
        return element

    @staticmethod
    def build_css_extractor(
        refname: str,
        expression: str,
        name: str = "CSS Selector Extractor",
        attribute: str = "text",
        match_number: str = "1",
        default_value: str = "NOT_FOUND",
        default_empty_value: bool = False,
        scope: str = "parent",
        implementation: str = "",
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "HtmlExtractor", "HtmlExtractorGui", "HtmlExtractor", name
        )
        for prop_name, value in (
            ("HtmlExtractor.refname", refname),
            ("HtmlExtractor.expr", expression),
            ("HtmlExtractor.attribute", attribute),
            ("HtmlExtractor.default", default_value),
        ):
            element.append(JMXComponentBuilder._string_prop(prop_name, value))
        element.append(
            JMXComponentBuilder._bool_prop(
                "HtmlExtractor.default_empty_value", default_empty_value
            )
        )
        for prop_name, value in (
            ("HtmlExtractor.match_number", match_number),
            ("HtmlExtractor.extractor_impl", implementation),
            ("Sample.scope", scope),
        ):
            element.append(JMXComponentBuilder._string_prop(prop_name, value))
        return element

    @staticmethod
    def build_xpath_extractor(
        refname: str,
        xpath_query: str,
        name: str = "XPath Extractor",
        match_number: str = "1",
        default_value: str = "NOT_FOUND",
        scope: str = "parent",
        use_tidy: bool = True,
        quiet: bool = True,
        report_errors: bool = False,
        show_warnings: bool = False,
        use_namespaces: bool = False,
        validate_xml: bool = False,
        ignore_whitespace: bool = True,
        fetch_external_dtds: bool = False,
        return_fragment: bool = False,
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "XPathExtractor", "XPathExtractorGui", "XPathExtractor", name
        )
        for prop_name, value in (
            ("XPathExtractor.default", default_value),
            ("XPathExtractor.refname", refname),
            ("XPathExtractor.matchNumber", match_number),
            ("XPathExtractor.xpathQuery", xpath_query),
        ):
            element.append(JMXComponentBuilder._string_prop(prop_name, value))
        for prop_name, value in (
            ("XPathExtractor.validate", validate_xml),
            ("XPathExtractor.tolerant", use_tidy),
            ("XPathExtractor.namespace", use_namespaces),
            ("XPathExtractor.quiet", quiet),
            ("XPathExtractor.show_warnings", show_warnings),
            ("XPathExtractor.report_errors", report_errors),
            ("XPathExtractor.download_dtds", fetch_external_dtds),
            ("XPathExtractor.whitespace", ignore_whitespace),
            ("XPathExtractor.fragment", return_fragment),
        ):
            element.append(JMXComponentBuilder._bool_prop(prop_name, value))
        element.append(JMXComponentBuilder._string_prop("Sample.scope", scope))
        return element

    @staticmethod
    def build_boundary_extractor(
        refname: str,
        left_boundary: str,
        right_boundary: str,
        match_number: str = "1",
        default_value: str = "NOT_FOUND",
        use_headers: str = "false",
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "BoundaryExtractor",
            "BoundaryExtractorGui",
            "BoundaryExtractor",
            f"BE_{refname}",
        )
        for prop_name, value in (
            ("BoundaryExtractor.refname", refname),
            ("BoundaryExtractor.boundaries", left_boundary),
            ("BoundaryExtractor.rightBoundary", right_boundary),
            ("BoundaryExtractor.defaultValue", default_value),
            ("BoundaryExtractor.matchNumber", match_number),
            ("BoundaryExtractor.useHeaders", use_headers),
        ):
            element.append(JMXComponentBuilder._string_prop(prop_name, value))
        return element

    @staticmethod
    def build_regex_extractor(
        refname: str,
        regex: str,
        template: str = "$1$",
        match_number: str = "1",
        default_value: str = "NOT_FOUND",
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "RegexExtractor", "RegexExtractorGui", "RegexExtractor", f"RE_{refname}"
        )
        for prop_name, value in (
            ("RegexExtractor.useHeaders", "false"),
            ("RegexExtractor.refname", refname),
            ("RegexExtractor.regex", regex),
            ("RegexExtractor.template", template),
            ("RegexExtractor.match_number", match_number),
            ("RegexExtractor.default", default_value),
        ):
            element.append(JMXComponentBuilder._string_prop(prop_name, value))
        return element

    @staticmethod
    def build_response_assertion(
        name: str = "Response Assertion",
        test_field: str = "Assertion.response_code",
        test_type: int = 16,
        patterns: List[str] | None = None,
        custom_message: str = "",
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "ResponseAssertion", "AssertionGui", "ResponseAssertion", name
        )
        collection = JMXComponentBuilder._collection_prop("Asserter.test_strings")
        for index, pattern in enumerate(patterns or ["200"]):
            pattern_text = str(pattern)
            collection.append(
                JMXComponentBuilder._string_prop(
                    f"{pattern_text}_{index}", pattern_text
                )
            )
        element.append(collection)
        element.append(
            JMXComponentBuilder._string_prop(
                "Assertion.custom_message", custom_message
            )
        )
        element.append(
            JMXComponentBuilder._string_prop("Assertion.test_field", test_field)
        )
        element.append(
            JMXComponentBuilder._bool_prop("Assertion.assume_success", False)
        )
        element.append(JMXComponentBuilder._int_prop("Assertion.test_type", test_type))
        return element

    @staticmethod
    def build_duration_assertion(duration_ms: str = "5000") -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "DurationAssertion",
            "DurationAssertionGui",
            "DurationAssertion",
            "Duration Assertion",
        )
        element.append(
            JMXComponentBuilder._string_prop(
                "DurationAssertion.duration", duration_ms
            )
        )
        return element

    @staticmethod
    def build_json_assertion(
        json_path: str,
        expected_value: str = "",
        is_regex: bool = False,
        expect_null: bool = False,
        invert: bool = False,
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "JSONPathAssertion",
            "JSONPathAssertionGui",
            "JSONPathAssertion",
            "JSON Assertion",
        )
        element.append(JMXComponentBuilder._string_prop("JSON_PATH", json_path))
        element.append(
            JMXComponentBuilder._string_prop("EXPECTED_VALUE", expected_value)
        )
        element.append(JMXComponentBuilder._bool_prop("JSONVALIDATION", True))
        element.append(JMXComponentBuilder._bool_prop("EXPECT_NULL", expect_null))
        element.append(JMXComponentBuilder._bool_prop("INVERT", invert))
        element.append(JMXComponentBuilder._bool_prop("ISREGEX", is_regex))
        return element

    @staticmethod
    def _build_jsr223(
        tag: str,
        name: str,
        script: str,
        language: str,
        cache_key: bool,
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            tag, "TestBeanGUI", tag, name
        )
        element.append(
            JMXComponentBuilder._string_prop("scriptLanguage", language)
        )
        element.append(JMXComponentBuilder._string_prop("parameters", ""))
        element.append(JMXComponentBuilder._string_prop("filename", ""))
        element.append(JMXComponentBuilder._bool_prop("cacheKey", cache_key))
        element.append(JMXComponentBuilder._string_prop("script", script))
        return element

    @staticmethod
    def build_jsr223_postprocessor(
        script: str,
        language: str = "groovy",
        cache_key: bool = True,
    ) -> ET.Element:
        return JMXComponentBuilder._build_jsr223(
            "JSR223PostProcessor",
            "JSR223 PostProcessor",
            script,
            language,
            cache_key,
        )

    @staticmethod
    def build_jsr223_preprocessor(
        script: str,
        language: str = "groovy",
        cache_key: bool = True,
    ) -> ET.Element:
        return JMXComponentBuilder._build_jsr223(
            "JSR223PreProcessor",
            "JSR223 PreProcessor",
            script,
            language,
            cache_key,
        )

    @staticmethod
    def build_result_collector(
        filename: str = "${__P(result_file,result.jtl)}",
        error_logging: bool = False,
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "ResultCollector",
            "ViewResultsFullVisualizer",
            "ResultCollector",
            "View Results Tree",
        )
        element.append(
            JMXComponentBuilder._bool_prop(
                "ResultCollector.error_logging", error_logging
            )
        )
        obj = ET.Element("objProp")
        name_element = ET.SubElement(obj, "name")
        name_element.text = "saveConfig"
        value = ET.SubElement(obj, "value", {"class": "SampleSaveConfiguration"})
        for tag, setting in (
            ("time", True),
            ("latency", True),
            ("timestamp", True),
            ("success", True),
            ("label", True),
            ("code", True),
            ("message", True),
            ("threadName", True),
            ("dataType", True),
            ("encoding", False),
            ("assertions", True),
            ("subresults", True),
            ("responseData", False),
            ("samplerData", False),
            ("xml", False),
            ("fieldNames", True),
            ("responseHeaders", False),
            ("requestHeaders", False),
            ("responseDataOnError", False),
            ("saveAssertionResultsFailureMessage", True),
            ("assertionsResultsToSave", "0"),
            ("bytes", True),
            ("sentBytes", True),
            ("url", True),
            ("threadCounts", True),
            ("idleTime", True),
            ("connectTime", True),
        ):
            child = ET.SubElement(value, tag)
            child.text = (
                str(setting).lower() if isinstance(setting, bool) else str(setting)
            )
        element.append(obj)
        element.append(JMXComponentBuilder._string_prop("filename", filename))
        return element

    @staticmethod
    def _build_explicit_result_listener(
        gui_class: str,
        name: str,
        filename: str,
        error_logging: bool,
        full_debug_data: bool,
        enabled: bool,
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "ResultCollector", gui_class, "ResultCollector", name
        )
        element.set("enabled", "true" if enabled else "false")
        element.append(
            JMXComponentBuilder._bool_prop(
                "ResultCollector.error_logging", error_logging
            )
        )
        obj = ET.Element("objProp")
        name_element = ET.SubElement(obj, "name")
        name_element.text = "saveConfig"
        value = ET.SubElement(obj, "value", {"class": "SampleSaveConfiguration"})
        settings = (
            ("time", True),
            ("latency", True),
            ("timestamp", True),
            ("success", True),
            ("label", True),
            ("code", True),
            ("message", True),
            ("threadName", True),
            ("dataType", True),
            ("encoding", full_debug_data),
            ("assertions", True),
            ("subresults", True),
            ("responseData", full_debug_data),
            ("samplerData", full_debug_data),
            ("xml", full_debug_data),
            ("fieldNames", True),
            ("responseHeaders", full_debug_data),
            ("requestHeaders", full_debug_data),
            ("responseDataOnError", full_debug_data),
            ("saveAssertionResultsFailureMessage", True),
            ("assertionsResultsToSave", "0"),
            ("bytes", True),
            ("sentBytes", True),
            ("url", True),
            ("threadCounts", True),
            ("idleTime", True),
            ("connectTime", True),
        )
        for tag, setting in settings:
            child = ET.SubElement(value, tag)
            child.text = (
                str(setting).lower() if isinstance(setting, bool) else str(setting)
            )
        element.append(obj)
        element.append(JMXComponentBuilder._string_prop("filename", filename))
        return element

    @staticmethod
    def build_view_results_tree(
        name: str = "View Results Tree (Debug)",
        filename: str = "${__P(debug_result_file,debug.jtl)}",
        error_logging: bool = False,
    ) -> ET.Element:
        return JMXComponentBuilder._build_explicit_result_listener(
            "ViewResultsFullVisualizer",
            name,
            filename,
            error_logging,
            full_debug_data=True,
            enabled=True,
        )

    @staticmethod
    def build_simple_data_writer(
        name: str = "Simple Data Writer (Load)",
        filename: str = "${__P(load_result_file,load.jtl)}",
        error_logging: bool = False,
    ) -> ET.Element:
        return JMXComponentBuilder._build_explicit_result_listener(
            "SimpleDataWriter",
            name,
            filename,
            error_logging,
            full_debug_data=False,
            enabled=False,
        )

    @staticmethod
    def build_backend_listener_influxdb(
        influxdb_url: str = "http://localhost:8086/api/v2/write",
        influxdb_token: str = "",
        application: str = "JMeter-Test",
        samplers_regex: str = ".*",
        percentiles: str = "50;90;95;99",
        summary_only: bool = False,
        queue_size: str = "5000",
    ) -> ET.Element:
        element = JMXComponentBuilder._named_element(
            "BackendListener",
            "BackendListenerGui",
            "BackendListener",
            "Backend Listener (InfluxDB)",
        )
        element.append(
            JMXComponentBuilder._string_prop(
                "classname",
                "org.apache.jmeter.visualizers.backend.influxdb."
                "InfluxdbBackendListenerClient",
            )
        )
        arguments = ET.Element(
            "elementProp",
            {
                "name": "Arguments",
                "elementType": "Arguments",
                "guiclass": "ArgumentsPanel",
                "testclass": "Arguments",
                "enabled": "true",
            },
        )
        collection = JMXComponentBuilder._collection_prop("Arguments.arguments")
        for key, value in (
            ("influxdbUrl", influxdb_url),
            ("influxdbToken", influxdb_token),
            ("application", application),
            ("measurement", "jmeter"),
            ("summaryOnly", str(summary_only).lower()),
            ("samplersRegex", samplers_regex),
            ("percentiles", percentiles),
            ("testTitle", "JMeter Load Test"),
        ):
            argument = JMXComponentBuilder._element_prop(key, "Argument")
            argument.append(JMXComponentBuilder._string_prop("Argument.name", key))
            argument.append(
                JMXComponentBuilder._string_prop("Argument.value", value)
            )
            collection.append(argument)
        arguments.append(collection)
        element.append(arguments)
        element.append(
            JMXComponentBuilder._string_prop("asyncQueueSize", queue_size)
        )
        return element
