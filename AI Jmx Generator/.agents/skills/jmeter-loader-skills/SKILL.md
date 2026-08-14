---
name: jmeter-loader-skills
description: Use when converting SAZ or Fiddler HTTP captures into parameterized JMeter test-plan previews, or generating tree-structured JMX files from explicitly approved previews.
---

# 生成 JMeter 测试计划

把 SAZ/Fiddler HTTP 会话转换为可审阅的文字版测试计划，并且只在用户明确批准后生成 JMX。

工作流分为两个阶段：

1. 生成并修订文字版测试计划。
2. 从已批准的计划生成 JMX。

完成阶段 1 后立即停止，只输出 `.md` 计划。此时严禁创建、修改或验证任何 `.jmx` 文件。只有用户在后续消息中明确说“确认通过，生成 JMX”或等价表达，才进入阶段 2。不得把用户提供初始需求、要求预览或沉默视为批准。

## 按需读取参考资料

| 当前任务 | 必须读取 |
|---|---|
| 从 SAZ/Fiddler 会话设计文字计划 | `references/saz-analysis.md` |
| 决定字段提取、随机化、CSV 或静态取值 | `references/parameterization-rules.md` |
| 把批准计划转换为嵌套场景 JSON | `references/scenario-schema.md` |
| 生成及验收 JMX | `references/validation-rules.md` |
| 查询特定 JMeter 组件 | `references/component_reference.md` 中对应章节 |
| 查询 JMeter 函数 | `references/functions_reference.md` 中对应函数 |
| 查询属性、XML 或 Sampler 配置 | 对应读取 `references/properties_reference.md`、`references/jmx_structure.md` 或 `references/sampler_types.md` |

不要为了普通 HTTP 场景加载全部通用参考文档。先搜索标题或组件名，再读取相关章节。

## 阶段 1：生成文字版测试计划

1. 读取 `references/saz-analysis.md` 和
   `references/parameterization-rules.md`。
2. 按两个参考文档规则生成 `.md` 文字计划。
3. 把计划发给用户，等待审批。
4. 用户提出修改时只修订文字计划，保持在阶段 1。


## 阶段 2：生成 JMX

进入本阶段前同时确认：

- 用户已在消息中明确批准生成 JMX。
- 最终版文字计划存在，并且所有待生成步骤均已确定。

然后：

1. 读取 `references/scenario-schema.md` 和 `references/validation-rules.md`。
2. 把批准计划逐层转换为嵌套场景 JSON；保持节点顺序和 `children` 层级。预计完整 Scenario 超过 30 KB 或超过 20 个 sampler 时，优先按 Transaction Controller 或清晰业务单元创建分片。
3. 仅在需要查看完整格式时读取 `assets/samples/nested-scenario.example.json`。它只展示结构，不是业务数据来源。
4. 每个分片写入后运行 `python3 -m json.tool <fragment>`。以下命令均从技能根目录 `AI Jmx Generator/.agents/skills/jmeter-loader-skills` 执行。使用分片时，先组装：

```bash
python3 scripts/assemble_scenario.py \
  --manifest scenario/main.manifest.json \
  --output test.scenario.json \
  --validate
```

组装后确认 JSON 中没有 `$include`，并与批准计划核对节点数和 sampler 数。一次完整 Scenario 大补丁失败后，立即切换为分片，不得原样重试同一个大补丁。

5. 调用树形生成入口：

```bash
python3 scripts/generate_jmx_tree.py \
  --scenario test.scenario.json \
  --output test.jmx \
  --validate
```

6. 按 `references/validation-rules.md` 验证结构、参数化、文件配套和批准计划一致性。

## 生成器边界

- 只调用 JSON 树形动态入口 `scripts/generate_jmx_tree.py`；
- 生成链目标版本为 JMeter 5.6.3；
- 动态 Sampler 支持 `http_sampler`、`jdbc_sampler` 和 `debug_sampler`；JDBC 场景必须同时配置 `jdbc_connection_config`。
- 固定变量既支持顶层 `test_plan.variables`，也支持可嵌套的原生 `user_defined_variables`。
- 运行期用户变量支持原生 `user_parameters`；批准计划要求 User Parameters 时不得改写成 JSR223。
- 新场景必须同时包含 `view_results_tree`（默认启用、完整调试数据）和 `simple_data_writer`（默认禁用、轻量负载数据）。生成后必须告知用户：正式负载测试前禁用前者并启用后者。
- 提取器支持 CSS Selector/HTML、XPath、JSON、Boundary 和正则。未注册类型不得伪造或用相近节点代替。

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
