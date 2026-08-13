# PA40 Incident Report 稳定负载测试计划（阶段 2 已批准架构）

> 状态：用户已明确批准按本架构生成 JMX。负载、参数化、静态值和断言选择均已冻结；配套 CSV 仍为占位数据，不可真实执行。

## 1. 测试目标与输入

- 抓包：`Fiddler file/PA40_Incident report.saz`
- 场景：PA40 Incident Report 端到端稳定负载测试
- 目标：5 个并发用户持续执行“选择活动案件并新建、保存、提交 Incident Report”的业务循环
- 目标环境：`https://parms42test.csitech.com:443`
- 并发线程数：`5`
- Ramp-up：`5 秒`（已批准）
- Scheduler duration：`600 秒`（从线程组启动开始计时，包含 ramp-up 和每线程一次的登录）
- 固定循环次数：无。业务 Loop Controller 设置为 `Forever`，由 600 秒 Scheduler 截止；不沿用旧方案的 3 次循环。
- 场景类型：稳定负载

## 2. SAZ 业务流摘要

SAZ 含 90 个会话。保留 52 个能够证明参与认证、页面/控件初始化、唯一性查询、业务保存、报告创建和工作流提交的 HTTP 会话。业务顺序为：

1. 登录并完成 Disclaimer 跳转，每线程仅执行一次。
2. 打开 My Active Incidents/Cases，随机选择当前账号可见的一个 `case_id`。
3. 打开案件详情和 Police Report 列表，发起 New Report，取得本轮 `FormGUID`。
4. 添加 Victim：执行 dropdown/ID Reader 初始化、姓名和 SSN 唯一性查询、地址查询及保存。
5. 添加 Vehicle：执行 dropdown/ID Reader 初始化、车牌唯一性查询、车型下拉及保存。
6. 打开 PA Charge 弹窗，从两次候选列表分别随机选择一项并保存两条 NJS/charge。
7. 根据本轮新建的联系人、车辆、NJS 和案件对象 ID 动态组装对象图，创建 Intake Report，提取新 `report_id`。
8. 打开并保存 Incident Report，然后按捕获的 `ROUTE1` 流程提交，清理工作流弹窗并刷新报告列表。
9. 在 600 秒结束前重复步骤 2～8。

## 3. 流量取舍

### 保留

- 登录、LoginRedirect、Index、Disclaimer、RMS/Home。
- Inbox 列表和案件/Police Report 页面初始化。
- New Report、middlepage、Victim/Vehicle/NJS popup、dropdown、ID Reader、MasterName 查询。
- GeoCode、MasterLocation children/common places；它们属于捕获到的地址选择路径。地址保存值仍按参数化规则保持静态，不从 GeoCode 响应动态覆盖。
- CreateIntake、Intake 保存、工作流选择/保存/清理、最终报告列表刷新。

### 排除

- 会话 10 `GetInboxCaseCountOneTime` 和会话 13/15/21/81/90 `ShowCountInTab`：计数/status 类请求，不是核心业务提交链路。
- CSS、JavaScript、图片、字体等静态资源。
- CONNECT 隧道会话。
- 页面图片（包括 Agency Logo）及其他不影响业务状态的展示资源。

## 4. JMeter 文字版测试树

