# PA40 Incident Report 性能测试计划（阶段 1 文字架构）

> 数据源：`PA40_Incident report.saz`（90 个有效编号会话）  
> 阶段限制：本文仅为文字架构；本阶段不创建、修改或验证任何 JMX。  
> 业务目标：5 个并发用户；每个用户登录一次；每个用户循环创建 3 份 Incident Report；预期成功创建并提交 15 份。

## 1. 场景与负载模型

| 参数 | 设计值 | 说明 |
|---|---:|---|
| protocol | `https` | 来自 SAZ |
| target_host | `parms42test.csitech.com` | 来自 SAZ；执行前确认仍为授权压测环境 |
| target_port | `443` | HTTPS 默认端口 |
| concurrency | `5` | 5 个并发用户 |
| rampup | `5s`（建议） | 每秒启动约 1 用户，可在生成 JMX 前调整 |
| Thread Group Loop Count | `1` | 避免登录及外层场景重复 |
| Business Loop Count | `3` | 每线程创建 3 份 Report |
| Same user on each iteration | `true` | 一个线程始终使用同一用户和 Cookie 会话 |
| Scheduler / duration | `false` / 不设 | 本场景按迭代数结束，保证理论创建数为 5×3=15 |
| On Sample Error | `Continue` | 业务循环内用失败标志和 Flow Control Action 跳过当前 Report；不能用 Start Next Thread Loop，因为 Thread Group Loop Count=1 会结束线程 |

说明：这是固定工作量的并发业务场景，不是 10～30 分钟稳定态负载。若要做稳定态测试，应另建按 duration 控制的场景，避免与“每用户恰好创建 3 份”混用。

## 2. SAZ 流量筛选

保留：登录/免责声明、Home 与 Inbox 初始化、随机 Case 打开、Police Reports 页及必要 Tab Count、Incident Report 中间页、Victim/Vehicle/PA Charge 控件初始化与保存、CreateIntake、Report 保存、Workflow 提交与最终列表刷新。

排除：CSS、JavaScript、图片、字体等静态资源；3 条 HTTPS `CONNECT`；无业务状态变更的浏览器资源加载。`ShowCountInTab`、Dropdown、地址/映射与局部刷新请求虽不是最终保存接口，但会初始化页面控件、Tab 计数或返回后续保存所需数据，因此保留。随机 `rnd` 不使用抓包常量，统一动态生成。

## 3. JMeter GUI 树形架构

