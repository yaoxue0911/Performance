# RI 同一 Case 并行新增 Person / Property 性能测试架构

## 1. 测试目标与边界

- 来源：`RI_add person and property.saz`（Fiddler SAZ，共 137 个会话）。
- 目标：使用两个不同账号、两个并行 Thread Group，在同一个 `${case_id}` 中持续执行：
  - Person 线程：新增 Person。
  - Property 线程：每轮读取该 Case 当前已有 Person，随机勾选任意一人后新增 Property。
- 目的：制造“新增 Person”与“读取/关联 Person 后新增 Property”对同一 Case 的并发访问，观察数据库死锁、锁等待、请求超时和错误响应。
- 本阶段只定义文字架构；不创建、修改或验证任何 `.jmx`。
- 排除流量：Fiddler 更新、CONNECT、SignalR ping、CAD timer、`get_process_flag`/`set_process_flag` 轮询、WebResource/CSS/JS/image 等静态资源。
- 保留流量：登录、免责声明/Division 初始化、打开 Case、业务页面、控件 dropdown 初始化、Master Name 查重、保存和业务列表刷新。

## 2. SAZ 关键结论

| 业务 | SAZ 会话 | 请求 | 关键结论 |
|---|---:|---|---|
| 登录页 | 003 | `GET /RMS/Login.aspx` | 返回登录所需 `__VIEWSTATE`、`__VIEWSTATEGENERATOR` |
| 登录 | 005 | `POST /RMS/Login.aspx` | `txtUserName`/`txtPassword` 必须分别取两个线程组的账号变量；响应 302 并建立登录 Cookie |
| Disclaimer | 005-017 | Login POST 302→Index、GET Disclaimer、POST DisclaimerRedirect、GET HomeA | Disclaimer POST 的 WebForms 字段实际从 Login POST 重定向后的 Index 子样本提取；`Disclaimer.htm` 为静态内容，不含隐藏字段 |
| 打开 Case | 031 | `GET /RMS/AspSoft/Dispatcher.aspx?nextPID=inquireIncidentSummary&case_id=...` | 抓包 Case ID `2000011166` 不可硬编码，全部替换为 `${case_id}` |
| 打开 Party 列表 | 043/094 | `GET /RMS/Aspsoft/Dispatcher.aspx?nextPID=showCaseContact...` | Person 流程入口及保存后刷新页 |
| 打开新增 Person | 049 | `GET /RMS/Aspsoft/PopUpDispatcher.aspx?nextPID=addCaseVW...` | 返回 Person 保存所需三个 WebForms 隐藏字段和 `doubleEntryTimeStamp` |
| Master Name 查重 | 078/079/086 | setsession、SearchMasterNameSys_MasterPerson、removesession | 查询与保存必须复用本轮生成的动态姓名 |
| 保存 Person | 089 | `POST /RMS/Aspsoft/PopUpDispatcher.aspx?nextPID=addCaseVW...` | 抓包仅 First/Last Name 动态；其余 Person 业务字段按 SAZ 静态值保留，所有 Case ID 替换为 `${case_id}` |
| Property 列表 | 100/131 | GET/POST `Dispatcher.aspx?nextPID=listCaseProperty...` | Property 流程入口及保存后刷新页 |
| 打开新增 Property | 106 | `GET /RMS/Aspsoft/PopUpDispatcher.aspx?nextPID=addCaseProperty...` | 返回 WebForms 隐藏字段，并包含 `input ObjectName='c_person_id' value='<person id>'` 列表 |
| Property dropdown | 125 | `POST /RMS/Aspsoft/engineservice.ashx?action=dropdown&row_id=<form value>` | 返回 Clothing subtype（抓包选中 131/JACKET）；`row_id` 从新增表单动态提取，不硬编码抓包值 479399 |
| 保存 Property | 128 | `POST /RMS/Aspsoft/PopUpDispatcher.aspx?nextPID=addCaseProperty...` | `c_person_id` 必须使用本轮新增页动态随机提取值；其余 Property 业务值保持 SAZ 静态 |