```text
Test Plan: PA40 Incident Report - 5 Users / 600 Seconds
├── User Defined Variables
│   ├── target_host = parms42test.csitech.com
│   ├── target_port = 443
│   ├── protocol = https
│   ├── division_id = 3
│   ├── inbox_sub_id = 10030101
│   ├── template_id = 1318
│   ├── report_type = C
│   ├── indicator_type = 1
│   └── master_location_id = 19198
├── HTTP Request Defaults
│   ├── Protocol = ${protocol}
│   ├── Server = ${target_host}
│   ├── Port = ${target_port}
│   ├── UTF-8
│   └── Follow Redirects = false（保留抓包中的显式 302/GET 顺序）
├── HTTP Cookie Manager
│   └── Clear cookies each iteration = false
├── HTTP Cache Manager
├── HTTP Header Manager
│   └── 按各捕获请求保留 Accept、Content-Type、Origin、Referer、X-Requested-With；不写死 Cookie
├── CSV Data Set Config: pa40_incident_users.csv
│   ├── Variable names = username,password,staff_id,region_id
│   ├── Recycle on EOF = false
│   ├── Stop thread on EOF = true
│   └── Sharing mode = All threads
├── Thread Group: Stable Load
│   ├── Number of Threads = 5
│   ├── Ramp-up = 5 seconds
│   ├── Thread Group loop count = 1
│   ├── Scheduler = enabled
│   ├── Duration = 600 seconds
│   └── Action after sampler error = Continue（由下方关联失败守卫控制当前业务迭代）
│       ├── Once Only Controller: Per-thread authentication and initialization
│       │   └── Transaction Controller: Login and Disclaimer
│       │       ├── GET /RMS/Login
│       │       │   └── CSS Selector Extractor: login_csrf
│       │       │       input[name="__RequestVerificationToken"] / value / Match 1
│       │       ├── POST /RMS/Login
│       │       │   └── LoginId=${username}, Password=${password}, __RequestVerificationToken=${login_csrf}
│       │       ├── GET /RMS/LoginRedirect
│       │       ├── GET /RMS/Index
│       │       ├── GET /RMS/DisclaimerRedirect
│       │       │   ├── division_id=${division_id}
│       │       │   └── CSS Selector Extractor: disclaimer_csrf
│       │       ├── GET /RMS/AspSoft/Disclaimer/Disclaimer.htm
│       │       ├── POST /RMS/DisclaimerRedirect
│       │       │   └── __RequestVerificationToken=${disclaimer_csrf}
│       │       ├── GET /RMS
│       │       └── GET /RMS/Home
│       │           ├── division_id=${division_id}
│       │           ├── Response Assertion [Enabled]: Authenticated Home Logout Link
│       │           │   ├── Field to Test = Response Text
│       │           │   ├── Pattern Matching Rule = Substring
│       │           │   └── Pattern = `href="/RMS/Logout"`
│       │           │       来源：SAZ 会话 09 `/RMS/Home?division_id=3` 响应正文第 129 行；该 sampler 是实际产生此已认证主页特征的请求
│       │           └── 登录/初始化失败：Flow Control Action = Stop Current Thread
│       └── Loop Controller: Create and submit Incident Report (Forever)
│           ├── User Parameters: Per-report dynamic data
│           │   ├── iteration_failed = false
│           │   ├── firstName = TEST${__Random(1000,9999)}
│           │   ├── lastName = TEST${__Random(1000,9999)}
│           │   ├── ssn = ${__Random(100,999)}-${__Random(10,99)}-${__Random(1000,9999)}
│           │   ├── plateNo = P${__Random(100000,999999)}
│           │   ├── narrative = TEST REPORT ${__threadNum}-${__time(yyyyMMddHHmmssSSS)}-${__Random(1000,9999)}
│           │   ├── contact_name_mn_rnd = 0.${__Random(100000000,999999999)}
│           │   ├── contact_ssn_mn_rnd = 0.${__Random(100000000,999999999)}
│           │   ├── vehicle_mn_rnd = 0.${__Random(100000000,999999999)}
│           │   ├── victim_popup_rnd = 0.${__Random(100000000,999999999)}
│           │   ├── vehicle_popup_rnd = 0.${__Random(100000000,999999999)}
│           │   └── njs_popup_rnd = 0.${__Random(100000000,999999999)}
│           ├── Simple Controller: Correlation failure guard（复制到每个关键提取/保存点之后）
│           │   ├── 若 sampler 失败，或关键值为空/等于 NOT_FOUND：iteration_failed=true
│           │   └── If iteration_failed=true → Flow Control Action: Go to next iteration of Current Loop
│           ├── Uniform Random Timer
│           │   └── 每个业务请求延迟 500～1500 ms（已批准）
│           ├── Transaction Controller: Open active case and report list
│           │   ├── GET /RMS/inbox/list
│           │   │   ├── inbox_staff_id=${staff_id}, inbox_sub_id=${inbox_sub_id}
│           │   │   ├── Regular Expression Extractor: case_id / Match 0（从当前用户候选案件随机取一项）
│           │   │   └── Regular Expression Extractor: mapping_key / Match 1
│           │   │       来源：本响应 `sessionStorage.setItem("MappingKey", "...")`（SAZ 会话 11）
│           │   ├── GET /RMS/AspSoft/Dispatcher
│           │   │   └── case_id=${case_id}
│           │   └── GET /RMS/Aspsoft/Dispatcher
│           │       ├── case_id=${case_id}, division_id=${division_id}
│           │       ├── report_type=${report_type}, indicator_type=${indicator_type}
│           │       ├── CSS Selector Extractor: report_list_csrf
│           │       └── CSS Selector Extractor: report_list_timestamp（doubleEntryTimeStamp）
│           ├── Transaction Controller: Start new report
│           │   ├── POST /RMS/Aspsoft/Dispatcher
│           │   │   ├── query: case_id=${case_id}, division_id=${division_id}, report_type=${report_type}, indicator_type=${indicator_type}
│           │   │   ├── form: template_id=${template_id}, submit_button=New Report
│           │   │   ├── doubleEntryTimeStamp=${report_list_timestamp}
│           │   │   ├── __RequestVerificationToken=${report_list_csrf}
│           │   │   └── Boundary Extractor: form_guid（从 302 Location 的 FormGUID=... 提取）
│           │   └── GET /RMS/Aspsoft/IntakeForm/middlepage
│           │       ├── report_id=0, case_id=${case_id}, FormGUID=${form_guid}
│           │       ├── Regular Expression Extractor: case_location_id
│           │       └── Regular Expression Extractor: case_master_object（CASE/ORG 对象串）
│           ├── Transaction Controller: Add victim
│           │   ├── GET /RMS/aspsoft/popupdispatcher
│           │   │   ├── case_id=${case_id}, report_id=0, rnd=${victim_popup_rnd}
│           │   │   ├── CSS Selector Extractor: victim_csrf
│           │   │   └── CSS Selector Extractor: victim_timestamp
│           │   ├── POST /RMS/aspsoft/EngineService/Dropdown
│           │   ├── POST /RMS/aspsoft/EngineService/Dropdown
│           │   ├── POST /RMS/include/RmsData/PostIDReader
│           │   ├── POST /RMS/AspSoft/MasterName
│           │   │   └── query rnd=${contact_name_mn_rnd}; body MN_rnd=${contact_name_mn_rnd}; ToObjects/ToAliasObjects 保留抓包值
│           │   ├── GET /RMS/AspSoft/MasterName
│           │   │   └── last_name=${lastName}, first_name=${firstName}, MN_rnd=${contact_name_mn_rnd}, rnd=0.${__Random(100000000,999999999,request_rnd)}
│           │   ├── POST /RMS/AspSoft/MasterName
│           │   │   └── MN_rnd=${contact_name_mn_rnd}（name removesession）
│           │   ├── POST /RMS/AspSoft/MasterName
│           │   │   └── query rnd=${contact_ssn_mn_rnd}; body MN_rnd=${contact_ssn_mn_rnd}
│           │   ├── GET /RMS/AspSoft/MasterName
│           │   │   └── ssn=${ssn}, MN_rnd=${contact_ssn_mn_rnd}, rnd=0.${__Random(100000000,999999999,request_rnd)}
│           │   ├── POST /RMS/AspSoft/MasterName
│           │   │   └── MN_rnd=${contact_ssn_mn_rnd}（SSN removesession）
│           │   ├── GET /InfoMapping/api/GisSvc/GeoCode
│           │   │   └── condition=6, regionId=${region_id}, csi-key=${mapping_key}
│           │   ├── GET /InfoMapping/api/gissvc/GetMasterLocationChildren
│           │   │   └── regionId=${region_id}, masterLocationId=${master_location_id}, csi-key=${mapping_key}
│           │   ├── GET /InfoMapping/api/gissvc/GetCommonPlaces
│           │   │   └── regionId=${region_id}, masterLocationId=${master_location_id}, csi-key=${mapping_key}
│           │   ├── POST /RMS/aspsoft/EngineService/Dropdown
│           │   ├── POST /RMS/aspsoft/popupdispatcher
│           │   │   ├── query rnd=${victim_popup_rnd}; first_name=${firstName}, last_name=${lastName}, ssn=${ssn}
│           │   │   ├── case_id=${case_id}, __RequestVerificationToken=${victim_csrf}
│           │   │   ├── doubleEntryTimeStamp=${victim_timestamp}
│           │   │   └── 地址/位置按 SAZ 静态保存值（见第 6 节）
│           │   └── GET /RMS/Aspsoft/IntakeForm/middlepage
│           │       ├── handler=partialrefresh, rnd=0.${__Random(100000000,999999999,request_rnd)}
│           │       └── XPath Extractor: contact_master_object（person/contact/location IDs）
│           │           只取同一 `<tr>` 中姓名为 `${lastName}, ${firstName}` 的 master_id_list value
│           │           XPath: //tr[.//a[contains(normalize-space(.), concat('${lastName}', ', ', '${firstName}'))]]//input[@objectname='master_id_list']/@value
│           ├── Transaction Controller: Add vehicle
│           │   ├── GET /RMS/aspsoft/popupdispatcher
│           │   │   ├── rnd=${vehicle_popup_rnd}
│           │   │   ├── CSS Selector Extractor: vehicle_csrf
│           │   │   └── CSS Selector Extractor: vehicle_timestamp
│           │   ├── POST /RMS/aspsoft/EngineService/Dropdown
│           │   ├── POST /RMS/include/RmsData/PostIDReader
│           │   ├── POST /RMS/AspSoft/MasterName
│           │   │   └── query rnd=${vehicle_mn_rnd}; body MN_rnd=${vehicle_mn_rnd}
│           │   ├── GET /RMS/AspSoft/MasterName
│           │   │   └── plate_no=${plateNo}, MN_rnd=${vehicle_mn_rnd}, rnd=0.${__Random(100000000,999999999,request_rnd)}
│           │   ├── POST /RMS/AspSoft/MasterName
│           │   │   └── MN_rnd=${vehicle_mn_rnd}（Vehicle removesession）
│           │   ├── POST /RMS/aspsoft/EngineService/Dropdown
│           │   ├── POST /RMS/aspsoft/popupdispatcher
│           │   │   ├── query rnd=${vehicle_popup_rnd}; plate_no=${plateNo}, case_id=${case_id}
│           │   │   ├── __RequestVerificationToken=${vehicle_csrf}
│           │   │   └── doubleEntryTimeStamp=${vehicle_timestamp}
│           │   └── GET /RMS/Aspsoft/IntakeForm/middlepage
│           │       ├── handler=partialrefresh, rnd=0.${__Random(100000000,999999999,request_rnd)}
│           │       └── XPath Extractor: vehicle_master_object（vehicle/case_vehicle IDs）
│           │           只取同一 `<tr>` 中 plate_no 为 `${plateNo}` 的 master_id_list value
│           │           XPath: //tr[.//a[@objectname='plate_no' and normalize-space(.)='${plateNo}']]//input[@objectname='master_id_list']/@value
│           ├── Transaction Controller: Add PA charges
│           │   ├── GET /RMS/aspsoft/popupdispatcher
│           │   │   ├── rnd=${njs_popup_rnd}
│           │   │   ├── CSS Selector Extractor: njs_csrf
│           │   │   └── CSS Selector Extractor: njs_timestamp
│           │   ├── GET /RMS/Aspsoft/PopUpDispatcher
│           │   │   ├── charge=4；两个 rnd 分别内联生成 request_rnd_1/request_rnd_2
│           │   │   ├── Regular Expression Extractor: charge_1_candidate / Match 0
│           │   │   └── JSR223 PostProcessor: HTML/URL decode 后按 `~` 仅拆出 code/description
│           │   ├── GET /RMS/Aspsoft/PopUpDispatcher
│           │   │   ├── charge=3；两个 rnd 分别内联生成 request_rnd_1/request_rnd_2
│           │   │   ├── Regular Expression Extractor: charge_2_candidate / Match 0
│           │   │   └── JSR223 PostProcessor: HTML/URL decode 后按 `~` 仅拆出独立 code/description
│           │   ├── POST /RMS/aspsoft/popupdispatcher
│           │   │   ├── query rnd=${njs_popup_rnd}; 使用 charge_1_code/description 和 charge_2_code/description
│           │   │   ├── __RequestVerificationToken=${njs_csrf}
│           │   │   └── doubleEntryTimeStamp=${njs_timestamp}
│           │   └── GET /RMS/Aspsoft/IntakeForm/middlepage
│           │       ├── handler=partialrefresh, rnd=0.${__Random(100000000,999999999,request_rnd)}
│           │       ├── XPath Extractor: inv_njs_id_1
│           │       │   只取同一 `<tr>` 中 njs_code=${charge_1_code} 的 inv_njs_id value
│           │       │   XPath: //tr[.//span[@objectname='njs_code' and normalize-space(.)='${charge_1_code}']]//input[@objectname='inv_njs_id']/@value
│           │       └── XPath Extractor: inv_njs_id_2
│           │           只取同一 `<tr>` 中 njs_code=${charge_2_code} 的 inv_njs_id value
│           │           XPath: //tr[.//span[@objectname='njs_code' and normalize-space(.)='${charge_2_code}']]//input[@objectname='inv_njs_id']/@value
│           ├── Transaction Controller: Create report
│           │   ├── JSR223 PreProcessor: Build intake object graph
│           │   │   ├── 使用 contact_master_object、vehicle_master_object、inv_njs_id_1/_2、case_location_id、case_master_object、case_id
│           │   │   ├── 按捕获格式使用 STX (U+0002) / ETX (U+0003) 分隔对象
│           │   │   └── 生成 Base64 objects_parameter 和 objects_data_index
│           │   ├── POST /RMS/Aspsoft/IntakeForm/middlepage
│           │   │   ├── JSON Extractor: report_id
│           │   │   ├── JSON Assertion [Enabled]: CreateIntake Message OK
│           │   │   │   └── JSON Path=$.message; Expected Value=OK; Match as regular expression=false
│           │   │   └── JSON Assertion [Enabled]: CreateIntake Report ID Is Positive Integer
│           │   │       └── JSON Path=$.report_id; Expected Value=`^[1-9][0-9]*$`; Match as regular expression=true
│           │   └── GET /RMS/Aspsoft/IntakeForm/Intake
│           │       ├── report_id=${report_id}, rnd=0.${__Random(100000000,999999999,request_rnd)}
│           │       └── CSS Selector Extractor: intake_csrf
│           ├── Transaction Controller: Save incident report
│           │   └── POST /RMS/AspSoft/IntakeForm/Intake
│           │       ├── query action=auto_confirm, save_data=1, rnd=0.${__Random(100000000,999999999,request_rnd)}
│           │       ├── case_id=${case_id}, report_id=${report_id}
│           │       ├── hdnReportID=${report_id}, hdnCaseID=${case_id}
│           │       ├── narrative=${narrative}
│           │       ├── __RequestVerificationToken=${intake_csrf}
│           │       └── Response Assertion [Enabled]: Intake Auto Confirm Body WF
│           │           ├── Field to Test = Response Text
│           │           ├── Pattern Matching Rule = Matches
│           │           └── Pattern = `(?s)^\s*WF\s*$`
│           └── Transaction Controller: Submit workflow and refresh list
│               ├── GET /RMS/AspSoft/IntakeForm/IntakeReportAssignWorkflow
│               │   ├── report_ids=${report_id}；两个 rnd 分别内联生成 request_rnd_1/request_rnd_2
│               │   └── CSS Selector Extractor: workflow_csrf
│               ├── POST /RMS/AspSoft/IntakeForm/IntakeReportAssignWorkflow
│               │   └── nextStep=ROUTE1, reportIds=${report_id}
│               ├── POST /RMS/AspSoft/IntakeForm/IntakeReportAssignWorkflow
│               │   └── reportIds=${report_id}; 其余路由字段保留 SAZ 值
│               ├── POST /RMS/AspSoft/IntakeForm/IntakeReportAssignWorkflow
│               │   ├── multipart/form-data；保留原始 boundary 与 part 结构
│               │   ├── report_ids=${report_id}
│               │   └── __RequestVerificationToken=${workflow_csrf}
│               └── GET /RMS/Aspsoft/Dispatcher
│                   └── case_id=${case_id}, division_id=${division_id}
├── View Results Tree
│   └── 默认启用，仅用于单用户调试；正式负载测试前必须禁用
└── Simple Data Writer
    └── 默认禁用；正式负载测试前启用，写入轻量 JTL
```

