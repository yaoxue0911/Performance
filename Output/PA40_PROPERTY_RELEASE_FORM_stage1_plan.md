# PA40 Property Release Form — JMeter 阶段 1 测试计划

> 状态：用户已批准进入阶段 2。最终负载模型为 1 用户、1 秒 Ramp-up、600 秒持续时间、Forever Loop；批准加入第 9 节全部 4 组业务断言。尚未执行压力测试。

## 1. 输入与目标

- 输入文件：`Fiddler file/PA40_PROPERTY RELEASE FORM.saz`
- SAZ SHA-256：`b9a72382b71d9dbe3f967dd524b0c7ced609f4144c74c28d11c21ca2457d306e`
- 捕获规模：79 个 request、79 个 response、79 个 metadata 文件
- 目标：`https://parms42test.csitech.com:443`
- 最终并发数：1
- 场景类型：稳定负载
- Ramp-up：1 秒
- 持续时间：600 秒
- 循环：Scheduler 600 秒 + Forever Loop；认证每线程只执行一次，业务流持续循环
- 思考时间：业务 Loop 下放置 Uniform Random Timer，500–1500 ms

## 2. 流量筛选

### 2.1 保留

- 登录、免责声明接受、Home 初始化。
- Active Case Inbox、随机选择案件、Incident Summary、Police Report 列表、新建 Property Release Form。
- 联系人、车辆、财物、财物处置的弹窗、Dropdown、IDReader、MasterName 查重、保存及 partial refresh。
- CreateIntake、打开生成的报告、auto-confirm、返回 Police Report 列表。

### 2.2 排除或折叠

- 排除 CONNECT：SAZ 01、12、55–59。
- 排除静态资源：SAZ 11、28、54、60–75。
- 排除数量/状态类请求：SAZ 13、16、18、21、76、79。
- 排除只展示协议正文且不提供后续参数的 iframe：SAZ 07。
- `follow_redirects=true` 折叠显式重定向目标：SAZ 04–06 由 SAZ 03 覆盖，SAZ 09 由 SAZ 08 覆盖，SAZ 20 由 SAZ 19 覆盖。
- 计划保留 41 个 HTTP Sampler。

## 3. JMeter 树形架构

```text
Test Plan — PA40 Property Release Form
└── Thread Group — PA40 Property Release Form Stable Load
    ├── users = 1
    ├── ramp-up = 1s
    ├── duration = 600s
    ├── loop = forever，受 Scheduler 控制
    ├── CSV Data Set Config — pa40_property_release_users.csv
    ├── HTTP Request Defaults — https / parms42test.csitech.com / 443
    ├── HTTP Cookie Manager — clear_each_iteration=false
    ├── HTTP Cache Manager
    ├── Once Only Controller — Authentication and initialization
    │   └── Transaction Controller — Login and disclaimer
    │       ├── GET /RMS/Login
    │       ├── POST /RMS/Login
    │       ├── POST /RMS/DisclaimerRedirect
    │       └── GET /RMS/Home
    ├── Loop Controller — Property Release Form business flow
    │   ├── User Parameters — per-loop random values
    │   ├── Uniform Random Timer — 500–1500 ms
    │   ├── Transaction Controller — Select active case
    │   ├── Transaction Controller — Start new Property Release Form
    │   ├── Transaction Controller — Add contact
    │   ├── Transaction Controller — Add vehicle
    │   ├── Transaction Controller — Add property
    │   ├── Transaction Controller — Add property disposition
    │   ├── Transaction Controller — Create and save intake report
    │   └── Transaction Controller — Return to police-report list
    ├── View Results Tree — enabled for debugging
    └── Simple Data Writer — disabled for debugging
```

正式负载测试前必须禁用 View Results Tree，并启用 Simple Data Writer。

## 4. 请求头与请求体约定

- 每个 HTTP Request 都设置 `follow_redirects=true`。
- Cookie 不硬编码，由 HTTP Cookie Manager 管理。
- 浏览器指纹头（`sec-ch-ua*`、`Sec-Fetch-*`、压缩和浏览器版本）不作为业务依赖写入。
- 普通导航请求保留捕获语义所需的 `Referer`；跨请求含动态 ID/rnd 的 Referer 使用同一变量重建。首个 `GET /RMS/Login` 是明确例外：不发送 SAZ 02 中含旧 `case_id`/`FormGUID` 的捕获 Referer，因为这些变量在登录前尚不存在。
- 表单 POST 保留 `Content-Type: application/x-www-form-urlencoded`、`Origin` 和动态 `Referer`。
- AJAX 请求按捕获保留 `X-Requested-With: XMLHttpRequest` 和 `RequestVerificationToken`；token 从对应页面响应提取，禁止硬编码。
- 表格未展开的静态字段和空字段按 SAZ 原样保留；只替换下表明确标出的动态字段。
- SAZ 25、34 的 body 保持捕获语义 `{"a":1}`，使用 Body Data，不改造成普通表单参数；Content-Type 仍按捕获保留。

