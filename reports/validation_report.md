# PA40 Incident Report 最终 JMX 验证报告

## 结论

**PASS：新增修复与原全量静态回归全部通过，无剩余阻断项。**

验证对象：`Output/PA40_Incident_Report_5Users_3Loops.jmx`

限制：按任务要求未启动 JMeter、未联网、未发送 HTTP 请求、未运行真实压测。本次使用 Python `xml.etree.ElementTree`、生成器内置只读验证函数及静态扫描完成复验；未修改 JMX、生成器或 CSV。

## 新增修复检查

- **case_location_id / cfs_id / org_id：PASS**
  - 三个 Regex Extractor 均绑定到 `POST /RMS/Aspsoft/Dispatcher` 新建 Report 的重定向链。
  - 三者均为 Body 提取、`Sample.scope=all`、`Match No.=1`、Default=`NOT_FOUND`。
  - Regex 分别按 `master_id_list` 中的 LOCATION、CASE/cfs、CASE/org 结构定位，随后与 `FormGUID,middle_csrf` 一起进入关联失败检查。
  - 生成器针对 SAZ 的提取器回归输出：`Extractor regression PASS: regex=14, css=15, json=5`。
- **登录失败 Stop Thread：PASS**
  - GET Login 与 POST Login 后各有 1 个 `Stop Current Thread - Login Correlation Failed`，共 2 个。
  - 两者均为 `ActionProcessor.action=1`、`target=0`；按本地 JMeter skill 结构参考，对应 Stop / Current Thread，而非 Pause 或停止整个测试。
- **断言失败门控：PASS**
  - `Gate Failed CreateIntake Assertion` 紧邻带 2 个 JSONPath Assertion 的 CreateIntake Sampler，检查 `JMeterThread.last_sample_ok` 与 `iteration_failed`。
  - `Gate Failed Auto Confirm Assertion` 紧邻带 2 个 Response Assertion 的 Auto Confirm Sampler，检查 `JMeterThread.last_sample_ok`。
  - 两个门控的动作均为 `action=5,target=0`，失败时跳到当前 Report Loop 的下一次迭代，阻止后续有状态请求继续执行。
- **生成器验证：PASS**
  - 仅导入 `Output/generate_pa40_incident_report_jmx.py`，未执行会写文件的 `main()`。
  - 对当前 JMX 调用 `validate_arguments_and_http_defaults`、`validate_control_flow_and_assertions`、`validate_extractors_against_saz`，三者均通过。
  - 控制流输出：`login_stop=2 action=1; assertion_gates=2 immediate; assertions=4`。

## 原全量回归

- XML：Python 标准库解析成功，根元素为 `jmeterTestPlan`。
- 历史修复：`home_csrf` 全文零匹配；所有 URL/Referer 均无重复 `rnd` 查询键。
- 负载：`${__P(concurrency,5)}`、`${__P(rampup,5)}`、`${__P(report_loops,3)}`；线程组循环 1 次，理论 15 份 Report。
- 登录：恰好 1 个 `OnceOnlyController: Login Once Per User`，位于业务 Loop 外。
- CSV：变量 `username,password,staff_id,region_id`；表头加 5 行用户；忽略首行、EOF 不回收、EOF 停线程、All Threads。占位数据须在实际执行前替换。
- HTTP：53 个 HTTP Sampler 均 Follow Redirects=true；Parameters POST 均 `always_encode=true`，JSON Body Data 与 multipart raw body 保持例外。
- 变量：未发现请求引用但无来源的普通变量，未发现有副作用的未使用提取变量。`JMeterThread.last_sample_ok` 是 JMeter 内建运行时变量，不视为未定义。
- 命名：Victim、Vehicle、Charge 前缀一致且未混用；`inv_njs_id_1/2` 来源为 `Match No.=-1` 多值提取。
- 硬编码：未发现固定 CSRF token、MappingKey、FormGUID、既有 Case/Report/Person/Vehicle/Charge ID；新建场景 `report_id=0` 合理。
- 重定向范围：`disclaimer_csrf`、`FormGUID`、`middle_csrf` 及新增三项 Case 上下文 ID 均正确覆盖重定向子样本。
- JSR223：2 个 PreProcessor、21 个 PostProcessor，均为 Groovy且 `cacheKey` 非空；动态初始化、Charge decode、STX/ETX payload 构造具备必要性。
- Timer：7 个 Uniform Random Timer，全部直接挂在目标 HTTP Sampler 下。
- Collector：1 个 Simple Data Writer，输出 `${__P(result_file,PA40_Incident_Report.jtl)}`，必需 JTL 字段齐全。
- 断言：恰好两组、共 4 个获批 Assertion，无其他断言：CreateIntake 的 2 个 JSONPath Assertion；Auto Confirm 的 2 个 Response Assertion。

## JMeter 函数与内建变量

- `__P`：`concurrency`、`rampup`、`report_loops`、`protocol`、`target_host`、`target_port`、`think_time_min_ms`、`think_time_range_ms`、`result_file`。
- `__Random`：`${__Random(100000,999999)}`。
- `__groovy`：STX 字符生成、关联失败判断、断言失败门控。
- 内建变量：`JMeterThread.last_sample_ok`、`__jm__Create Incident Report__idx`。

以上函数和内建变量均不作为未定义变量。