Sampler 名称严格采用 `<METHOD> <实际路径>`；同路径的不同用途由所在 Transaction Controller、query/form 参数区分。阶段 2 若获批准，所有未在上树单独列出的 query、form、Body Data 和空字段均以对应 SAZ 会话为唯一来源，保留重复字段、顺序及编码；只替换本文明确声明的 CSV、随机值和前置响应变量。`Referer` 也必须引用本轮 `${case_id}`、`${form_guid}`、`${report_id}` 等变量，不能复制抓包中的固定 URL。

## 5. CSV 参数化

配套文件：`Output/pa40_incident_users.csv`

| CSV 列 | 使用位置 | 说明 |
|---|---|---|
| `username` | Login POST `LoginId` | 5 个独立、允许创建/提交报告的测试账号 |
| `password` | Login POST `Password` | 填写浏览器实际提交前的 Base64 文本；由 HTTP 参数编码处理 `%3D`，不要填 URL 编码后的重复值 |
| `staff_id` | Inbox `inbox_staff_id` | 必须与该行账号匹配 |
| `region_id` | InfoMapping 请求 `regionId` | 必须与该行账号/环境匹配 |

CSV 现含 5 行 `REPLACE_*` 数据槽。它不可用于真实执行，用户必须替换全部占位值。禁止把生产账号或明文凭据提交到版本库。

