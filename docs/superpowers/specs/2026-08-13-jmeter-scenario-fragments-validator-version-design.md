# JMeter Scenario 分片、Validator 终态与 5.6.3 统一设计

## 目标

优化 `jmeter-loader-skills` 的大型 Scenario 生成过程，避免在一次模型工具调用中写入包含大量转义内容的完整 JSON；让 `jmx_validator` 在有限检查后输出明确终态；并将活动生成链统一到 JMeter 5.6.3。

本次不增加变量生产者—消费者闭包检查。

## 方案选择

采用“分片生成 + 独立自动组装器”，不重构 `generate_jmx_tree.py` 的输入协议。现有单文件命令保持兼容：

```bash
python3 scripts/generate_jmx_tree.py --scenario test.scenario.json --output test.jmx --validate
```

大型场景先运行：

```bash
python3 scripts/assemble_scenario.py \
  --manifest scenario/main.manifest.json \
  --output Output/test.scenario.json \
  --validate
```

然后把组装出的完整 Scenario 交给现有生成器。

## 分片格式

Manifest 和每个 fragment 都必须是合法 JSON。树中使用以下 include 节点：

```json
{"$include": "fragments/30-add-victim.json"}
```

规则：

- include 路径相对包含它的 JSON 文件解析；
- fragment 为对象时替换为一个对象；
- fragment 为数组且 include 位于数组中时，按原顺序展开数组元素；
- fragment 内允许继续 include；
- 拒绝绝对路径、越出 manifest 根目录的路径、缺失文件和循环引用；
- include 对象不得混有其他字段；
- 最终输出中不得残留 `$include`；
- `--validate` 同时验证最终顶层包含非空 `thread_groups`，每个线程组包含非空 `children`。

建议文件组织：

```text
scenario/
├── main.manifest.json
└── fragments/
    ├── 00-config.json
    ├── 10-auth.json
    ├── 20-open-case.json
    ├── 30-add-victim.json
    ├── 40-add-vehicle.json
    ├── 50-add-charges.json
    ├── 60-create-report.json
    ├── 70-workflow.json
    └── 90-listeners.json
```

当预计完整 Scenario 超过 30 KB 或包含 20 个以上 sampler 时，技能要求优先采用分片。每个 fragment 按 Transaction Controller 或清晰业务单元划分，写入后先单独运行 `python3 -m json.tool`。不得在一次大补丁失败后原样重试；立即切换分片。

## Validator 终态契约

`jmx_validator` 的每次正式审查必须以以下固定结构结束：

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

首轮审查一次性收集全部发现。`Blockers: 0` 时必须立即返回 `PASS`。修复后的复验只检查原 blockers 和固定回归项：JSON/XML 可解析、节点与 sampler 数量、负载模型、断言数量、listeners、multipart 变量化，不重新开启无边界的全面探索。进度消息不能替代最终终态。

Validator 保持只读，只在最终响应返回终态，由调用方按需保存报告。JMeter 元数据不是 5.6.3 时最多记录为 warning，不得单独构成 blocker。

## JMeter 版本

- 生成器根元数据固定为 `jmeter="5.6.3"`；
- 活动参考文档和示例统一为 5.6.3；
- 扫描活动技能目录，不能残留 5.4.1。

## 测试

自动组装器至少覆盖：

- 对象 include；
- 数组 include 的顺序展开；
- 嵌套 include；
- 缺失文件；
- 循环引用；
- 越界路径；
- include 混合额外字段；
- 最终 Scenario 结构校验；
- 组装结果可被 `generate_jmx_tree.py --validate` 生成 JMX。

现有生成器测试继续全部通过；不新增版本元数据专用断言，也不把版本元数据差异定义为 validator blocker。

## 修改范围

- 修改 `jmeter-loader-skills/SKILL.md`；
- 修改 `references/scenario-schema.md`、`references/validation-rules.md`、`references/jmx_structure.md`；
- 新增 `scripts/assemble_scenario.py` 及其测试；
- 修改 `jmx_validator.toml` 的终态输出协议；
- 保留 `generate_jmx_tree.py --scenario` 的现有行为。