抓包中的 Property 静态非空业务值为：`property_type=CLOTHING`、`property_sub_type=131`、`property_status=23`、`quantity=1`、`value=200`、`value_type=FAIR MARKET VALUE`。空字段仍按抓包为空，不随机化。

抓包中的 Person 静态非空业务值包括：`person_company_flag=P`、`contact_type=APPLICANT`、`driver_license_country=US`、`dob=08/12/1992`（含 txtDate）、`sex=F`、`pob_country=US`、`race=A`、`ethnicity=H`、Location/Mail/Other country 与类型、Region `104900` 等；保存请求中除 First/Last Name、WebForms 令牌、时间戳和 Case ID 外，均复制 SAZ 值（包括空值）。

## 3. 参数化设计

### 3.1 Test Plan — User Defined Variables（不用 CSV）

| 变量 | 初始值 | 用途 |
|---|---|---|
| `target_protocol` | `https` | HTTP Request Defaults |
| `target_host` | `rirmsint.csitech.com` | HTTP Request Defaults |
| `target_port` | `443` | HTTP Request Defaults |
| `case_id` | 用户填写 | 两个线程组访问的同一 Case；替换 URL 和所有 POST body 中的 Case ID |
| `person_username` | 用户填写 | Person Thread Group 登录账号 |
| `person_password` | 用户填写 | Person Thread Group 登录密码 |
| `property_username` | 用户填写 | Property Thread Group 登录账号，必须不同于 Person 账号 |
| `property_password` | 用户填写 | Property Thread Group 登录密码 |

不创建 CSV，不使用 CSV Data Set Config。账号密码只保存在本地 JMX User Defined Variables 中；交付/提交 JMX 前需自行清除真实密码。

### 3.2 运行参数（JMeter Properties）

- Person threads：`${__P(person_threads,1)}`
- Property threads：`${__P(property_threads,1)}`
- Person loops：`${__P(person_loops,10)}`
- Property loops：`${__P(property_loops,10)}`
- Ramp-up：两个线程组均 `${__P(rampup,0)}`
- Scheduler：`true`；Duration：`${__P(duration,60)}`（安全运行上限）
- Loop 间隔：`${__P(iteration_delay_ms,0)}`
- 两个 Thread Group 的 Scheduler start delay 均为 0，Test Plan 的 “Run Thread Groups consecutively” 必须为 false。

默认各 1 个线程代表两个独立操作进程。若提高线程数，同一组内多个线程会共享同一账号凭据但各自拥有独立 Cookie Manager 实例；需要先确认应用是否允许同账号多会话。

### 3.3 动态 Person 姓名

在 Person Loop 的首个步骤使用 `User Parameters: Generate Person Name`，一轮只生成一次并供查重与保存共同使用：

- `lastName = TESTL${__time(yyyyMMddHHmmssSSS,)}${__threadNum}${__Random(1000,9999)}`
- `firstName = TESTF${__time(yyyyMMddHHmmssSSS,)}${__threadNum}${__Random(1000,9999)}`
- `person_request_rnd = ${__Random(100000000,999999999,)}`
- `mn_rnd = ${__Random(100000000,999999999,)}`（setsession、查询、removesession 共用）

User Parameters 必须启用 “Update Once Per Iteration”，避免同一轮的查重请求与保存请求生成不同姓名。

仅 First/Last Name 动态；DOB、sex、race、ethnicity、contact type、地址和其余 Person 字段保持 SAZ 静态。

### 3.4 WebForms 与 Person ID 关联