## 6. 动态参数、关联与静态值

### 每轮动态生成并复用

| 变量 | 生成位置 | 规则 | 复用请求 |
|---|---|---|---|
| `firstName` | 业务 Loop 起始 | `TEST${__Random(1000,9999)}` | 姓名搜索、Victim 保存 |
| `lastName` | 业务 Loop 起始 | `TEST${__Random(1000,9999)}` | 姓名搜索、Victim 保存 |
| `ssn` | 业务 Loop 起始 | `${__Random(100,999)}-${__Random(10,99)}-${__Random(1000,9999)}` | SSN 搜索、Victim 保存 |
| `plateNo` | 业务 Loop 起始 | `P` + 6 位随机数 | Vehicle 搜索、Vehicle 保存 |
| `narrative` | 业务 Loop 起始 | `TEST REPORT ${__threadNum}-${__time(yyyyMMddHHmmssSSS)}-${__Random(1000,9999)}` | Intake auto_confirm |
| `contact_name_mn_rnd` | 业务 Loop 起始 | `0.${__Random(100000000,999999999)}` | Victim 姓名 set/search/remove 会话组 |
| `contact_ssn_mn_rnd` | 业务 Loop 起始 | `0.${__Random(100000000,999999999)}` | Victim SSN set/search/remove 会话组 |
| `vehicle_mn_rnd` | 业务 Loop 起始 | `0.${__Random(100000000,999999999)}` | Vehicle set/search/remove 会话组 |
| `victim_popup_rnd` | 业务 Loop 起始 | `0.${__Random(100000000,999999999)}` | addCaseVW popup GET 与对应保存 POST |
| `vehicle_popup_rnd` | 业务 Loop 起始 | `0.${__Random(100000000,999999999)}` | addCaseVehicle popup GET 与对应保存 POST |
| `njs_popup_rnd` | 业务 Loop 起始 | `0.${__Random(100000000,999999999)}` | addCaseNJSCode popup GET 与对应保存 POST |
| `request_rnd` | 每个包含 `rnd` 的 Sampler 内联生成 | `rnd=0.${__Random(100000000,999999999,request_rnd)}` | 仅消费于当前 Sampler 的 `rnd` query；每次求值覆盖变量并得到新值 |