## 5. 计划 Sampler 与数据依赖

请求名称严格使用 `<METHOD> <实际路径>`；同路径的多个请求按所在 Transaction Controller 和执行顺序区分。

| # | SAZ | Transaction | 请求名称 | 动态输入、输出与说明 |
|---:|---:|---|---|---|
| 1 | 02 | Login and disclaimer | `GET /RMS/Login` | 提取 `login_csrf`（HTML hidden input，主响应）。 |
| 2 | 03 | Login and disclaimer | `POST /RMS/Login` | `${login_id}`、`${login_password_encoded}`、`${login_csrf}`；Follow Redirects 覆盖 04–06；从最终响应提取 `disclaimer_csrf`。 |
| 3 | 08 | Login and disclaimer | `POST /RMS/DisclaimerRedirect` | `handler=Jump`、`${disclaimer_csrf}`；Follow Redirects 覆盖 09。 |
| 4 | 10 | Login and disclaimer | `GET /RMS/Home` | `division_id=3`；提取 `staff_id` 与 `region_id`，供后续请求复用。 |
| 5 | 14 | Select active case | `GET /RMS/inbox/list` | `${staff_id}`；固定 `inbox_sub_id=10030101`；从 `input[name="case_id"]` 候选中 Match No. 0 随机提取 `${case_id}`。 |
| 6 | 15 | Select active case | `GET /RMS/AspSoft/Dispatcher` | `nextPID=inquireIncidentSummary`、`${case_id}`；从响应的 `PD Case #:` 文本提取 `${dept_case_no}`。 |
| 7 | 17 | Select active case | `GET /RMS/Aspsoft/Dispatcher` | `nextPID=listPoliceReport`、`${case_id}`、`division_id=3`；提取 `police_csrf`、`police_timestamp`。 |
| 8 | 19 | Start new form | `POST /RMS/Aspsoft/Dispatcher` | `${case_id}`、`template_id=2409`、`${police_csrf}`、`${police_timestamp}`；Follow Redirects 覆盖 20；从最终响应提取 `${FormGUID}`、`${middle_csrf}` 和 `${case_master_object}`，提取范围为 main sample and sub-samples。 |
| 9 | 22 | Add contact | `GET /RMS/aspsoft/popupdispatcher` | `nextPID=addCaseVW`、`${case_id}`、`${FormGUID}`、`${contact_popup_rnd}`；提取 `contact_csrf`、`contact_timestamp`。 |
| 10 | 23 | Add contact | `POST /RMS/aspsoft/EngineService/Dropdown` | 保留 `par=36@*addCaseVW@municipality@county`、rowID、parents；Referer 复用 `${contact_popup_rnd}`。 |
| 11 | 24 | Add contact | `POST /RMS/aspsoft/EngineService/Dropdown` | 保留 other-location dropdown 参数；Referer 复用 `${contact_popup_rnd}`。 |
| 12 | 25 | Add contact | `POST /RMS/include/RmsData/PostIDReader` | `action=IDREADEREABLE`；Body Data `{"a":1}`。 |
| 13 | 26 | Add contact | `POST /RMS/AspSoft/MasterName` | `action=setsession`，`${contact_mn_rnd}` 与捕获的 ToObjects/ToAliasObjects。 |
| 14 | 27 | Add contact | `GET /RMS/AspSoft/MasterName` | `${lastName}`、`${firstName}`，复用 `${contact_mn_rnd}` 做姓名查重。 |
| 15 | 29 | Add contact | `POST /RMS/AspSoft/MasterName` | `action=removesession`，复用 `${contact_mn_rnd}`。 |
| 16 | 30 | Add contact | `POST /RMS/aspsoft/popupdispatcher` | `${lastName}`、`${firstName}`、`${case_id}`、`${contact_csrf}`、`${contact_timestamp}`；其余非空/空字段按捕获保留。 |
| 17 | 31 | Add contact | `GET /RMS/Aspsoft/IntakeForm/middlepage` | `${case_id}`、`${FormGUID}`、`PartialRefresh_Ajax=listIntakeFormMaster_ALLCONTACT`、`${middle_csrf}` header；按 `${lastName}, ${firstName}` 所在行提取 `${contact_master_object}`。 |
| 18 | 32 | Add vehicle | `GET /RMS/aspsoft/popupdispatcher` | `nextPID=addCaseVehicle`、`${case_id}`、`${vehicle_popup_rnd}`；提取 `vehicle_csrf`、`vehicle_timestamp`。 |
| 19 | 33 | Add vehicle | `POST /RMS/aspsoft/EngineService/Dropdown` | 保留 county/municipality dropdown 参数。 |
| 20 | 34 | Add vehicle | `POST /RMS/include/RmsData/PostIDReader` | `action=IDREADEREABLE`；Body Data `{"a":1}`。 |
| 21 | 35 | Add vehicle | `POST /RMS/AspSoft/MasterName` | 第一次 `action=setsession`，`${vehicle_mn_rnd_1}`。 |
| 22 | 36 | Add vehicle | `GET /RMS/AspSoft/MasterName` | `${plateNo}`、空 vin，复用 `${vehicle_mn_rnd_1}`。 |
| 23 | 37 | Add vehicle | `POST /RMS/AspSoft/MasterName` | 第一次 `action=removesession`，复用 `${vehicle_mn_rnd_1}`。 |
| 24 | 38 | Add vehicle | `POST /RMS/aspsoft/EngineService/Dropdown` | 保留 `make=AUDI` 到 model 的联动参数。 |
| 25 | 39 | Add vehicle | `POST /RMS/AspSoft/MasterName` | 第二次 `action=setsession`，`${vehicle_mn_rnd_2}`。 |
| 26 | 40 | Add vehicle | `GET /RMS/AspSoft/MasterName` | `${plateNo}`、`${vinNo}`，复用 `${vehicle_mn_rnd_2}`。 |
| 27 | 41 | Add vehicle | `POST /RMS/AspSoft/MasterName` | 第二次 `action=removesession`，复用 `${vehicle_mn_rnd_2}`。 |
| 28 | 42 | Add vehicle | `POST /RMS/aspsoft/popupdispatcher` | `${plateNo}`、`${vinNo}`、`${case_id}`、`${vehicle_csrf}`、`${vehicle_timestamp}`；车辆其他字段保持捕获值。 |
| 29 | 43 | Add vehicle | `GET /RMS/Aspsoft/IntakeForm/middlepage` | `PartialRefresh_Ajax=listIntakeFormMaster_Vehicle`、`${FormGUID}`、`${middle_csrf}`；按 `${plateNo}` 所在行提取 `${vehicle_master_object}` 和 `${vehicle_id}`。 |
| 30 | 44 | Add property | `GET /RMS/aspsoft/popupdispatcher` | `nextPID=addCaseProperty`、`${case_id}`、`${property_popup_rnd}`；提取 `property_csrf`、`property_timestamp`。 |
| 31 | 45 | Add property | `POST /RMS/aspsoft/EngineService/Dropdown` | 保留 `property_type=VEHICLE` 的 subtype 联动参数。 |
| 32 | 46 | Add property | `GET /RMS/Include/CommonModule/Remote` | `action=CHECK_CASE_VEHICLE`、`${case_id}`、`${vehicle_id}`、`property_status=23`。 |
| 33 | 47 | Add property | `POST /RMS/aspsoft/popupdispatcher` | `${case_id}`、`${vehicle_id}`、`${property_csrf}`、`${property_timestamp}`；`value=3000`、`value_type=FAIR MARKET VALUE` 等保持捕获值。 |
| 34 | 48 | Add property | `GET /RMS/Aspsoft/IntakeForm/middlepage` | `PartialRefresh_Ajax=listIntakeFormMaster_Property`、`${FormGUID}`、`${middle_csrf}`；按包含 `${plateNo}` 的财物行提取 `${property_master_object}`。 |
| 35 | 49 | Add property disposition | `GET /RMS/Aspsoft/PopUpDispatcher` | `nextPID=addPropertyDispose_Intake`、`${case_id}`、`${disposition_popup_rnd}`；提取 `disposition_csrf`、`disposition_timestamp`。 |
| 36 | 50 | Add property disposition | `POST /RMS/Aspsoft/PopUpDispatcher` | `${releaseDate}`、`${case_id}`、`${disposition_csrf}`、`${disposition_timestamp}`；`DispositionStatus=Complete`。 |
| 37 | 51 | Add property disposition | `GET /RMS/Aspsoft/IntakeForm/middlepage` | `PartialRefresh_Ajax=listIntakeFormMaster_PropertyDispose`、`${FormGUID}`、`${middle_csrf}`；从本轮新增的 Complete 行提取 `${disposition_master_object}`。 |
| 38 | 52 | Create and save report | `POST /RMS/Aspsoft/IntakeForm/middlepage` | `${case_id}`、`${FormGUID}`、`${middle_csrf}`；使用必要的 JSR223 PreProcessor 从五个 master object 重建并 Base64 编码 `objects_parameter`/`objects_data_index`；JSON 提取 `${report_id}`。 |
| 39 | 53 | Create and save report | `GET /RMS/Aspsoft/IntakeForm/Intake` | `${case_id}`、`${report_id}`、`${intake_page_rnd}`；提取 `${intake_csrf}`。 |
| 40 | 77 | Create and save report | `POST /RMS/AspSoft/IntakeForm/Intake` | `action=auto_confirm`；header/body token=`${intake_csrf}`；`INV_HEADER_DEPT_CASENO=${dept_case_no}`、`hdnCaseID=${case_id}`、`hdnReportID=${report_id}`、`ORG_IMAGE=/AspSoft/ImageHandler?image_code=AGENCY_LOGO&smalllogo=1&region_id=${region_id}&type=clearimage`、`releasedtowner=${releaseDate}`；Referer 使用完整 Intake URL 并复用 `${case_id}`、`${report_id}`、`${intake_page_rnd}`。禁止保留捕获的案件号、case/report ID 或 region ID。 |
| 41 | 78 | Return to list | `GET /RMS/Aspsoft/Dispatcher` | `nextPID=listPoliceReport`、`${case_id}`、`report_workflow_type=INTAKE`、`division_id=3`。 |

