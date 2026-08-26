# JMX 生成与验收规则

## 生成前检查

- 用户已在文字计划输出后的消息中明确批准生成 JMX。
- 最终版文字计划存在且没有待确认项。
- 场景 JSON 中所有请求均能追溯到捕获内容和批准计划。
- 需要的 CSV 文件及列名已经确定。
- 节点类型全部在 `scenario-schema.md` 的支持列表中。

## 生成命令

生成链目标版本为 JMeter 5.6.3。完整 Scenario 只使用树形入口：

```bash
python3 scripts/generate_jmx_tree.py \
  --scenario test.scenario.json \
  --output test.jmx \
  --validate
```

`scripts/generate_jmx_tree.py` 必须只依赖 `scripts/jmx_tree_components.py`。

## 结构检查

- 每个 JMeter 元件后都有配对 `hashTree`。
- 每个线程组有非空子树。
- 每个 Controller 有非空 `children`，层级与批准计划一致。
- 认证流程仅在批准计划要求时存在，并完整位于 Once Only Controller 子树。
- 普通业务事务不位于 Once Only Controller 内。
- Extractor、Header Manager、Timer 和 Pre/PostProcessor 位于其目标 Sampler 子树。
- 节点顺序与批准计划一致。

## HTTP 检查

- HTTP Request Defaults 的 host、port、protocol使用 `${__P(propname,default)}`,default 为.saz文件中获取的值；字面量和 `${variable}` 均不允许。
- 请求名称、method、path、headers、params 和 body 与批准计划一致。
- HTTP Request Sampler 使用 `follow_redirects=true`。
- POST 使用 Parameters 时，参数使用 `HTTPArgument.always_encode=true`。
- JSON body 使用 Body Data。
- Multipart 保留原始 boundary 和分段结构，同时完成字段关联。
- 有重定向链时，根据实际响应范围决定提取器是否处理 sub-samples；不要仅凭 Referer header 判断必然重定向。

## 参数化检查

- 压测参数使用 `${__P(property,default)}`。
- CSV Data Set 字段通过 `${column_name}` 引用，CSV 第一行为列名。
- 同一业务值在唯一性检查和提交请求中引用同一变量。
- 前置响应值优先于随机、CSV 和静态值。
- 随机业务字段在业务循环开始处生成一次，不在多个 Sampler 中分别生成。
- WebForms、弹窗回填、multipart 和 multisection 按 `parameterization-rules.md` 处理。

## 提取器检查

- CSS Extractor 的 `refname`、`expression`、`attribute` 和 `scope` 与实际 HTML 响应一致。
- XPath Extractor 的 `refname`、`xpath_query`、Tidy 和 namespace 设置与实际响应格式一致。
- 提取器位于产生该响应的 Sampler 子树；需要包含重定向 sub-samples 时使用 `scope=all`。

## JDBC 检查

- 每个 JDBC Request 引用已存在的 JDBC Connection Configuration `pool_name`。
- JDBC URL、driver、username 和 password 使用属性或变量，不在日志中输出密码。
- `query_type` 与 SQL 类型一致。
- Prepared/Callable 请求的 `query_arguments` 和 `query_argument_types` 数量一致。
- 所需 JDBC driver JAR 已放入 JMeter 运行环境；生成器本身不测试数据库连接。

## 结果与文件检查

- 默认同时存在 `view_results_tree` 和 `simple_data_writer`：前者启用并输出完整 XML 调试 JTL，后者禁用并输出轻量 CSV 负载 JTL。
- 正式负载测试前禁用 View Results Tree、启用 Simple Data Writer，避免响应正文和 GUI 渲染造成额外负载。
- 两个 Result Collector 均输出 `.jtl`，并使用不同文件名。
- CSV、场景 JSON 和 JMX 的相对路径在实际运行目录下可解析。
- 生成器 `--validate` 返回成功。
- 运行现有生成器测试，确认树形结构和错误处理没有回归。
- 本工作流不自动加入断言；建议断言只保留在审阅说明中。
- Jmx中不能出现任何中文

## Validator 终态协议

首轮审查一次性完成有限检查并收集全部发现。`Blockers: 0` 时立即返回 `PASS`，不得用进度消息代替终态：

```text
Verdict: PASS | FAIL
Blockers: <count>
Warnings: <count>
Checks completed: <finite checklist>
Findings:
- Severity: BLOCKER | WARNING
  File/location: ...
  Evidence: ...
  Impact: ...
  Required fix: ...
```

没有发现时写 `Findings: None`。修复后的复验只检查原 blockers，以及 JSON/XML 可解析、节点和 sampler 数量、负载模型、断言数量、listeners、multipart 变量化；完成后立即给出新终态。

Validator 保持只读，只在最终响应中返回结果，由调用方按需保存报告。JMeter 元数据版本与目标 5.6.3 不一致时最多记为 `WARNING`，不得单独构成 blocker。

## 禁止事项

- 不因示例存在而生成未捕获的登录端点。
- 不静默丢弃未知节点。
- 不为生成器已支持的结构创建一次性脚本。
- 不把 JMeter 本身支持的 Sampler 误报为树形生成器已支持。
