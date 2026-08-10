# RI Add Person / Property JMX 最终验证报告

## 结论

**PASS：当前 JMX 与 SAZ、已批准架构及用户设置一致，未发现剩余阻断项。**

验证对象：`Output/RI_Add_Person_Property_Deadlock.jmx`

依据：`RI_add person and property.saz`、`Output/RI_Add_Person_Property_Deadlock_Test_Plan.md`、`jmeter-loader-skills`。

验证基线：

- JMX SHA-256：`1f7ff79b0c0445f6660f5379572be6db148b9d0d90271f2c151b4dee70e95b8e`
- 架构 SHA-256：`e8cbfa938d49080e0d0df4a5493774394857aa55554f66a0809f062c57012a30`
- SAZ SHA-256：`105181f1df33b89d76c611af88336376ffbcf0b9a648e2fe2c01ec4edf670f9c`

限制：本次只读解析 XML、读取 SAZ 原始会话并静态比较；未修改 JMX 或生成器，未启动 JMeter，未发送 HTTP 请求。

## 最新修复回归

- 当前 12:23 重生成 JMX 与上一轮已验证成品字节完全一致，SHA-256 仍为 `1f7ff79b0c0445f6660f5379572be6db148b9d0d90271f2c151b4dee70e95b8e`。
- 5 个此前残留抓包 rnd 的 Referer 已全部修复。
- Driver License State Dropdown、Place of Birth State Dropdown、City List、IDReaderHandler 均使用 `rnd=${person_request_rnd}`。
- Property Subtype Dropdown 使用 `rnd=${property_request_rnd}`。
- JMX 全文未发现 `rnd=<抓包小数>` 残留。
- “No Existing Person - Property Save Skipped” Debug Sampler 的 `displayJMeterVariables=false`，不会把当前线程变量写入调试响应。
- MasterName Set Session 与 Remove Session 的 Referer 均复用 `rnd=${person_request_rnd}`，与当前 Person Form 一致；`mn_rnd` 只用于 MasterName 会话本身的请求参数。
- Simple Data Writer 默认文件已改为 `${__P(result_file,RI_Add_Person_Property_Deadlock_${__time(yyyyMMdd_HHmmss,)}.jtl)}`，未显式传入 `result_file` 时按运行时间生成独立 JTL 文件名。
- 对所有元素按两条独立路径复扫：`element.tag.startswith("JSR223")` 命中 0 个；`(element.get("testclass") or "").startswith("JSR223")` 命中 0 个。
- 两条扫描覆盖 `JSR223Sampler`、`JSR223PreProcessor`、`JSR223PostProcessor`、`JSR223Timer`、`JSR223Listener`，也覆盖普通 tag 搭配 JSR223 testclass 的伪装情况。
- 未发现名称以 `Assertion` 结尾的组件，也未发现 `CSVDataSet`、`CriticalSectionController`、`SyncTimer` 或 `Synchronizer`。

## XML、线程组与控制结构

- XML：Python `xml.etree.ElementTree` 解析成功；根元素为 `jmeterTestPlan`。
- HTTP Sampler：32 个，其中 GET 17 个、POST 15 个。
- Thread Group：恰好 2 个，`Add Person Process` 与 `Add Property Process`。
- Test Plan `serialize_threadgroups=false`，两个线程组并行运行。
- 两组默认线程数分别为 `${__P(person_threads,1)}`、`${__P(property_threads,1)}`。
- 两组均 `scheduler=true`、duration=`${__P(duration,60)}`、ramp-up=`${__P(rampup,0)}`、delay=0、On error=Continue。
- Person/Property 业务 Loop 默认分别为 `${__P(person_loops,10)}`、`${__P(property_loops,10)}`。
- 两个 Once Only Controller 分别包含独立登录和打开 Case 流程。
- 两个 Constant Timer 均直接绑定各自每轮首个 Form GET，delay=`${__P(iteration_delay_ms,0)}`。
- 两个 If Controller 使用互斥 `__jexl3` 条件；有候选时保存 Property，无候选时执行 Debug Sampler并跳过保存。

## 会话隔离与禁止组件

- 恰好 2 个 Cookie Manager：`Person Session` 直属 Person Thread Group，`Property Session` 直属 Property Thread Group。
- 两个 Cookie Manager 均 `clearEachIteration=false`、`controlledByThreadGroup=true`，会话彼此隔离。
- 未发现 CSV Data Set Config 或 `__CSVRead`。
- 未发现任何 Assertion 元件。ResultCollector 中 assertion 相关字段只是 JTL 保存配置，不是 Assertion 组件。
- 未发现任何 `JSR223*` 组件；检查覆盖 Sampler、Pre/PostProcessor、Timer、Listener 及其他可能的 JSR223 tag/testclass。
- 未发现 Critical Section Controller。
- 未发现 Synchronizing Timer / SyncTimer。

## HTTP 属性与 SAZ 一致性