`request_rnd` 的消费请求为 Disclaimer.htm、MasterName search、三个 partial refresh、两个 PA charge list、Intake GET、auto_confirm 以及 Workflow GET。MasterName setsession 的 query `rnd` 必须复用本组 `*_mn_rnd`，三个 add popup 的打开 GET/保存 POST 必须复用本组 `*_popup_rnd`。捕获 URL 含两个同名 `rnd`（两个 PA charge list 与 Workflow GET）时，分别写为 `0.${__Random(100000000,999999999,request_rnd_1)}` 与 `0.${__Random(100000000,999999999,request_rnd_2)}`，两个值只在当前请求消费，不跨请求复用。

同一业务值不得在不同 Sampler 内重新调用随机函数，否则唯一性检查和最终保存值会不一致。

### 前置响应关联

- `login_csrf`：Login GET 的 `__RequestVerificationToken`。
- `disclaimer_csrf`：DisclaimerRedirect GET 的 `__RequestVerificationToken`。
- `mapping_key`：从每轮 `GET /RMS/inbox/list` 响应（SAZ 会话 11）中的 `sessionStorage.setItem("MappingKey", "...")` 以正则 `sessionStorage\.setItem\("MappingKey",\s*"([^"]+)"`、Match No. `1` 提取；它在 GeoCode 前已产生。Home 响应不作为来源，也不得复用抓包中的固定 key。
- `case_id`：Inbox 当前账号可见案件列表的候选值，Match No. `0` 随机选择。
- `report_list_csrf`、`report_list_timestamp`：Police Report 页面。
- `form_guid`：New Report POST 的 302 `Location` 响应头。
- `victim_csrf`/`victim_timestamp`、`vehicle_csrf`/`vehicle_timestamp`、`njs_csrf`/`njs_timestamp`：分别来自对应 popup GET。
- `contact_master_object`：联系人 partial refresh 返回的新 person/contact/location IDs。
- `vehicle_master_object`：车辆 partial refresh 返回的新 vehicle/case_vehicle IDs。
- `charge_1_code`/`charge_1_description`、`charge_2_code`/`charge_2_description`：两个 PA charge 候选页面各自随机选一项；必须保持角色分离。候选串中的 grade 未被保存请求消费，因此不输出 grade 变量。
- `inv_njs_id_1`、`inv_njs_id_2`：NJS partial refresh 返回的两条新 ID。
- `report_id`：CreateIntake JSON 响应的新报告 ID；后续 Intake、workflow、multipart Clear 全部复用。
- `intake_csrf`、`workflow_csrf`：分别来自 Intake 和 Workflow GET。

