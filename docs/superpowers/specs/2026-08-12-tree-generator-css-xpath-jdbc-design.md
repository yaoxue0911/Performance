# Tree Generator CSS, XPath, and JDBC Design

## Goal

Extend the JSON-only tree JMX generator with executable support for CSS Selector/HTML extraction, XPath extraction, JDBC testing, and explicit debug/load JTL listeners while keeping `generate_jmx.py` deprecated and unused.

## New tree nodes

### `css_extractor`

Required fields: `refname`, `expression`.

Optional fields and defaults: `name="CSS Selector Extractor"`, `attribute="text"`, `match_number="1"`, `default_value="NOT_FOUND"`, `default_empty_value=false`, `scope="parent"`, and `implementation=""` (JMeter default).

The node generates JMeter `HtmlExtractor` XML and is placed in the paired `hashTree` of its target sampler.

### `xpath_extractor`

Required fields: `refname`, `xpath_query`.

Optional fields and defaults: `name="XPath Extractor"`, `match_number="1"`, `default_value="NOT_FOUND"`, `scope="parent"`, `use_tidy=true`, `quiet=true`, `report_errors=false`, `show_warnings=false`, `use_namespaces=false`, `validate_xml=false`, `ignore_whitespace=true`, `fetch_external_dtds=false`, and `return_fragment=false`.

The node generates JMeter `XPathExtractor` XML and is placed in the paired `hashTree` of its target sampler.

### `jdbc_connection_config`

Required fields: `pool_name`, `database_url`, `driver_class`.

Optional fields and defaults: `name="JDBC Connection Configuration"`, `username=""`, `password=""`, `max_connections="10"`, `connection_timeout_ms="10000"`, `validation_query="SELECT 1"`, `connection_properties=""`, `connection_age_ms="5000"`, `keep_alive=true`, `auto_commit=true`, and `transaction_isolation="DEFAULT"`.

The node generates JMeter `JDBCDataSource` XML. It is normally a direct child of a thread group so descendant JDBC samplers can reference its `pool_name`. Database connectivity and driver availability are runtime concerns and are not tested during JMX generation.

### `jdbc_sampler`

Required fields: `name`, `pool_name`, `query_type`, `query`.

Optional fields and defaults: `query_arguments=""`, `query_argument_types=""`, `variable_names=""`, `result_variable=""`, `query_timeout=""`, and `result_set_handler="Store as String"`.

The node generates JMeter `JDBCSampler` XML. Supported `query_type` values are exactly `Select Statement`, `Update Statement`, `Callable Statement`, `Prepared Select Statement`, `Prepared Update Statement`, `Commit`, `Rollback`, `AutoCommit(false)`, and `AutoCommit(true)`. Unsupported values fail generation with a location-aware error.

When query arguments and argument types are both supplied as comma-separated lists, their item counts must match.

### `view_results_tree`

Optional fields and defaults: `name="View Results Tree (Debug)"`, `filename="${__P(debug_result_file,debug.jtl)}"`, `error_logging=false`, and `enabled=true`.

The listener uses `ViewResultsFullVisualizer` and XML JTL output. It saves response data, sampler/request data, request headers, response headers, subresults, assertions, and error response data for debugging.

### `simple_data_writer`

Optional fields and defaults: `name="Simple Data Writer (Load)"`, `filename="${__P(load_result_file,load.jtl)}"`, `error_logging=false`, and `enabled=false`.

The listener uses `SimpleDataWriter` and CSV JTL output. It keeps the existing lightweight performance fields and does not save bodies or headers.

Every generated load-test scenario contains both listeners unless the approved text plan explicitly says otherwise. The debug listener is enabled and the load listener is disabled by default; the user switches them before a real load run.

## Architecture

All six factories live in `scripts/jmx_tree_components.py`. `scripts/generate_jmx_tree.py` registers their JSON node names in `COMPONENT_FACTORIES`; it remains a JSON-only dynamic assembler and does not import `generate_jmx.py` or support templates.

The recursive renderer remains unchanged: each new node is followed by its paired `hashTree`. Extractors are sampler children; JDBC connection configuration and JDBC requests remain separate nodes so connection pools can be shared by multiple requests.

## Documentation

Update all of the following:

- `SKILL.md`: state that JDBC is supported and must include a matching connection configuration, and require the two explicit result listeners with their default enabled states.
- `references/scenario-schema.md`: add the four nodes, their fields and examples; update `## 生成器范围` so JDBC is no longer listed as unsupported.
- `references/validation-rules.md`: add extractor and JDBC validation checks.

The supported-node count changes from 26 to 32. The existing `result_collector` node remains supported for existing scenario JSON, but new scenarios use the two explicit listener types.

## Error handling

Generation stops for missing required fields, unsupported JDBC query types, mismatched JDBC argument/type counts, and malformed node values. Errors include the scenario node location.

The generator does not test database connectivity; JMeter performs that at runtime. Credentials may use JMeter variables or properties and must not be printed by the generator.

## Tests

Add behavior tests that verify:

- CSS fields and scope produce the expected `HtmlExtractor` XML.
- XPath parser flags and scope produce the expected `XPathExtractor` XML.
- JDBC connection fields produce the expected `JDBCDataSource` XML.
- JDBC request fields produce the expected `JDBCSampler` XML.
- View Results Tree writes full XML debug data and is enabled by default.
- Simple Data Writer writes lightweight CSV load data and is disabled by default.
- Missing required fields, invalid query types, and argument/type count mismatch fail with the JSON location.
- All existing nesting, no-template, and no-legacy-generator tests continue to pass.