- 每个 HTML GET 仅在响应存在字段时提取并供紧随其后的 POST 使用：`__VIEWSTATE`、`__VIEWSTATEGENERATOR`、`__EVENTVALIDATION`、`doubleEntryTimeStamp`。
- 登录、Person 和 Property 使用不同变量前缀，避免两个线程组及多个表单之间混用，例如 `login_*`、`person_form_*`、`property_form_*`、`property_list_*`。
- 提取器 Scope 逐请求固定如下：
  - `GET /RMS/Login.aspx`：`Main sample only`（200，无重定向）。
  - `POST /RMS/Login.aspx`：`Main sample and sub-samples`；Login POST 为 302，从跳转后的 Index HTML 提取 Disclaimer POST 所需字段。
  - `GET Disclaimer.htm`：不配置提取器（静态 200，不含 WebForms 隐藏字段）。
  - `GET ...nextPID=addCaseVW`：`Main sample and sub-samples`（请求带 Referer；从最终表单响应取值）。
  - 首次 `GET ...nextPID=listCaseProperty`：`Main sample and sub-samples`（请求带 Referer；从 Property List 表单取值）。
  - `GET ...nextPID=addCaseProperty`：`Main sample and sub-samples`（请求带 Referer；WebForms 值与 Person 候选均从该表单取值）。
  - `POST ...nextPID=listCaseProperty`：`Main sample and sub-samples`（请求带 Referer；从刷新后的列表表单覆盖下一轮变量）。
  - Disclaimer POST 的 302 仅用于 Cookie/导航，不在其上绑定提取器。
- 表单变量与 POST 字段一一映射：
  - Person form：`person_form_viewstate` → `__VIEWSTATE`，`person_form_viewstategenerator` → `__VIEWSTATEGENERATOR`，`person_form_eventvalidation` → `__EVENTVALIDATION`，`person_form_double_entry_timestamp` → `ctl00$ContentPlaceHolder1$ctl00$doubleEntryTimeStamp`。
  - Property form：`property_form_viewstate` → `__VIEWSTATE`，`property_form_viewstategenerator` → `__VIEWSTATEGENERATOR`，`property_form_eventvalidation` → `__EVENTVALIDATION`，`property_form_double_entry_timestamp` → `ctl00$ContentPlaceHolder1$ctl00$doubleEntryTimeStamp`。
  - Person 登录：`login_person_viewstate` → Login POST `__VIEWSTATE`；`login_person_viewstategenerator` → Login POST `__VIEWSTATEGENERATOR`。
  - Property 登录：`login_property_viewstate` → Login POST `__VIEWSTATE`；`login_property_viewstategenerator` → Login POST `__VIEWSTATEGENERATOR`。
  - Person Login POST 的重定向响应提取：`person_disclaimer_viewstate` → Disclaimer POST `__VIEWSTATE`；`person_disclaimer_viewstategenerator` → `__VIEWSTATEGENERATOR`；`person_disclaimer_eventvalidation` → `__EVENTVALIDATION`。
  - Property Login POST 的重定向响应提取：`property_disclaimer_viewstate` → Disclaimer POST `__VIEWSTATE`；`property_disclaimer_viewstategenerator` → `__VIEWSTATEGENERATOR`；`property_disclaimer_eventvalidation` → `__EVENTVALIDATION`。
- `GET ...nextPID=addCaseProperty` 下添加 CSS Selector Extractor：
  - 变量：`property_person_id`
  - Selector：`input[ObjectName="c_person_id"]`
  - Attribute：`value`
  - Match No.：`0`（在本轮响应的所有已有 Person 中随机选一个）
  - Default：`PERSON_NOT_FOUND`
- Property POST 的 `c_person_id=${property_person_id}`。每轮重新打开新增页并重新提取，不能使用抓包硬编码值 `2000137319`，也不能跨线程传递 Person Thread 新增出的 ID。
- Property Loop 开头生成 `property_request_rnd=${__Random(100000000,999999999,)}`，本轮新增页 GET 与保存 POST 共用。
- 保存分支 If 条件：`${__jexl3("${property_person_id}" != "PERSON_NOT_FOUND" && "${property_person_id}" != "",)}`。
- 无候选分支 If 条件：`${__jexl3("${property_person_id}" == "PERSON_NOT_FOUND" || "${property_person_id}" == "",)}`。两个条件严格互斥；无候选时不提交，记录 Debug Sampler 并进入下一轮，避免用空值或上一轮旧值保存。