SAZ 中不存在 `__VIEWSTATE`、`__VIEWSTATEGENERATOR`、`__EVENTVALIDATION`，因此不生成这些提取器。

### CSRF 的 body/header 消费范围

以下 `RequestVerificationToken` 均使用前置 popup/page 提取的变量，禁止保留 SAZ 中的固定 token：

| 变量 | form/body 消费 | AJAX `RequestVerificationToken` header 消费 |
|---|---|---|
| `victim_csrf` | Victim 保存 `POST /RMS/aspsoft/popupdispatcher` 的 `__RequestVerificationToken` | 两个 Dropdown、IDReader、Victim name/SSN 的 setsession 与 removesession、GeoCode、GetMasterLocationChildren、GetCommonPlaces、municipality refresh、ALLCONTACT partial refresh |
| `vehicle_csrf` | Vehicle 保存 `POST /RMS/aspsoft/popupdispatcher` 的 `__RequestVerificationToken` | Vehicle Dropdown、IDReader、setsession、removesession、model Dropdown、Vehicle partial refresh |
| `njs_csrf` | NJS 保存 `POST /RMS/aspsoft/popupdispatcher` 的 `__RequestVerificationToken` | NJS partial refresh；两个普通导航型 charge list GET 按 SAZ 不带该 header |
| `intake_csrf` | Intake auto_confirm form 的 `__RequestVerificationToken` | 同一 auto_confirm AJAX 请求的 `RequestVerificationToken` header |
| `workflow_csrf` | Workflow Clear multipart part `__RequestVerificationToken` | ReportNextStepSelectedChanged 与 SaveWorkFlow 的 `RequestVerificationToken` header |

