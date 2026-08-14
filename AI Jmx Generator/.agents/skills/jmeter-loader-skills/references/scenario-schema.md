# 嵌套场景 JSON 规则

## 目录

- [数据来源](#数据来源)
- [顶层结构](#顶层结构)
- [大型场景分片](#大型场景分片)
- [树形映射](#树形映射)
- [支持的节点](#支持的节点)
- [生成器范围](#生成器范围)
- [示例](#示例)

## 数据来源

场景 JSON 是最终批准文字计划的结构化表达。所有请求 `name`、`method`、`path`、host、headers、params、body 和业务顺序必须来自 SAZ/Fiddler 捕获及批准计划。

示例文件中的主机、路径、控制器名称和参数只是演示值。除非源数据包含完全相同的值，否则不得复制到实际场景。

## 顶层结构

场景必须包含：

- `test_plan`：对象，可包含名称和用户变量。
- `thread_groups`：非空数组。
- 每个 `thread_groups[]`：必须包含非空 `children`。

线程组使用：

- `threads`: `${__P(concurrency,10)}`
- `rampup`: `${__P(rampup,10)}`
- `duration`: `${__P(duration,60)}`
- `on_sample_error`: `continue`

## 大型场景分片

预计完整 Scenario 超过 30 KB 或超过 20 个 sampler 时，优先按 Transaction Controller 或清晰业务单元拆分 JSON。Manifest 和每个 fragment 必须分别是合法 JSON；写完每个分片立即运行：

```bash
python3 -m json.tool scenario/fragments/30-add-victim.json
```

使用只含 `$include` 的对象引用分片：

```json
{
  "test_plan": {"name": "Incident Report"},
  "thread_groups": [{
    "name": "Users",
    "children": [
      {"$include": "fragments/10-auth.json"},
      {"$include": "fragments/30-add-victim.json"}
    ]
  }]
}
```

include 路径相对包含它的 JSON 文件解析。对象 fragment 替换 include 节点；数组 fragment 位于数组中时按原顺序展开。fragment 可继续 include。绝对路径、越出 manifest 根目录的路径、缺失文件、循环引用以及混有其他字段的 include 对象均使组装失败。

运行：

```bash
python3 scripts/assemble_scenario.py \
  --manifest scenario/main.manifest.json \
  --output test.scenario.json \
  --validate
```

只有在组装结果可解析、不含 `$include`，且节点数和 sampler 数与批准计划一致后，才交给 `generate_jmx_tree.py`。一次完整 Scenario 大补丁失败后立即切换分片，不得原样重试。


## 树形映射

- 文字计划的每一层映射为同一层 JSON `children`，并保持顺序。
- `once_only_controller`、`transaction_controller`、`if_controller`、`loop_controller`、`foreach_controller` 必须包含非空 `children`。
- 如果批准计划存在每线程认证或初始化流程，把完整流程放入 `once_only_controller.children`；普通业务事务位于其外部。
- HTTP/JDBC Sampler 的 Extractor、Assertion、Header Manager、Timer 和 Pre/PostProcessor 放在该 Sampler 的 `children` 中；仅使用对该 Sampler 有意义的子元件。
- 未知 `type`、空 Controller 或错误参数必须使生成停止，不得忽略节点继续生成。

## 支持的节点

当前 `generate_jmx_tree.py` 注册以下 34 种节点：

| 类别 | 节点类型 |
|---|---|
| Samplers | `http_sampler`, `jdbc_sampler`, `debug_sampler` |
| Controllers | `if_controller`, `transaction_controller`, `once_only_controller`, `loop_controller`, `foreach_controller` |
| Timers | `constant_timer`, `gaussian_timer`, `uniform_timer`, `synchronizing_timer` |
| Extractors | `json_extractor`, `boundary_extractor`, `regex_extractor`, `css_extractor`, `xpath_extractor` |
| Assertions | `response_assertion`, `duration_assertion`, `json_assertion` |
| Config | `http_defaults`, `header_manager`, `cookie_manager`, `cache_manager`, `csv_data_set`, `jdbc_connection_config`, `user_defined_variables` |
| PreProcessors | `user_parameters`, `jsr223_preprocessor` |
| PostProcessors | `jsr223_postprocessor` |
| Listeners | `view_results_tree`, `simple_data_writer`, `result_collector`, `backend_listener_influxdb` |

字段名必须匹配 `scripts/jmx_tree_components.py` 中对应 `JMXComponentBuilder.build_*` 方法的参数。需要不常用节点时先检查该方法签名，不要猜测字段。

### User Defined Variables

测试计划全局变量可继续放在顶层 `test_plan.variables`。需要 Thread Group 或 Controller 作用域时，使用可嵌套的原生 `user_defined_variables`：

```json
{
  "type": "user_defined_variables",
  "name": "Thread-scoped constants",
  "variables": {
    "division_id": "3",
    "master_location_id": "19198"
  }
}
```

`variables` 必须是非空对象，变量名必须是非空字符串，变量值必须是字符串。节点可放在任意 `children` 数组中，其变量作用域遵循 JMeter 树层级规则。

### User Parameters

运行期随机变量应使用原生 `user_parameters`，不得用 JSR223 模拟已批准的 User Parameters：

```json
{
  "type": "user_parameters",
  "name": "Per-report dynamic data",
  "per_iteration": true,
  "parameters": [
    {"name": "firstName", "values": ["TEST${__Random(1000,9999)}"]},
    {"name": "lastName", "values": ["TEST${__Random(1000,9999)}"]}
  ]
}
```

`parameters` 必须是非空有序数组，名称非空且唯一。每项的 `values` 必须是非空字符串数组，且所有数组长度相同；每个数组下标表示一个用户值列。`per_iteration=true` 表示每次经过父控制器只更新一次，适合让同一业务循环中的所有请求共享同一组随机值。

### HTTP Request Defaults

HTTP Request Defaults 的运行参数必须保留命令行覆盖能力。`host`、`port`、`protocol`必须使用 `${__P(propname,default)}`，不得传入字面量或普通 JMeter 变量：

```json
{"type":"http_defaults","host":"${__P(target_host,example.invalid)}","port":"${__P(target_port,443)}","protocol":"${__P(protocol,https)}"}
```

省略这些字段时，生成器仍会写入对应的 `__P` 默认表达式；不会写入固定值。

### CSS/XPath 提取器

```json
{"type":"css_extractor","refname":"csrf","expression":"input[name='__RequestVerificationToken']","attribute":"value","match_number":"1","default_value":"NOT_FOUND","scope":"parent"}
```

```json
{"type":"xpath_extractor","refname":"viewstate","xpath_query":"//*[@name='__VIEWSTATE']/@value","match_number":"1","default_value":"NOT_FOUND","scope":"parent","use_tidy":true}
```

两者必须作为目标 Sampler 的 `children`。`scope` 根据实际响应范围使用 `parent` 或 `all`。

### JDBC

连接配置和请求是两个独立节点。连接配置通常放在线程组下，请求通过相同 `pool_name` 引用：

```json
{"type":"jdbc_connection_config","name":"Application Database","pool_name":"app_db","database_url":"jdbc:h2:mem:test","driver_class":"org.h2.Driver","username":"${db_username}","password":"${db_password}"}
```

```json
{"type":"jdbc_sampler","name":"Select Person","pool_name":"app_db","query_type":"Prepared Select Statement","query":"SELECT person_id FROM person WHERE last_name = ?","query_arguments":"${lastName}","query_argument_types":"VARCHAR","variable_names":"person_id","result_variable":"person_rows"}
```

`query_type` 只允许：`Select Statement`、`Update Statement`、`Callable Statement`、`Prepared Select Statement`、`Prepared Update Statement`、`Commit`、`Rollback`、`AutoCommit(false)`、`AutoCommit(true)`。同时填写 JDBC 参数和值类型时，逗号分隔项数量必须相同。

### 结果监听器

新场景默认同时包含：

```json
{"type":"view_results_tree","filename":"${__P(debug_result_file,debug.jtl)}"}
```

```json
{"type":"simple_data_writer","filename":"${__P(load_result_file,load.jtl)}"}
```

`view_results_tree` 默认启用，使用 XML JTL 保存请求、响应、请求头和响应头等调试数据。`simple_data_writer` 默认禁用，使用轻量 CSV JTL。正式负载测试前切换启用状态。`result_collector` 仅为既有场景保留，新场景不再使用这个含义模糊的类型。

## 生成器范围

- 当前动态树形 Sampler 支持 HTTP、JDBC 和 Debug；JDBC 必须配套 `jdbc_connection_config`，数据库驱动由 JMeter 运行环境提供。
- 当前提取器支持 JSON、Boundary、Regular Expression、CSS Selector/HTML 和 XPath。
- TCP、Java、FTP、SMTP、LDAP、JMS、OS Process、JSR223 Sampler 和 Bolt 是 JMeter 本身支持的类型，但尚未注册为树形生成节点。
- 树形生成器不会在生成阶段连接数据库，也不会验证 JDBC URL、账号或驱动是否真实可用。
- 遇到未支持的 Sampler 时停止并向用户说明，不得使用相近节点代替。

## JMeter 内置函数速查

| 函数 | 语法 | 用途 |
|---|---|---|
| `__P` | `${__P(prop,default)}` | 读取属性，支持命令行 `-Jprop=value` 覆盖 |
| `__property` | `${__property(prop,var,default)}` | 读取属性并可保存到变量 |
| `__setProperty` | `${__setProperty(prop,value,)}` | 设置 JMeter 属性，供线程间共享 |
| `__time` | `${__time(format,)}` | 获取当前时间 |
| `__timeShift` | `${__timeShift(format,date,shift,,)}` | 时间偏移 |
| `__Random` | `${__Random(min,max,)}` | 生成随机整数 |
| `__RandomString` | `${__RandomString(len,chars,)}` | 生成随机字符串 |
| `__UUID` | `${__UUID()}` | 生成 UUID |
| `__counter` | `${__counter(TRUE,)}` | 递增计数器 |
| `__V` | `${__V(Var${N},)}` | 嵌套变量引用 |
| `__groovy` | `${__groovy(expr,)}` | 执行 Groovy 表达式 |
| `__jexl3` | `${__jexl3(expr,)}` | 执行 JEXL3 表达式，适用于 If Controller |
| `__digest` | `${__digest(algo,str,,,)}` | 计算哈希摘要 |
| `__split` | `${__split(str,var,delim)}` | 拆分字符串 |
| `__eval` | `${__eval(${var})}` | 对变量内容再次求值 |
| `__log` | `${__log(msg,level,,)}` | 写入 JMeter 日志 |
| `__threadNum` | `${__threadNum}` | 当前线程号 |
| `__machineIP` | `${__machineIP}` | 本机 IP |

完整参数说明和全部内置函数见 `references/functions_reference.md`。JSR223 元件优先使用 Groovy，并启用编译缓存；脚本内使用 `vars.get("varName")`，不要使用 `${varName}` 插值。

## 示例

需要完整、可解析的结构示例时读取 `../assets/samples/nested-scenario.example.json`。该文件只展示嵌套和字段格式，不能作为实际业务路径来源。