### 5.1 Token 与 Referer 的逐请求映射

以下模板中的 host/protocol 由 HTTP Request Defaults 提供；这里列出的路径作为完整动态 Referer 写入。未列 token 的请求不发送 `RequestVerificationToken` header。表单 body 中的 `__RequestVerificationToken` 仍按第 5 节相应 popup/page token 填写。

| SAZ / Sampler | Header token | Referer |
|---|---|---|
| 02 / 1 | 无 | 不发送 Referer；明确丢弃捕获中的旧 case/GUID Referer。 |
| 03 / 2 | 无；body `${login_csrf}` | `/RMS/Login` |
| 08 / 3 | 无；body `${disclaimer_csrf}` | `/RMS/DisclaimerRedirect?division_id=3` |
| 10 / 4 | 无 | POST Disclaimer redirect chain 的最终 `/RMS` 页面语义；无需旧业务 ID。 |
| 14 / 5 | 无 | `/RMS/Home?division_id=3` |
| 15 / 6 | 无 | `/RMS/inbox/list?nextPID=listInbox_MyActiveCase&inbox_staff_id=${staff_id}&inbox_sub_id=10030101&UseDefault=1&is_temp_page_size=1&page_size=100` |
| 17 / 7 | 无 | `/RMS/AspSoft/Dispatcher?nextPID=inquireIncidentSummary&case_id=${case_id}` |
| 19 / 8 | 无；body `${police_csrf}` | `/RMS/Aspsoft/Dispatcher?nextPID=listPoliceReport&case_id=${case_id}&division_id=3&report_type=C&indicator_type=1` |
| 22 / 9 | 无 | `/RMS/Aspsoft/IntakeForm/middlepage?nextPID=intakeFormMiddelPage&template_id=2409&report_id=0&case_id=${case_id}&PID=listPoliceReport&FormGUID=${FormGUID}` |
| 23–26 / 10–13 | `RequestVerificationToken: ${contact_csrf}` | `/RMS/aspsoft/popupdispatcher?nextPID=addCaseVW&case_id=${case_id}&PartialRefresh=listIntakeFormMaster_ALLCONTACT&template_id=2409&report_id=0&rnd=${contact_popup_rnd}` |
| 27 / 14 | 无 | middlepage Referer（`${case_id}`、`${FormGUID}`，模板同 SAZ 22）。 |
| 29 / 15 | `RequestVerificationToken: ${contact_csrf}` | Contact popup Referer（`${case_id}`、`${contact_popup_rnd}`）。 |
| 30 / 16 | 无 header；body `${contact_csrf}` | Contact popup Referer（`${case_id}`、`${contact_popup_rnd}`）。 |
| 31 / 17 | `RequestVerificationToken: ${middle_csrf}` | middlepage Referer（`${case_id}`、`${FormGUID}`）。 |
| 32 / 18 | 无 | middlepage Referer（`${case_id}`、`${FormGUID}`）。 |
| 33–35 / 19–21 | `RequestVerificationToken: ${vehicle_csrf}` | `/RMS/aspsoft/popupdispatcher?nextPID=addCaseVehicle&case_id=${case_id}&PartialRefresh=listIntakeFormMaster_Vehicle&template_id=2409&report_id=0&rnd=${vehicle_popup_rnd}` |
| 36 / 22 | 无 | middlepage Referer（`${case_id}`、`${FormGUID}`）。 |
| 37–39 / 23–25 | `RequestVerificationToken: ${vehicle_csrf}` | Vehicle popup Referer（`${case_id}`、`${vehicle_popup_rnd}`）。 |
| 40 / 26 | 无 | middlepage Referer（`${case_id}`、`${FormGUID}`）。 |
| 41 / 27 | `RequestVerificationToken: ${vehicle_csrf}` | Vehicle popup Referer（`${case_id}`、`${vehicle_popup_rnd}`）。 |
| 42 / 28 | 无 header；body `${vehicle_csrf}` | Vehicle popup Referer（`${case_id}`、`${vehicle_popup_rnd}`）。 |
| 43 / 29 | `RequestVerificationToken: ${middle_csrf}` | middlepage Referer（`${case_id}`、`${FormGUID}`）。 |
| 44 / 30 | 无 | middlepage Referer（`${case_id}`、`${FormGUID}`）。 |
| 45–46 / 31–32 | `RequestVerificationToken: ${property_csrf}` | `/RMS/aspsoft/popupdispatcher?nextPID=addCaseProperty&case_id=${case_id}&PartialRefresh=listIntakeFormMaster_Property&template_id=2409&report_id=0&rnd=${property_popup_rnd}` |
| 47 / 33 | 无 header；body `${property_csrf}` | Property popup Referer（`${case_id}`、`${property_popup_rnd}`）。 |
| 48 / 34 | `RequestVerificationToken: ${middle_csrf}` | middlepage Referer（`${case_id}`、`${FormGUID}`）。 |
| 49 / 35 | 无 | middlepage Referer（`${case_id}`、`${FormGUID}`）。 |
| 50 / 36 | 无 header；body `${disposition_csrf}` | `/RMS/Aspsoft/PopUpDispatcher?nextPID=addPropertyDispose_Intake&case_id=${case_id}&PartialRefresh=listIntakeFormMaster_PropertyDispose&template_id=2409&report_id=0&rnd=${disposition_popup_rnd}` |
| 51–52 / 37–38 | `RequestVerificationToken: ${middle_csrf}` | middlepage Referer（`${case_id}`、`${FormGUID}`）。 |
| 53 / 39 | 无 | middlepage Referer（`${case_id}`、`${FormGUID}`）。 |
| 77 / 40 | `RequestVerificationToken: ${intake_csrf}`；body 同值 | `/RMS/Aspsoft/IntakeForm/Intake?nextPID=listPoliceReport&MPID=intakeFormMiddelPage&case_id=${case_id}&template_id=2409&report_id=${report_id}&rnd=${intake_page_rnd}` |
| 78 / 41 | 无 | 与 SAZ 77 相同的完整 Intake Referer。 |

