# PA40 Incident Report fix round 1 静态复验报告

## 结论

**PASS**

阻塞项：**无**。

本轮仅做静态解析与生成器单元测试；未运行 JMX、未访问目标环境、未修改计划/Scenario/JMX。

## 此前遗漏与修复证据

此前验证没有把 `${...}` 的所有消费点与 JSR223 动态生产点做完整闭包对照，因此没有独立证明 PA charge 解码输出和保存请求消费变量完全同名。本轮已补充全局闭包扫描，并将以下来源纳入：Test Plan UDV、CSV 列、Extractor `refname`、JSR223 `vars.put`/`vars.putObject`、批量 `vars.put(it, ...)`、带输出变量名的 `__Random`；JMeter 函数、属性表达式和已知内建状态不作为普通业务变量误报。

扫描结果：

- Scenario 普通 `${variable}` 引用集与生成 JMX 引用集完全相同。
- 无来源业务变量：0。
- JSR223 `vars.get(...)` 无来源变量：0。
- 命名 `__Random` 的 `request_rnd`、`request_rnd_1`、`request_rnd_2` 是函数副作用输出；当前没有通过 `${request_rnd*}` 消费，但函数即时返回值已用于请求字符串，因此不属于“无来源业务变量”。

## PA charge 命名闭包

- `Decode charge_1_candidate` 生产 `charge_1_code`、`charge_1_description`。
- `Decode charge_2_candidate` 生产 `charge_2_code`、`charge_2_description`。
- NJS 保存 sampler 的两个 code 字段和两个 description 字段分别消费完全同名的 `${charge_1_code}`、`${charge_1_description}`、`${charge_2_code}`、`${charge_2_description}`。
- 后续两个 NJS XPath extractor 与 correlation guard 也使用 `charge_1_*`、`charge_2_*`。
- Scenario/JMX 全文均未发现旧消费者 `charge1_*` 或 `charge2_*`。

## 生成器元数据与测试

- 生成 JMX 根节点为 `<jmeterTestPlan version="1.2" properties="5.0" jmeter="5.6.3">`。
- 通用生成器 `build_jmx` 明确写入 `jmeter="5.6.3"`。
- 通用测试套件新增 `test_root_metadata_targets_supported_jmeter_version`，断言根元数据为 5.6.3。
- 完整通用生成器测试：13 项运行，13 项通过，0 failure，0 error。
- 工作区另有一个旧 PA40 专项脚本硬编码读取已不存在的 `AI Jmx Generator/Output/PA40_Incident_Report.jmx`，因此该旧夹具运行 0 项并报 FileNotFoundError；它不指向本轮 `Output/PA40_Incident_Report_5Users_600Seconds.jmx`，不构成本轮制品或通用生成器回归结果。

## 既有关键项回归

- Scenario：173 个节点、52 个 HTTP sampler。
- JMX：52 个 `HTTPSamplerProxy`，XML 可解析。
- Accept：52/52 sampler 均存在，无缺失。
- Correlation guards：7 个，均包含 `iteration_failed=true` 和 `prev.setSuccessful(false)`；workflow guard 位于 token 提取后、三个状态 POST 前。
- 断言：仍为批准的三组，共 4 个 assertion 元件，无新增断言。
- GIS：两个 sampler 继续使用 `${master_location_id}`。
- Referer rnd：Victim/Vehicle/NJS/Intake/Workflow 的专用变量复用无回归；Workflow GET 的 Intake Referer 使用 `${intake_page_rnd}`。
- Multipart：Workflow Clear 的 Scenario/JMX body 保留 9 个 CRLF，且继续使用 `${report_id}`、`${workflow_csrf}`。
- 未发现捕获的 case ID、FormGUID、report ID、MappingKey、CSRF token 或业务对象 ID 被硬编码。

## CSV 外部执行风险（不影响本次静态 PASS）

`Output/pa40_incident_users.csv` 的 5 行仍为 `REPLACE_*` 占位值。在替换为 5 套独立且有权限的测试数据前不可真实执行。

## 静态验证边界

本报告未运行 JMX，也未验证目标环境登录、权限或业务响应。正式负载前必须替换 CSV，占位数据清理后禁用 View Results Tree并启用 Simple Data Writer。