### 3.5 Property List 表单关联链

- 首次 `GET ...nextPID=listCaseProperty`（会话 100）提取，Scope=`Main sample and sub-samples`。该页面及刷新 POST 不含 `__EVENTVALIDATION`，因此只关联以下三个字段：
  - `property_list_viewstate`：CSS `input#__VIEWSTATE` / attribute `value`
  - `property_list_viewstategenerator`：CSS `input#__VIEWSTATEGENERATOR` / attribute `value`
  - `property_list_double_entry_timestamp`：CSS `input[ObjectName="doubleEntryTimeStamp"], input[id$="doubleEntryTimeStamp"]` / attribute `value`
- 每轮 `POST ...nextPID=listCaseProperty`（会话 131）明确回填：
  - `__VIEWSTATE=${property_list_viewstate}`
  - `__VIEWSTATEGENERATOR=${property_list_viewstategenerator}`
  - `ctl00$ContentPlaceHolder1$ctl00$doubleEntryTimeStamp=${property_list_double_entry_timestamp}`
- 同一 POST 响应下再次配置上述三个同名 CSS Extractor，Scope=`Main sample and sub-samples`，覆盖变量供下一轮刷新 POST 使用。首次循环来自 GET 100，后续循环来自上一轮 POST 131。

### 3.6 Dropdown row_id 关联

抓包中的 `497130`、`497146`、`479399` 均能从对应新增表单的 `select` 元素 `row_id` 属性取得，不硬编码：

- Person form：CSS `select[ObjectName="driver_license_state"]` / `row_id` → `driver_license_state_row_id`
- Person form：CSS `select[ObjectName="pob_state"]` / `row_id` → `pob_state_row_id`
- Property form：CSS `select[ObjectName="property_sub_type"]` / `row_id` → `property_sub_type_row_id`

## 4. JMeter GUI 树形架构