- 32/32 HTTP Sampler 均 `HTTPSampler.follow_redirects=true`。
- 15 个 POST 共 263 个 HTTPArgument；263/263 均 `HTTPArgument.always_encode=true`。
- SAZ 对应 13 类 POST 的参数名称、参数数量与 JMX 完全一致；两个账号各自的 Login/Disclaimer 分别复核。
- 除获准动态替换字段外，SAZ 与 JMX 的 POST 静态值无差异。
- 关键 GET/POST URL 的查询参数名称与 SAZ 一致；Case、rnd、row_id 等动态值均按设计替换。

## 变量定义与消费

- Test Plan 变量：`target_protocol`、`target_host`、`target_port`、`case_id`、两组 username/password 均已定义并被消费。
- User Parameters：`lastName`、`firstName`、`person_request_rnd`、`mn_rnd`、`property_request_rnd` 均有来源并被请求消费；两个 User Parameters 均 `per_iteration=true`。
- 28 个 CSS Extractor 产生的变量均有后续消费；未发现已提取但未使用的变量。
- 未发现请求引用但没有变量/提取器来源的普通变量。
- Person 查重与保存共同使用同轮 `${lastName}`、`${firstName}`。
- 两个账号只引用各自 UDV；没有跨线程共享 Cookie 或业务变量。

## WebForms 与提取器 Scope

- 两个 Login GET：分别提取本线程 Login `__VIEWSTATE`、`__VIEWSTATEGENERATOR`，Scope=`parent`，并回填对应 Login POST。
- 两个 Login POST：Scope=`all` 提取 302 跳转后 Index 子样本中的 Disclaimer `__VIEWSTATE`、`__VIEWSTATEGENERATOR`、`__EVENTVALIDATION`；SAZ 会话 005→006 证实字段来源正确。
- `Disclaimer.htm` 不绑定提取器，符合 SAZ 静态响应不含 WebForms 字段的事实。
- Person Form：四个 WebForms/timestamp 提取器及两个 row_id 提取器均绑定 Add Person GET，Scope=`all`；保存和 dropdown 请求正确消费。
- Property Form：四个 WebForms/timestamp、`property_person_id`、`property_sub_type_row_id` 均绑定 Add Property GET，Scope=`all`。
- `property_person_id`：CSS `input[ObjectName="c_person_id"]`、attribute=`value`、Match No.=0、Default=`PERSON_NOT_FOUND`；保存 POST 使用 `c_person_id=${property_person_id}`。
- Property List GET 与刷新 POST 均提取 `property_list_viewstate`、`property_list_viewstategenerator`、`property_list_double_entry_timestamp`，Scope=`all`；POST 回填并覆盖供下一轮使用。
- SAZ 会话 100/131 不含 `__EVENTVALIDATION`，JMX 正确未虚构该字段。

## 动态 Case、Person 与 row_id

- 未出现抓包 Case ID `2000011166`；所有 Case URL、POST 字段及 ShowCount URL 列表均使用 `${case_id}`。
- 未出现抓包 Person ID `2000137319`；Property 保存使用动态 `${property_person_id}`。
- 未出现抓包 row_id `497130`、`497146`、`479399`。
- `driver_license_state_row_id`、`pob_state_row_id`、`property_sub_type_row_id` 均从对应表单精确提取，attribute=`row_id`、Match No.=1、Default=`ROW_ID_NOT_FOUND`，并用于 dropdown URL。
- SAZ 表单响应证实三个 selector 和目标属性存在；`pob_state` 多匹配时 Match No.=1 与抓包调用的首个 row_id 一致。
- Person 保存 175 个参数、Property 保存 37 个参数均与 SAZ 字段集合一致；除姓名/Person 关联/WebForms/Case/timestamp 外，静态业务值与抓包一致。

## JTL

- 恰好 1 个 Simple Data Writer，文件为 `${__P(result_file,RI_Add_Person_Property_Deadlock_${__time(yyyyMMdd_HHmmss,)}.jtl)}`。
- 已保存 timestamp、elapsed/time、label、response code/message、threadName、dataType、success、bytes、sentBytes、threadCounts、URL、latency、idleTime、connectTime 等必需字段。

## JMeter 函数清单

以下函数不视为未定义变量：

- `${__P(person_threads,1)}`
- `${__P(property_threads,1)}`
- `${__P(rampup,0)}`
- `${__P(duration,60)}`
- `${__P(person_loops,10)}`
- `${__P(property_loops,10)}`
- `${__P(iteration_delay_ms,0)}`
- `${__P(result_file,RI_Add_Person_Property_Deadlock_${__time(yyyyMMdd_HHmmss,)}.jtl)}`
- `${__time(yyyyMMddHHmmssSSS,)}`
- `${__Random(1000,9999,)}`
- `${__Random(100000000,999999999,)}`
- `${__threadNum}`
- `${__jexl3("${property_person_id}" != "PERSON_NOT_FOUND" && "${property_person_id}" != "",)}`
- `${__jexl3("${property_person_id}" == "PERSON_NOT_FOUND" || "${property_person_id}" == "",)}`
- `${__char(2)}`

`__char(2)` 在两个 ShowCount 请求中生成 STX 分隔符，共 42 次（每组 21 个），与 SAZ 多 URL 结构一致。