## 6. 参数化设计

### 6.1 CSV Data Set

文件：`pa40_property_release_users.csv`

```csv
login_id,login_password_encoded
```

CSV 当前只有表头，不包含抓包中的凭据。请补充至少 1 行可用的测试账号。Password 列必须填写登录 POST 所期望的已编码值，而不是未经前端处理的明文密码。

CSV 配置：`ignoreFirstLine=true`、`recycle=true`、`stopThread=false`、`sharingMode=shareMode.all`。单线程持续循环时复用同一行凭据；登录仍只执行一次。

### 6.2 每轮生成的变量

这些变量放在业务 Loop Controller 内的 User Parameters 中，每轮生成一次并在所有相关请求中复用：

| 变量 | 建议规则 | 使用位置 |
|---|---|---|
| `firstName` | `TEST${__Random(1000,9999,)}` | 姓名查重、联系人保存、联系人刷新行定位 |
| `lastName` | `TEST${__Random(1000,9999,)}` | 姓名查重、联系人保存、联系人刷新行定位 |
| `plateNo` | `P${__Random(100000,999999,)}` | 两次车辆查重、车辆保存、车辆/财物刷新行定位 |
| `vinNo` | `W${__RandomString(15,0123456789,)}` | 第二次车辆查重、车辆保存；保持捕获的 16 字符格式 |
| `releaseDate` | `${__time(MM/dd/yyyy,)}` | disposition 保存、auto-confirm |
| `contact_popup_rnd` | `0.${__Random(100000000,999999999,)}` | Contact popup GET/POST 与 Referer |
| `contact_mn_rnd` | `0.${__Random(100000000,999999999,)}` | Contact set/search/remove session |
| `vehicle_popup_rnd` | `0.${__Random(100000000,999999999,)}` | Vehicle popup GET/POST 与 Referer |
| `vehicle_mn_rnd_1` | `0.${__Random(100000000,999999999,)}` | 第一组 vehicle set/search/remove |
| `vehicle_mn_rnd_2` | `0.${__Random(100000000,999999999,)}` | 第二组 vehicle set/search/remove |
| `property_popup_rnd` | `0.${__Random(100000000,999999999,)}` | Property popup GET/POST 与 Referer |
| `disposition_popup_rnd` | `0.${__Random(100000000,999999999,)}` | Disposition popup GET/POST 与 Referer |
| `intake_page_rnd` | `0.${__Random(100000000,999999999,)}` | Intake GET 与 auto-confirm Referer |