```text
Test Plan: RI Same Case Person-Property Lock Contention
|-- User Defined Variables: Environment / Case / Two Accounts
|   |-- target_protocol = https
|   |-- target_host = rirmsint.csitech.com
|   |-- target_port = 443
|   |-- case_id = <用户填写>
|   |-- person_username = <用户填写>
|   |-- person_password = <用户填写>
|   |-- property_username = <用户填写且必须不同>
|   `-- property_password = <用户填写>
|-- HTTP Request Defaults
|-- HTTP Header Manager: Browser-compatible common headers
|   `-- 所有 HTTP Request: Follow Redirects=true；POST Parameters: always_encode=true
|
|-- Thread Group: Add Person Process
|   |-- Threads = ${__P(person_threads,1)}
|   |-- Ramp-up = ${__P(rampup,0)}
|   |-- Scheduler = true; Duration = ${__P(duration,60)}
|   |-- Loop Count = 1 (业务循环由下级 Loop Controller 控制)
|   |-- On error = Continue
|   |-- HTTP Cookie Manager: Person Session (clear each iteration = false)
|   |-- HTTP Cache Manager
|   |-- Once Only Controller: Login and Open Case
|   |   |-- Transaction Controller: Person Account Login
|   |   |   |-- GET /RMS/Login.aspx
|   |   |   |   `-- CSS Extractors: login_person_viewstate, login_person_viewstategenerator
|   |   |   |-- POST /RMS/Login.aspx
|   |   |   |   |-- txtUserName=${person_username}
|   |   |   |   |-- txtPassword=${person_password}
|   |   |   |   |-- __VIEWSTATE=${login_person_viewstate}
|   |   |   |   |-- __VIEWSTATEGENERATOR=${login_person_viewstategenerator}
|   |   |   |   `-- CSS Extractors (Scope=Main+sub): person_disclaimer_viewstate, person_disclaimer_viewstategenerator, person_disclaimer_eventvalidation
|   |   |   |-- GET /RMS/AspSoft/Disclaimer/Disclaimer.htm
|   |   |   |-- POST /RMS/DisclaimerRedirect.aspx?division_id=3
|   |   |   |   |-- __VIEWSTATE=${person_disclaimer_viewstate}
|   |   |   |   |-- __VIEWSTATEGENERATOR=${person_disclaimer_viewstategenerator}
|   |   |   |   `-- __EVENTVALIDATION=${person_disclaimer_eventvalidation}
|   |   |   `-- GET /RMS/HomeA.aspx?division_id=3
|   |   `-- Transaction Controller: Open Case for Person
|   |       |-- GET /RMS/AspSoft/Dispatcher.aspx?nextPID=inquireIncidentSummary&case_id=${case_id}
|   |       `-- GET /RMS/Aspsoft/Dispatcher.aspx?nextPID=showCaseContact&case_id=${case_id}&division_id=3
|   `-- Loop Controller: Add Person Loop (${__P(person_loops,10)})
|       |-- User Parameters: Generate Person Name
|       |   |-- lastName = TESTL...dynamic...
|       |   |-- firstName = TESTF...dynamic...
|       |   |-- person_request_rnd = random cache-buster
|       |   `-- mn_rnd = random Master Name session key (Update Once Per Iteration=true)
|       |-- Transaction Controller: Add Person
|       |   |-- GET /RMS/Aspsoft/PopUpDispatcher.aspx?nextPID=addCaseVW&case_id=${case_id}&rnd=${person_request_rnd}
|       |   |   |-- Constant Timer: ${__P(iteration_delay_ms,0)} ms (仅绑定本轮首个 Form GET，每轮一次)
|       |   |   `-- CSS Extractors (Scope=Main+sub): person_form_viewstate, person_form_viewstategenerator, person_form_eventvalidation, person_form_double_entry_timestamp, driver_license_state_row_id, pob_state_row_id
|       |   |-- POST /RMS/Aspsoft/engineservice.ashx?action=dropdown&row_id=${driver_license_state_row_id}
|       |   |-- POST /RMS/Aspsoft/engineservice.ashx?action=dropdown&row_id=${pob_state_row_id}
|       |   |-- POST /RMS/Include/CommonModule/Remote.ashx?action=GET_CITY_LIST
|       |   |-- GET /RMS/Include/RMS/IDReaderHandler.ashx?action=IDREADEREABLE
|       |   |-- POST /RMS/AspSoft/MasterName.aspx?PageID=SearchMasterNameSys_MasterPerson&action=setsession&rnd=${mn_rnd}
|       |   |   `-- first/last name use this iteration's variables
|       |   |-- GET /RMS/AspSoft/MasterName.aspx?PageID=SearchMasterNameSys_MasterPerson&...last_name=${lastName}&first_name=${firstName}...
|       |   |-- POST /RMS/AspSoft/MasterName.aspx?PageID=SearchMasterNameSys_MasterPerson&action=removesession&MN_rnd=${mn_rnd}
|       |   |-- GET /RMS/aspsoft/engineservice.ashx?action=getserverdatetime
|       |   `-- POST /RMS/Aspsoft/PopUpDispatcher.aspx?nextPID=addCaseVW&case_id=${case_id}&rnd=${person_request_rnd}
|       |       |-- first/last name = ${firstName}/${lastName}
|       |       |-- all Case ID fields = ${case_id}
|       |       |-- WebForms fields/timestamp = four current `person_form_*` variables (explicit mapping in 3.4)
|       |       `-- all other business fields = SAZ static values
|       |-- Transaction Controller: Refresh Person List
|       |   |-- GET /RMS/Aspsoft/Dispatcher.aspx?nextPID=showCaseContact&case_id=${case_id}&division_id=3
|       |   `-- POST /RMS/AspSoft/EngineService.ashx?action=ShowCountInTab&nextPID=showCaseContact&case_id=${case_id}&division_id=3...
|
|-- Thread Group: Add Property Process
|   |-- Threads = ${__P(property_threads,1)}
|   |-- Ramp-up = ${__P(rampup,0)}
|   |-- Scheduler = true; Duration = ${__P(duration,60)}
|   |-- Loop Count = 1 (业务循环由下级 Loop Controller 控制)
|   |-- On error = Continue
|   |-- HTTP Cookie Manager: Property Session (与 Person Session 隔离)
|   |-- HTTP Cache Manager
|   |-- Once Only Controller: Login and Open Case
|   |   |-- Transaction Controller: Property Account Login
|   |   |   |-- GET /RMS/Login.aspx
|   |   |   |   `-- CSS Extractors: login_property_viewstate, login_property_viewstategenerator
|   |   |   |-- POST /RMS/Login.aspx
|   |   |   |   |-- txtUserName=${property_username}
|   |   |   |   |-- txtPassword=${property_password}
|   |   |   |   |-- __VIEWSTATE=${login_property_viewstate}
|   |   |   |   |-- __VIEWSTATEGENERATOR=${login_property_viewstategenerator}
|   |   |   |   `-- CSS Extractors (Scope=Main+sub): property_disclaimer_viewstate, property_disclaimer_viewstategenerator, property_disclaimer_eventvalidation
|   |   |   |-- GET /RMS/AspSoft/Disclaimer/Disclaimer.htm
|   |   |   |-- POST /RMS/DisclaimerRedirect.aspx?division_id=3
|   |   |   |   |-- __VIEWSTATE=${property_disclaimer_viewstate}
|   |   |   |   |-- __VIEWSTATEGENERATOR=${property_disclaimer_viewstategenerator}
|   |   |   |   `-- __EVENTVALIDATION=${property_disclaimer_eventvalidation}
|   |   |   `-- GET /RMS/HomeA.aspx?division_id=3
|   |   `-- Transaction Controller: Open Case for Property
|   |       |-- GET /RMS/AspSoft/Dispatcher.aspx?nextPID=inquireIncidentSummary&case_id=${case_id}
|   |       |-- GET /RMS/Aspsoft/Dispatcher.aspx?nextPID=showCaseContact&case_id=${case_id}&division_id=3
|   |       `-- GET /RMS/Aspsoft/Dispatcher.aspx?nextPID=listCaseProperty&case_id=${case_id}&division_id=3
|   |           `-- CSS Extractors (Scope=Main+sub): property_list_viewstate, property_list_viewstategenerator, property_list_double_entry_timestamp
|   `-- Loop Controller: Add Property Loop (${__P(property_loops,10)})
|       |-- User Parameters: Generate Request Cache-buster
|       |   `-- property_request_rnd = random (Update Once Per Iteration=true)
|       |-- Transaction Controller: Load Property Form and Select Existing Person
|       |   |-- GET /RMS/Aspsoft/PopUpDispatcher.aspx?nextPID=addCaseProperty&case_id=${case_id}&rnd=${property_request_rnd}
|       |   |   |-- Constant Timer: ${__P(iteration_delay_ms,0)} ms (仅绑定本轮首个 Form GET，每轮一次)
|       |   |   |-- CSS Extractors (Scope=Main+sub): property_form_viewstate, property_form_viewstategenerator, property_form_eventvalidation, property_form_double_entry_timestamp
|       |   |   |-- CSS Extractor: property_person_id, selector input[ObjectName="c_person_id"], attribute value, match 0, default PERSON_NOT_FOUND, Scope=Main+sub
|       |   |   `-- CSS Extractor: property_sub_type_row_id, selector select[ObjectName="property_sub_type"], attribute row_id, Scope=Main+sub
|       |   `-- POST /RMS/Aspsoft/engineservice.ashx?action=dropdown&row_id=${property_sub_type_row_id}
|       |-- If Controller: candidate exists
|       |   |-- Condition = ${__jexl3("${property_person_id}" != "PERSON_NOT_FOUND" && "${property_person_id}" != "",)}
|       |   `-- Transaction Controller: Add Property
|       |       `-- POST /RMS/Aspsoft/PopUpDispatcher.aspx?nextPID=addCaseProperty&case_id=${case_id}&rnd=${property_request_rnd}
|       |           |-- c_person_id=${property_person_id}
|       |           |-- all Case ID fields = ${case_id}
|       |           |-- WebForms fields/timestamp = four current `property_form_*` variables (explicit mapping in 3.4)
|       |           `-- all other Property fields = SAZ static values
|       |-- If Controller: candidate missing
|       |   |-- Condition = ${__jexl3("${property_person_id}" == "PERSON_NOT_FOUND" || "${property_person_id}" == "",)}
|       |   `-- Debug Sampler: No existing Person in current Property form (do not submit)
|       |-- Transaction Controller: Refresh Property List
|       |   `-- POST /RMS/Aspsoft/Dispatcher.aspx?nextPID=listCaseProperty&case_id=${case_id}&division_id=3
|       |       |-- POST fields explicitly map three latest `property_list_*` values
|       |       `-- CSS Extractors (Scope=Main+sub) overwrite the same three `property_list_*` variables for next loop
|       `-- Transaction Controller: Refresh Property Tab Count
|           `-- POST /RMS/AspSoft/EngineService.ashx?action=ShowCountInTab&nextPID=listCaseProperty&case_id=${case_id}&division_id=3...
|
`-- Simple Data Writer
    `-- Output: RI_Add_Person_Property_Deadlock_${__time(yyyyMMdd_HHmmss,)}.jtl
```