姓名/SSN/Vehicle 的普通导航型 MasterName search GET 按 SAZ 不带 `RequestVerificationToken` header；不能为它们臆造 header。

### 依规则保留的 SAZ 静态值

- `division_id=3`、`inbox_sub_id=10030101`、`template_id=1318`、`report_type=C`、`indicator_type=1`。
- Victim 地址选择结果：`6 ACORN BLVD, LANCASTER, PA 17602`，county `36`、municipality `36215`、longitude `-76.234123`、latitude `40.032795`、master location `19198`、country `US`、source `master`。
- Vehicle 描述字段保留捕获业务选择：state `PA`、year `2020`、make `AUDI`、model `5000`、body type `CONVERTIBLE`、color `BLACK`；仅 plate number 动态化。
- Workflow 路由值：`ROUTE1`、`PENDING`、`INTAKE_1LEVELGROUP`、`GROUP`、`OFFICER`。
- 空字段保持空，不为其创建无来源变量；不添加 JDBC 数据源。

Vehicle 保存 body 中 `person_id~|location_add~|A=1`、`person_id~|person_add~|A=1` 按用户批准保留捕获静态值 `1`，不得替换为 `${staff_id}` 或新增 CSV person ID。

### 特殊请求体

- CreateIntake 的 `objects_parameter` 与 `objects_data_index` 必须根据本轮对象 ID 重新组装，使用 U+0002/U+0003 控制字符保持捕获层级，再进行 Base64；不能复用抓包中的固定 Base64。
- Workflow Clear 必须保留 multipart boundary、`Content-Disposition`、空行和结尾 boundary，并替换 `report_ids`、`__RequestVerificationToken`。
- JSON 仅用于 CreateIntake 响应提取；捕获中的 JSON 请求体（ID Reader `{"a":1}`）使用 Body Data，不放到 Parameters。