只出现一次且无复用要求的其他 `rnd` 可在对应请求中内联生成。捕获中的 SSN 和 Driver License 为空，因此不凭空生成这两个值。

### 6.3 静态值

- `division_id=3`、`inbox_sub_id=10030101`、`template_id=2409`、`report_type=C`、`indicator_type=1`。
- 联系人静态业务值包括 DOB `05/05/1998`、sex `M`、race `A`、ethnicity `H`、state `PA`、county `36` 等。
- 车辆静态业务值包括 state `PA`、year `2020`、make `AUDI`、model `2000 TT-COUPE`、body type `4 DOOR`、color `BLACK` 等。
- 财物静态业务值包括 type `VEHICLE`、status `23`、value `3000`、value type `FAIR MARKET VALUE`。
- 报告静态业务值包括 narrative `test note`、template code `RMS_PROPERTYRELEASEFORM`、disposition status `Complete`。

auto-confirm 中的 `INV_HEADER_DEPT_CASENO`、`hdnCaseID`、`hdnReportID` 和 `ORG_IMAGE` 内嵌 region ID 明确属于动态字段，不在上述静态保留范围内，分别使用 `${dept_case_no}`、`${case_id}`、`${report_id}`、`${region_id}`。

以上字段在 SAZ 中没有可靠的更高优先级动态来源；用户可在审批时要求改成 CSV 或其他取值。

