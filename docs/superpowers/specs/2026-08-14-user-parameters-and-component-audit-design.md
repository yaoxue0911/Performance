# User Parameters 与树形生成器组件审计设计

## 目标

为 `generate_jmx_tree.py` 注册原生 `user_parameters` 节点，禁止再用 JSR223 模拟已批准的 User Parameters。同时分别审计明确支持契约和全部参考资料，输出可追踪的生成器组件覆盖结果，并重新生成 PA40 Incident Report JMX。

## 范围

本次实现包含：

- 为树形生成器新增 `user_parameters` 节点及原生 `<UserParameters>` XML 构建逻辑。
- 更新场景 Schema、示例和支持节点计数。
- 增加注册表与明确支持文档的一致性测试。
- 生成两层组件审计结果：
  - 明确支持契约中声明但未注册的元件，属于必须修复的缺口。
  - `references/` 中提到但未注册的全部元件，属于参考能力清单，不自动承诺实现。
- 把 PA40 场景中的随机变量 JSR223 PreProcessor 替换为 Loop Controller 直属的原生 User Parameters，并重新生成、验证 JMX。

本次不批量实现参考资料中的 FTP、SMTP、LDAP、JMS 或其他未承诺节点；除 `user_parameters` 外，新发现的缺口先报告，不在同一变更中扩展实现。

## Scenario JSON 接口

节点格式：

```json
{
  "type": "user_parameters",
  "name": "Per-report dynamic data",
  "per_iteration": true,
  "parameters": [
    {
      "name": "iteration_failed",
      "values": ["false"]
    },
    {
      "name": "firstName",
      "values": ["TEST${__Random(1000,9999)}"]
    }
  ]
}
```

规则：

- `parameters` 必须是非空有序数组。
- 每项必须包含非空、唯一的 `name` 和非空字符串数组 `values`。
- 所有参数的 `values` 长度必须一致；每个数组下标代表 JMeter User Parameters 的一个用户值列。
- `per_iteration` 必须是布尔值，默认 `true`。
- `name` 为可选测试树名称，默认 `User Parameters`。
- 节点可以作为 Controller 的子节点。PA40 将它放在业务 Forever Loop 的首个子节点，以便一轮报告只生成一组随机业务值。

## JMX 映射

`JMXComponentBuilder.build_user_parameters()` 生成：

- 标签：`UserParameters`
- GUI：`UserParametersGui`
- testclass：`UserParameters`
- `UserParameters.names`：按 `parameters` 顺序保存变量名。
- `UserParameters.thread_values`：把各参数的 `values` 按用户值列转置为 JMeter 所需结构。
- `UserParameters.per_iteration`：映射 `per_iteration`。

集合子节点名称使用确定性值，保证相同 Scenario 每次生成相同 JMX。生成器不得把 `user_parameters` 改写成 JSR223 或其他近似节点。

## 组件审计

审计输出写入 `reports/jmeter_tree_generator_component_audit.md`，分为两部分。

### 明确支持契约

数据来源：

- `SKILL.md` 中对动态 Sampler、提取器和监听器的明确支持说明。
- `references/scenario-schema.md` 的“支持的节点”表。
- `generate_jmx_tree.py` 的 `COMPONENT_FACTORIES` 注册表。

审计结果列出文档声明集合、实际注册集合、声明但未注册、注册但未声明。测试至少保证 `scenario-schema.md` 的机器可识别节点集合与注册表完全一致。

### 全部参考资料

扫描 `references/*.md` 中以组件标题或明确组件名称介绍的 JMeter 元件，将其规范化分类为 Sampler、Controller、Listener、Config、Assertion、Timer、PreProcessor、PostProcessor、Thread Group 或 Miscellaneous。

每项标记：

- `REGISTERED`：树形生成器已注册。
- `REFERENCE_ONLY`：参考资料介绍，但支持契约没有承诺且生成器未注册。
- `CONTRACT_GAP`：支持契约明确承诺，但生成器未注册。
- `AMBIGUOUS`：名称不能可靠映射，需要人工确认。

内置函数、JMeter 属性和普通概念不作为组件缺口。审计报告记录来源文件和标题，避免只给名称而无法追踪。

## PA40 迁移

删除当前挂在 `GET /RMS/inbox/list` 下、名为 `Per-report dynamic data` 的 JSR223 PreProcessor。将原生 `user_parameters` 放到 `Create and submit Incident Report (Forever)` Loop Controller 的第一个子节点，保留批准计划中的变量名和 JMeter 函数表达式：

- `iteration_failed`
- `firstName`
- `lastName`
- `ssn`
- `plateNo`
- `narrative`
- `contact_name_mn_rnd`
- `contact_ssn_mn_rnd`
- `vehicle_mn_rnd`
- `victim_popup_rnd`
- `vehicle_popup_rnd`
- `njs_popup_rnd`

`per_iteration=true`，确保一次报告循环内唯一性查询、保存和提交使用同一组值，下一轮报告重新计算。

## 验证与错误处理

采用 TDD：

1. 先增加失败测试，覆盖注册缺失、原生 XML、变量顺序、多用户值列转置、`per_iteration`、空数组、重复名称和列数不一致。
2. 实现最小构建器与注册逻辑，使测试通过。
3. 增加支持契约同步测试和组件审计测试。
4. 重新生成 PA40 Scenario/JMX，确认原随机变量 JSR223 不再存在，原生 User Parameters 位于业务 Loop 首位。
5. 运行完整生成器测试、`--validate`、JSON/XML 解析和 PA40 固定回归检查：52 个 HTTP Sampler、5/5/600 负载、Forever Loop、断言、监听器、multipart 和关联失败控制均不回归。

输入不合法时生成器必须停止并给出包含 Scenario 节点位置的错误，不得静默丢弃、截断或补齐参数。

## 兼容性与非目标

- 目标 JMeter 版本保持 5.6.3。
- 不修改现有 HTTP Defaults 未提交改动，也不回退工作区其他用户修改。
- 不运行真实负载测试。
- 本机若仍无 JMeter CLI，则明确报告未完成原生 JMeter 装载验证。
- 不在本次变更中提交真实账号或替换 PA40 CSV 占位数据。