```text
Test Plan: PA40 Incident Report - 5 Users x 3 Reports
|-- User Defined Variables
|   |-- protocol = ${__P(protocol,https)}
|   |-- target_host = ${__P(target_host,parms42test.csitech.com)}
|   |-- target_port = ${__P(target_port,443)}
|   |-- division_id = 3                         # SAZ 静态值
|   |-- template_id = 1318                     # SAZ 静态值
|   |-- report_type = C                        # SAZ 静态值
|   |-- indicator_type = 1                    # SAZ 静态值
|-- HTTP Request Defaults
|   |-- Protocol/Host/Port = ${protocol}/${target_host}/${target_port}
|   |-- Implementation = HttpClient4; UTF-8; KeepAlive=true; Follow Redirects=true
|-- HTTP Cookie Manager
|   |-- 每线程独立 Cookie；Clear cookies each iteration=false
|-- HTTP Cache Manager
|   |-- 每线程独立缓存；Clear cache each iteration=false
|-- HTTP Header Manager
|   |-- Accept / Accept-Language / User-Agent（保留业务必要头）
|   |-- Origin/Referer 按请求上下文设置；AJAX 请求加 X-Requested-With
|-- CSV Data Set Config: pa40_incident_users.csv
|   |-- Variables from header = username,password,staff_id,region_id
|   |-- Recycle on EOF=false; Stop thread on EOF=true; Sharing mode=All threads
|-- Thread Group: Incident Report Users
|   |-- Threads = ${__P(concurrency,5)}
|   |-- Ramp-up = ${__P(rampup,5)}
|   |-- Loop Count = 1; Same user=true; On Sample Error=Continue
|   |
|   |-- Once Only Controller: Login Once Per User
|   |   |-- Transaction Controller: Login and Disclaimer
|   |   |   |-- GET /RMS/Login
|   |   |   |   |-- CSS Extractor: login_csrf, input[name='__RequestVerificationToken']@value
|   |   |   |-- POST /RMS/Login
|   |   |   |   |-- LoginId=${username}; Password=${password}; __RequestVerificationToken=${login_csrf}
|   |   |   |   |-- 302 链由 Follow Redirects 跟随至 DisclaimerRedirect
|   |   |   |   |-- CSS Extractor: disclaimer_csrf；来源为 POST Login 重定向链中的 `/RMS/DisclaimerRedirect?division_id=3` HTML（SAZ session 05）
|   |   |   |   |   Apply to=Main sample and sub-samples；Selector=input[name='__RequestVerificationToken']@value；Default=NOT_FOUND
|   |   |   |   |-- 独立 Disclaimer.htm（SAZ session 06）不含 token，不作为 token 来源；提取失败则停止当前线程登录流程
|   |   |   |-- GET /RMS/AspSoft/Disclaimer/Disclaimer.htm
|   |   |   |-- POST /RMS/DisclaimerRedirect?handler=Jump
|   |   |   |   |-- __RequestVerificationToken=${disclaimer_csrf}
|   |   |   |-- GET /RMS/Home?division_id=${division_id}
|   |   |   |   |-- inbox_staff_id 后续固定使用当前 CSV 的 ${staff_id}
|   |   |   |-- POST /RMS/Aspsoft/HomeHandler/GetInboxCaseCountOneTime
|   |
|   |-- Loop Controller: Create Incident Report
|   |   |-- Loop Count = ${__P(report_loops,3)}
|   |   |-- User Parameters: Generate Per-Report Dynamic Data
|   |   |   |-- Update Once Per Iteration = true（同一 Report 迭代内值保持稳定）
|   |   |   |-- firstName = TEST${__Random(1000,9999)}
|   |   |   |-- lastName = TEST${__Random(1000,9999)}
|   |   |   |-- ssn = ${__Random(100,999)}-${__Random(10,99)}-${__Random(1000,9999)}
|   |   |   |-- plateNo = P${__Random(100000,999999)}
|   |   |   |-- narrative = PERF-${username}-${__threadNum}-${__jm__Create Incident Report__idx}-${__time(yyyyMMddHHmmssSSS)}
|   |   |   |-- iteration_failed = false
|   |   |   |-- victim_name_rnd = ${__time()}${__Random(100000,999999)}
|   |   |   |-- victim_ssn_rnd = ${__time()}${__Random(100000,999999)}
|   |   |   |-- vehicle_mn_rnd = ${__time()}${__Random(100000,999999)}
|   |   |   |-- request_rnd = ${__time()}${__Random(100000,999999)}
|   |   |-- Simple Controller: Correlation Failure Check（复制到每个关键提取点之后）
|   |   |   |-- 提取值为空或等于 NOT_FOUND 时设置 iteration_failed=true
|   |   |   |-- If Controller: ${__groovy(vars.get('iteration_failed') == 'true')}
|   |   |       |-- Flow Control Action: Go to next iteration of Current Loop
|   |   |
|   |   |-- Transaction Controller: Select Active Case
|   |   |   |-- GET /RMS/inbox/list
|   |   |   |   |-- Uniform Random Timer（仅挂在本 GET 下）：300ms offset + 0~700ms
|   |   |   |   |-- inbox_staff_id=${staff_id}; inbox_sub_id=10030101; page_size=100
|   |   |   |   |-- Regex Extractor: case_id from inquireIncidentSummary links; Match No.=0（随机）
|   |   |   |-- GET /RMS/AspSoft/Dispatcher?nextPID=inquireIncidentSummary&case_id=${case_id}
|   |   |   |-- POST /RMS/AspSoft/EngineService/ShowCountInTab
|   |   |   |   |-- case_id=${case_id}; division_id=${division_id}; currentUrl 使用本轮 Case URL
|   |   |
|   |   |-- Transaction Controller: Open New Incident Report
|   |   |   |-- GET /RMS/Aspsoft/Dispatcher?nextPID=listPoliceReport
|   |   |   |   |-- Uniform Random Timer（仅作用于本次点击）：${__P(think_time_min_ms,300)} + 0~${__P(think_time_range_ms,700)}ms
|   |   |   |   |-- case_id=${case_id}; division_id=${division_id}; report_type=C; indicator_type=1
|   |   |   |   |-- CSS Extractors（POST 必需）: police_csrf, police_doubleEntryTimeStamp；Default=NOT_FOUND
|   |   |   |   |-- 任一失败即 iteration_failed=true，并跳下一业务迭代；不无条件提交空值
|   |   |   |-- POST /RMS/AspSoft/EngineService/ShowCountInTab
|   |   |   |-- POST /RMS/Aspsoft/Dispatcher?nextPID=listPoliceReport
|   |   |   |   |-- template_id=${template_id}; submit_button=New Report
|   |   |   |   |-- doubleEntryTimeStamp=${police_doubleEntryTimeStamp}; token=${police_csrf}
|   |   |   |   |-- Follow redirect 到 IntakeForm/middlepage
|   |   |   |   |-- Regex Extractor: FormGUID；Field=Response Headers；Apply to=Main sample and sub-samples
|   |   |   |   |   Regex=`(?i)Location:\\s*[^\\r\\n]*[?&]FormGUID=([^&\\r\\n]+)`；Default=NOT_FOUND
|   |   |   |   |-- FormGUID 提取失败时 iteration_failed=true，跳下一业务迭代
|   |   |   |   |-- CSS Extractor: middle_csrf（最终 middlepage 响应）
|   |   |   |-- POST /RMS/AspSoft/EngineService/ShowCountInTab
|   |   |
|   |   |-- Transaction Controller: Add Victim
|   |   |   |-- GET /RMS/aspsoft/popupdispatcher?nextPID=addCaseVW
|   |   |   |   |-- Uniform Random Timer（仅挂在本 GET 下，模拟点击 Add Victim）
|   |   |   |   |-- case_id=${case_id}; template_id=${template_id}; report_id=0; Form context=${FormGUID}
|   |   |   |   |-- CSS Extractors: victim_csrf, victim_doubleEntryTimeStamp
|   |   |   |   |-- Regex Extractor: mapping_key；唯一父 sampler=本 Add Victim GET（SAZ session 22）
|   |   |   |   |   Field=Body；Regex=`sessionStorage\\.setItem\\("MappingKey",\\s*"([^"]+)"`；Main sample only；Default=NOT_FOUND
|   |   |   |   |-- mapping_key 提取失败则 iteration_failed=true，跳下一业务迭代
|   |   |   |-- POST /RMS/aspsoft/EngineService/Dropdown        # municipality/control init
|   |   |   |-- POST /RMS/aspsoft/EngineService/Dropdown        # other municipality init
|   |   |   |-- POST /RMS/include/RmsData/PostIDReader?action=IDREADEREABLE
|   |   |   |-- POST /RMS/AspSoft/MasterName?action=setsession   # MN_rnd=${victim_name_rnd}
|   |   |   |-- GET /RMS/AspSoft/MasterName                    # last_name=${lastName}, first_name=${firstName}
|   |   |   |-- POST /RMS/AspSoft/MasterName?action=removesession # MN_rnd=${victim_name_rnd}
|   |   |   |-- POST /RMS/AspSoft/MasterName?action=setsession   # MN_rnd=${victim_ssn_rnd}
|   |   |   |-- GET /RMS/AspSoft/MasterName                    # ssn=${ssn}
|   |   |   |-- POST /RMS/AspSoft/MasterName?action=removesession # MN_rnd=${victim_ssn_rnd}
|   |   |   |-- GET /InfoMapping/api/GisSvc/GeoCode
|   |   |   |   |-- regionId=${region_id}; csi-key=${mapping_key}; address query 使用 SAZ 静态地址
|   |   |   |   |-- JSON Extractors: 精确选择 street1='6 ACORN BLVD' 的 location_id/longitude/latitude/municipality 等
|   |   |   |-- GET /InfoMapping/api/gissvc/GetMasterLocationChildren
|   |   |   |-- GET /InfoMapping/api/gissvc/GetCommonPlaces
|   |   |   |-- POST /RMS/aspsoft/EngineService/Dropdown
|   |   |   |-- POST /RMS/aspsoft/popupdispatcher?nextPID=addCaseVW
|   |   |   |   |-- first/last/ssn 使用同一组动态变量；case_id=${case_id}
|   |   |   |   |-- 地址字段保持 SAZ 值，ID/坐标使用 GeoCode 提取值；sex/race/ethnicity 等保持 SAZ 静态值
|   |   |   |   |-- token=${victim_csrf}; timestamp=${victim_doubleEntryTimeStamp}
|   |   |   |-- GET /RMS/Aspsoft/IntakeForm/middlepage?handler=partialrefresh
|   |   |       |-- Regex/CSS Extractors: victim_person_id, victim_contact_id, victim_location_id（objectname/master_id_list）
|   |   |
|   |   |-- Transaction Controller: Add Vehicle
|   |   |   |-- GET /RMS/aspsoft/popupdispatcher?nextPID=addCaseVehicle
|   |   |   |   |-- Uniform Random Timer（仅挂在本 GET 下，模拟点击 Add Vehicle）
|   |   |   |   |-- CSS Extractors: vehicle_csrf, vehicle_doubleEntryTimeStamp
|   |   |   |-- POST /RMS/aspsoft/EngineService/Dropdown
|   |   |   |-- POST /RMS/include/RmsData/PostIDReader?action=IDREADEREABLE
|   |   |   |-- POST /RMS/AspSoft/MasterName?action=setsession   # MN_rnd=${vehicle_mn_rnd}
|   |   |   |-- GET /RMS/AspSoft/MasterName                    # plate_no=${plateNo}
|   |   |   |-- POST /RMS/AspSoft/MasterName?action=removesession # MN_rnd=${vehicle_mn_rnd}
|   |   |   |-- POST /RMS/aspsoft/EngineService/Dropdown        # make=AUDI -> model list
|   |   |   |-- POST /RMS/aspsoft/popupdispatcher?nextPID=addCaseVehicle
|   |   |   |   |-- plate_no=${plateNo}; make/model 等使用 SAZ 静态值；case_id=${case_id}
|   |   |   |   |-- token=${vehicle_csrf}; timestamp=${vehicle_doubleEntryTimeStamp}
|   |   |   |-- GET /RMS/Aspsoft/IntakeForm/middlepage?handler=partialrefresh
|   |   |       |-- Regex/CSS Extractors: vehicle_id, case_vehicle_id（objectname/master_id_list）
|   |   |
|   |   |-- Transaction Controller: Add Two PA Charges
|   |   |   |-- GET /RMS/aspsoft/popupdispatcher?nextPID=addCaseNJSCode
|   |   |   |   |-- Uniform Random Timer（仅挂在本 GET 下，模拟点击 Add Charge）
|   |   |   |   |-- CSS Extractors: charge_csrf, charge_doubleEntryTimeStamp
|   |   |   |-- GET /RMS/Aspsoft/PopUpDispatcher?nextPID=listPopupCharge_PA&charge=4
|   |   |   |   |-- Regex Extractor charge1_raw: hidden return_value; Match No.=0（随机）
|   |   |   |   |-- JSR223 PostProcessor: HTML/URL decode 后按 `~` 拆为 charge1_code/description/grade...
|   |   |   |-- GET /RMS/Aspsoft/PopUpDispatcher?nextPID=listPopupCharge_PA&charge=3
|   |   |   |   |-- Regex Extractor charge2_raw: hidden return_value; Match No.=0（随机）
|   |   |   |   |-- JSR223 PostProcessor: 解码并拆为独立的 charge2_* 变量
|   |   |   |-- POST /RMS/aspsoft/popupdispatcher?nextPID=addCaseNJSCode
|   |   |   |   |-- 两行控件分别使用 charge1_* 与 charge2_*，禁止混用
|   |   |   |   |-- token=${charge_csrf}; timestamp=${charge_doubleEntryTimeStamp}
|   |   |   |-- GET /RMS/Aspsoft/IntakeForm/middlepage?handler=partialrefresh
|   |   |       |-- Extractors: inv_njs_id_1, inv_njs_id_2
|   |   |
|   |   |-- Transaction Controller: Create Incident Report
|   |   |   |-- JSR223 PreProcessor: Build Intake Object Payload
|   |   |   |   |-- 使用 victim/vehicle/charge/case 的已提取 ID 构造 objects_parameter 与 objects_data_index
|   |   |   |   |-- 不在 UDV/JMX XML 中保存控制字符；Groovy 显式执行 `char stx=(char)0x02`、`char etx=(char)0x03`
|   |   |   |   |-- 用 stx/etx 拼接原始对象串，按 UTF-8 Base64，再 URL encode 一次；不得复用 SAZ 固定串
|   |   |   |-- POST /RMS/Aspsoft/IntakeForm/middlepage?handler=CreateIntake
|   |   |   |   |-- Uniform Random Timer（仅挂在本 POST 下，模拟点击 Create）
|   |   |   |   |-- header RequestVerificationToken=${middle_csrf}
|   |   |   |   |-- template_id=${template_id}; report_id=0; dynamic object payloads
|   |   |   |   |-- JSON Extractor: report_id（仅保留后续使用字段；Default=NOT_FOUND）
|   |   |   |   |-- JSON Assertion [Enabled]: CreateIntake Message OK
|   |   |   |   |   |-- JSON Path=$.message; Expected Value=OK; Match as regular expression=false
|   |   |   |   |-- JSON Assertion [Enabled]: CreateIntake Report ID Is Positive Integer
|   |   |   |       |-- JSON Path=$.report_id; Expected Value=`^[1-9][0-9]*$`; Match as regular expression=true
|   |   |   |-- GET /RMS/Aspsoft/IntakeForm/Intake
|   |   |       |-- case_id=${case_id}; template_id=${template_id}; report_id=${report_id}
|   |   |       |-- CSS Extractor: intake_csrf
|   |   |
|   |   |-- Transaction Controller: Save and Submit Workflow
|   |   |   |-- POST /RMS/AspSoft/IntakeForm/Intake?action=auto_confirm&save_data=1
|   |   |   |   |-- Uniform Random Timer（仅挂在本 POST 下，模拟点击 Save）
|   |   |   |   |-- case_id=${case_id}; template_id=${template_id}; report_id=${report_id}
|   |   |   |   |-- narrative=${narrative}; hdnReportID=${report_id}; hdnCaseID=${case_id}
|   |   |   |   |-- RequestVerificationToken=${intake_csrf}
|   |   |   |   |-- Response Assertion [Enabled]: Auto Confirm HTTP 200
|   |   |   |   |   |-- Field to Test=Response Code; Pattern Matching Rule=Equals; Pattern=200
|   |   |   |   |-- Response Assertion [Enabled]: Auto Confirm Body WF
|   |   |   |       |-- Field to Test=Response Text; Pattern Matching Rule=Matches; Pattern=`(?s)^\\s*WF\\s*$`
|   |   |   |-- GET /RMS/AspSoft/IntakeForm/IntakeReportAssignWorkflow
|   |   |   |   |-- report_ids=${report_id}
|   |   |   |   |-- CSS Extractor: workflow_csrf
|   |   |   |-- POST /RMS/AspSoft/IntakeForm/IntakeReportAssignWorkflow?handler=ReportNextStepSelectedChanged
|   |   |   |   |-- reportIds=${report_id}; nextStep=ROUTE1; RequestVerificationToken=${workflow_csrf}
|   |   |   |-- POST /RMS/AspSoft/IntakeForm/IntakeReportAssignWorkflow?handler=SaveWorkFlow
|   |   |   |   |-- reportIds=${report_id}; route/status 参数沿用 SAZ；token=${workflow_csrf}
|   |   |   |-- POST /RMS/AspSoft/IntakeForm/IntakeReportAssignWorkflow?handler=Clear
|   |   |   |   |-- multipart boundary/Content-Disposition/body 分段保持 SAZ 结构
|   |   |   |   |-- report_ids=${report_id}; __RequestVerificationToken=${workflow_csrf}
|   |   |   |-- GET /RMS/Aspsoft/Dispatcher?nextPID=listPoliceReport
|   |   |   |-- POST /RMS/AspSoft/EngineService/ShowCountInTab
|   |
|   |-- Listener: Simple Data Writer / Result Collector
|       |-- 输出 ${__P(result_file,PA40_Incident_Report.jtl)}
|       |-- CSV JTL；保存 timeStamp,elapsed,label,responseCode,responseMessage,threadName,
|           dataType,success,failureMessage,bytes,sentBytes,grpThreads,allThreads,URL,
|           Latency,IdleTime,Connect
```

Timer 不放在 Loop/Transaction 同级作用域。每个 Uniform Random Timer 只作为目标用户动作 HTTP Sampler 的子元素，因此只延迟该次点击，不会给事务内每个技术请求重复叠加等待。建议主要点击使用 300～1000ms 思考时间。不使用 Synchronizing Timer：本需求是 5 用户并发进入，而非强制同一毫秒同时提交。

错误控制：Thread Group 始终 `Continue`。在 `case_id`、页面 token/timestamp、FormGUID、mapping_key、Victim/Vehicle/Charge IDs、`report_id`、workflow token 等关键提取点后放置 Correlation Failure Check；任一必需值为空或为 `NOT_FOUND` 时设置 `iteration_failed=true`，随后由 If Controller 内的 `Flow Control Action: Go to next iteration of Current Loop` 结束当前 Report 迭代。下一次 Loop 迭代由 User Parameters 将 `iteration_failed` 重置为 false 并生成新业务值。

## 4. 关联与参数化决策

| 变量/字段 | 来源 | 用途/规则 |
|---|---|---|
| username/password/staff_id/region_id | CSV | 每线程唯一用户；`inbox_staff_id=${staff_id}`；Mapping `regionId=${region_id}` |
| case_id | Inbox HTML response | 正则随机提取，Match No.=0；禁止固定抓包 Case ID |
| __RequestVerificationToken | 每个相关 GET/最终重定向 response | CSS 提取并仅回填对应页面的后续 POST/Header；必需 token 提取失败即跳本轮，不提交空值；不得跨页面长期复用 |
| disclaimer_csrf | POST Login 重定向子样本中的 DisclaimerRedirect HTML | Main sample and sub-samples；独立 Disclaimer.htm 不含此 token |
| doubleEntryTimeStamp | 每个弹窗/列表 GET response | 必需字段；CSS 提取、Default=NOT_FOUND，失败即跳本轮 |
| FormGUID | 新建 Report POST 的 Response Headers / Location | Regex 检查 Response Headers，Main sample and sub-samples，Default=NOT_FOUND；失败即跳本轮 |
| mapping_key | Add Victim GET response（SAZ session 22） | 唯一父 sampler；Body/Main sample only 中提取 `sessionStorage MappingKey`；不硬编码 SAZ key |
| firstName/lastName/ssn/plateNo | 循环首个 User Parameters | 每轮动态生成；唯一性检查与保存 POST 必须复用同一变量 |
| address/sex/race/ethnicity/division_id/template_id | SAZ 静态值 | 按 skill 规则保持；地址服务返回的 location ID/经纬度需关联 |
| victim_person_id/contact_id/location_id | Victim partial refresh response | 构造 CreateIntake 对象串 |
| vehicle_id/case_vehicle_id | Vehicle partial refresh response | 构造 CreateIntake 对象串 |
| charge1_* / charge2_* | 两个 PA popup list response | 各自 Match No.=0；HTML/URL decode 后按 `~` 拆分，保持两条记录独立 |
| inv_njs_id_1/inv_njs_id_2 | Charge partial refresh response | 构造 CreateIntake 对象串 |
| objects_parameter/objects_data_index | JSR223 PreProcessor | Groovy 用 `(char)0x02/(char)0x03` 构造 STX/ETX；UTF-8 Base64 后 URL encode 一次；不能在 XML/UDV 放实际控制字符或复用抓包固定 Base64 |
| report_id | CreateIntake JSON response | JSONPath `$.report_id`；用于 Intake 保存、Workflow 与清理 |
| narrative | 循环动态值 | 用于识别 15 个测试产物并辅助后置清理 |
| request_rnd | 循环 User Parameters | `${__time()}${__Random(100000,999999)}`；映射到普通页面、partialrefresh、ShowCount、Popup list、Intake/Workflow URL 的 `rnd`；每个需要独立值的请求可在其前置处理器按同规则刷新 |
| victim_name_rnd/victim_ssn_rnd/vehicle_mn_rnd | 循环 User Parameters | 分别映射到对应 MasterName `setsession -> search -> removesession` 三请求的 `MN_rnd`，同一序列稳定、不同序列隔离 |

ASP.NET 隐藏字段原则：每次响应仅当页面实际存在 `__VIEWSTATE`、`__VIEWSTATEGENERATOR`、`__EVENTVALIDATION`、`__RequestVerificationToken`、`doubleEntryTimeStamp` 时提取；后续 POST 仅回填该页面返回的最新值。本 SAZ 的核心可见字段是 token 与 timestamp，但生成 JMX 时仍需按响应实际存在性处理。

所有表单 POST 优先使用 Parameters 且 `always_encode=true`。JSON 请求（如 Inbox count 的数组 body）放 Body Data。Workflow Clear 是 multipart：必须保持原 boundary、Content-Disposition、Content-Type 和分段结构，同时替换 `report_ids` 与 token；如后续发现 multipart 还含其他动态字段，也必须逐 part 参数化。

## 5. 断言授权状态

以下断言已获用户批准，属于生成器必须实现的启用节点：

| 请求 | 启用断言 | 判定条件 |
|---|---|---|
| POST `/RMS/Aspsoft/IntakeForm/middlepage?handler=CreateIntake` | JSON Assertion ×2 | `$.message` 等于 `OK`；`$.report_id` 存在且匹配正整数正则 `^[1-9][0-9]*$` |
| POST `/RMS/AspSoft/IntakeForm/Intake?action=auto_confirm&save_data=1` | Response Assertion ×2 | Response Code 精确等于 `200`；Response Text 匹配 `(?s)^\\s*WF\\s*$`，即 trim 后精确等于 `WF` |

除此之外没有授权任何 Assertion。Login、Inbox、Victim/Vehicle/Charge popup、Workflow（包括 SaveWorkFlow）和 Duration Assertion 均保持禁用/不生成；它们也不作为本架构中的推荐节点。若后续需要增加，必须由用户再次明确批准并更新本权威架构。

## 6. Listener 与执行方式

仅保留 Simple Data Writer/Result Collector 写 JTL。不得在负载执行时启用 View Results Tree、View Results in Table、Graph Results。建议 CLI 执行；GUI 仅用于小并发调试。15 份的业务成功数应以 CreateIntake 返回有效 `report_id` 且 SaveWorkFlow 成功为准，而不是只看 HTTP 200。

## 7. 预计请求量与产物核对

- 登录事务：每线程 1 次，共 5 次；Cookie 会话跨 3 个业务循环复用。
- Create Incident Report Loop：每线程 3 次，共 15 次。
- 理论 CreateIntake：15 次；理论 Workflow Save：15 次。
- 若任一循环失败并跳到下一循环，实际成功 Report 少于 15；测试报告需列出成功 report_id 与 narrative，失败循环不得计入成功数。
- 测试数据会写入目标环境；执行前应确认账号权限、Case 可写状态、数据保留/清理策略。

## 8. 待用户确认

1. 是否确认每一轮都从 My Active Case Inbox **随机选择 Case**？当前设计如此；若希望每用户 3 份都写到同一 Case，应把 Select Active Case 移到 Loop 外。
2. 请在 `pa40_incident_users.csv` 填入 5 个唯一且有创建/提交权限的账号、密码、staff_id、region_id；占位值不可直接执行。
3. Ramp-up 是否采用 5 秒？是否需要强制 5 用户同时点击 Create/Save（若需要才增加 Synchronizing Timer）。
4. 当前只授权 CreateIntake JSON 断言和 auto_confirm HTTP 200/body `WF` 断言；如需 Login、Inbox、popup、Workflow 或 Duration/SLA 断言，须另行明确批准。
5. 是否确认 SAZ 中静态地址及两类 PA charge 随机候选可用于压测；是否有指定 Case/charge 数据集。
6. 是否需要 Workflow 提交到 `ROUTE1`，还是仅保存草稿；当前按 SAZ 完整提交。
7. 请确认测试后 15 份 report 的保留或清理方式；SAZ 未包含删除链路。