## 7. 关联与提取器作用域

| 来源 | 变量 | 提取方式与范围 |
|---|---|---|
| GET Login | `login_csrf` | CSS：`input[name="__RequestVerificationToken"]` 的 `value`；main sample。 |
| POST Login 的重定向最终页 | `disclaimer_csrf` | CSS hidden token；main sample and sub-samples，以覆盖 redirect chain 的最终响应。 |
| GET Home | `staff_id`, `region_id` | 从 Home HTML 的 Inbox URL 与 ImageHandler URL 提取；main sample。 |
| GET Inbox | `case_id` | CSS：`input[name="case_id"]` 的 `value`，Match No. 0 随机候选；main sample。 |
| GET Incident Summary | `dept_case_no` | Boundary/正则提取 `PD Case #:` 后的案件编号；该响应由已选 `${case_id}` 打开，因此与随机案件保持同一行语义。 |
| GET Police Report list | `police_csrf`, `police_timestamp` | CSS hidden token/timestamp；main sample。 |
| POST New Report 的 redirect chain | `FormGUID`, `middle_csrf`, `case_master_object` | 最终 middlepage 的 CurrentRequestUrl、CSRF meta/hidden input、包含 `case_id#${case_id}` 的 `master_id_list`；main sample and sub-samples。 |
| 各 popup GET | `<scope>_csrf`, `<scope>_timestamp` | 各 popup 自己的 CSRF 与 `doubleEntryTimeStamp`；只供同一 popup POST/关联请求使用。 |
| Contact partial refresh | `contact_master_object` | XPath/CSS 先定位文本 `${lastName}, ${firstName}` 的行，再取该行 `master_id_list`。 |
| Vehicle partial refresh | `vehicle_master_object`, `vehicle_id` | 按 `${plateNo}` 所在行提取，不使用捕获 ID。 |
| Property partial refresh | `property_master_object` | 按包含 `${plateNo}` 的 property category 行提取。 |
| Disposition partial refresh | `disposition_master_object` | XPath 同时限定本轮 `${releaseDate}` 和 `COMPLETE` 状态，并选择响应排序中的第一个（最新）匹配行。 |
| CreateIntake JSON | `report_id` | JSON Extractor：`$.report_id`；只供后续 Intake 请求使用。 |
| GET Intake | `intake_csrf` | Intake 页面 CSRF；只供 auto-confirm 使用。 |