## 5. 并发与死锁观测设计

- 两个 Thread Group 默认并行启动，且使用独立 Cookie Manager 和不同账号，等价于两个独立浏览器进程。
- 不使用 Critical Section Controller、跨线程锁或共享 Person ID；否则会人为串行化并掩盖服务端锁竞争。
- Property 每轮从服务端当前返回的 Person 列表重新随机选择，所以既可能选中 Case 原有 Person，也可能选中 Person 线程刚添加的人，符合“任意已有 Person”。
- 默认不增加业务思考时间，使两个保存循环尽可能重叠；可用 `iteration_delay_ms` 做对照组。
- JTL 至少保存：timestamp、elapsed、label、responseCode、responseMessage、threadName、success、failureMessage、bytes/sentBytes、grpThreads/allThreads、URL、Latency、IdleTime、Connect。
- 服务端应同步采集数据库 deadlock graph/锁等待与应用日志；仅凭 JMeter 客户端超时不能证明死锁。

## 6. 断言建议记录（用户已明确禁用）

| 请求 | 推荐断言 | 建议内容 |
|---|---|---|
| 两个登录 POST | Response Assertion | 最终响应不包含登录页错误，且已进入 `/RMS/Index.aspx` |
| 打开 Case | Response Assertion | HTTP 200，页面包含当前 `${case_id}` 或 Case Summary 标识 |
| 保存 Person | Response Assertion | 响应包含 `parent.CloseDialog(1` |
| 新增 Property GET | Response Assertion | 页面存在 `ObjectName='c_person_id'`（若 Case 预置至少一人） |
| 保存 Property | Response Assertion | 响应包含 `parent.CloseDialog(1` |
| 全部业务请求 | Duration Assertion | 阈值由用户指定，用于标记长锁等待 |

以上仅保留为设计历史。用户已明确要求不添加任何断言；生成的 JMX 不得包含 Response、JSON、Duration 或其他 Assertion 元件。

## 7. 已批准的生成设置与运行前提

1. 运行前应确保 `${case_id}` 对两个账号均可见且可编辑，并且测试 Case 可安全写入 Person/Property。
2. 生成脚本按 SAZ 保留 Disclaimer/Division 3 流程；若某账号环境不显示 Disclaimer，需要后续另行批准条件分支调整。
3. Person/Property 默认各 1 个线程、各 10 次业务循环。
4. Case 若没有初始 Person，Property 线程会跳过无候选轮次，直至新增页返回 Person。
5. 不生成任何断言。
6. 不添加跨 Thread Group 起跑栅栏、JSR223 或 Critical Section Controller；两组同时启动并在登录后自然重叠。

用户已明确批准按本架构生成并校验 JMX。