## 7. 已批准并启用的断言

只生成以下三组业务断言，不增加 HTTP 200、Duration、popup 保存、SaveWorkFlow 或最终列表断言：

1. `GET /RMS/Home?division_id=${division_id}` 响应正文包含精确子串 `href="/RMS/Logout"`。该特征直接来自 SAZ 会话 09 的响应，并挂在实际产生它的 Home sampler。
2. CreateIntake 响应的 `$.message` 严格等于 `OK`，且 `$.report_id` 匹配正整数正则 `^[1-9][0-9]*$`。
3. Intake auto_confirm 响应正文匹配 `(?s)^\s*WF\s*$`，即去除首尾空白后严格等于 `WF`。

## 8. 执行前置条件与风险

1. 必须把 CSV 的 5 行占位值替换为 5 套独立、权限正确的测试账号数据；否则不具备执行条件。
2. 每个账号的 My Active Cases 必须至少有一条可用于新增 Incident Report 的案件；否则随机 `case_id` 无值并停止该线程。
3. 当前业务循环会真实创建并提交报告，需确认目标测试环境允许 5 用户持续 600 秒写入，并安排数据清理/隔离策略。
4. 随机姓名/SSN/车牌的取值空间有限，长时间或重复执行仍可能碰撞；若环境有严格唯一约束，应把规则扩展为线程号 + 时间戳。
5. 600 秒从线程组启动算起，包含 5 秒 ramp-up 和每线程首次登录；这会减少完整业务迭代可用的稳态时间。
6. Timer 已批准为每个业务请求 500～1500 ms；抓包人工操作间隔只作为存在用户停顿的证据，不逐请求复制。
7. 正式负载执行必须使用非 GUI 模式，禁用 View Results Tree，启用 Simple Data Writer，并单独设置结果目录。

## 9. 真实执行前仍需满足的外部前置条件

- 用 5 套真实且有权限的 `username/password/staff_id/region_id` 替换 CSV 中全部 `REPLACE_*` 占位值。
- 确认 5 个账号都适用 `division_id=3`；如环境实际配置不同，应另行修订已批准的数据模型。
- 确认每个账号至少有一条可写活动案件，且目标测试环境授权持续创建并提交报告。
- 确认数据隔离、报告保留和清理策略。

在上述外部条件补齐前，生成产物仅可做静态校验，不可真实执行。