各 token 按页面作用域分别命名，不能用一个全局 token 覆盖。所有跟随重定向请求的提取器必须覆盖最终响应；其他提取器只检查直接响应，避免从错误的 Referer 页面取值。

## 8. CreateIntake 特殊编码

SAZ 52 的 `objects_parameter` 和 `objects_data_index` 内含本轮创建的对象 ID，不能使用捕获的 Base64 常量。

- 从 `${contact_master_object}`、`${vehicle_master_object}`、`${property_master_object}`、`${disposition_master_object}`、`${case_master_object}` 重建业务字符串。
- `objects_parameter` 的五个对象组使用 ETX（U+0003）连接。
- `objects_data_index` 的五个对象组使用 STX（U+0002）连接，并由各 master object 中解析出 person/vehicle/property/disposition/case ID 组成索引前缀。
- 在 SAZ 52 HTTP Request 之前使用一个必要的 Groovy JSR223 PreProcessor 完成解析、拼接和 Base64；开启编译缓存，变量通过 `vars.get(...)` 读取。
- 该 PreProcessor 无法用单个 XPath/CSS Extractor替代，因为它需要跨五个响应组合数据、插入控制字符并 Base64 编码；不得将其用于候选随机选择或普通字段提取。

## 9. 已批准的 3 组业务断言

用户最终批准保留以下 3 组断言；阶段 2 生成 4 个 Assertion 节点（第 2 组含两个节点）：

- 第 1 组：Login 后 GET Home 响应包含 `/RMS/Logout`。
- 第 2 组：CreateIntake JSON 的 `message` 等于 `OK`；`report_id` 匹配正整数。
- 第 3 组：auto-confirm 响应正文匹配 `(?s)^\s*OK\s*$`。

用户明确决定删除最终 Police Report 列表出现本轮报告的断言，不使用替代断言。

不会添加仅检查 HTTP 200 的断言。

## 10. 压测风险与运行前置条件

- 该流程会在测试环境创建真实 person、vehicle、property、disposition 和 report 数据。
- 当前只有 1 个线程，但 Forever Loop 会持续创建数据；同一案件多轮产生相似对象时，“最新行”关联必须始终按本轮随机姓名、车牌和日期定位。
- 每个账号必须拥有 template 2409 和目标案件的新增/保存权限。
- Inbox 无候选、任一 master object 未提取或 CreateIntake 未返回正整数 report ID 时，线程应停止或明确失败，禁止退回捕获的旧 ID。
- 当前提议的随机姓名/车牌/VIN 仍有极低碰撞概率；如环境有严格格式校验，请在审批时提供允许的数据规则。

## 11. 阶段 2 批准状态与运行前置条件

已批准：1 用户、1 秒 Ramp-up、600 秒、Forever Loop、500–1500 ms 思考时间、动态姓名/车牌/VIN/日期，以及第 9 节全部 4 组业务断言。

运行前仍必须：

1. 用户向 `pa40_property_release_users.csv` 补充至少 1 行有效账号和已编码密码。
2. 确认测试环境允许持续创建 person、vehicle、property、disposition 和 report 数据。
3. 正式负载运行前禁用 View Results Tree、启用 Simple Data Writer。
