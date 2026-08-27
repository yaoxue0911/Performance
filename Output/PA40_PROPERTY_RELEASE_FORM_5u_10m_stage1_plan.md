# PA40 Property Release Form — JMeter 阶段 1 测试计划

> 状态：用户已于 2026-08-26 明确批准生成 JMX；JMX 已生成并通过离线结构验收，尚未执行负载测试。

## 1. 输入与负载目标

- 输入文件：`Fiddler file/PA40_PROPERTY RELEASE FORM.saz`
- SAZ SHA-256：`b9a72382b71d9dbe3f967dd524b0c7ced609f4144c74c28d11c21ca2457d306e`
- 捕获规模：79 个 request、79 个 response、79 个 metadata 文件
- 目标：`https://parms42test.csitech.com:443`
- 场景类型：稳定负载
- 并发用户数：5
- Ramp-up：5 秒，约每秒启动 1 个用户
- 持续时间：600 秒
- 循环：认证和初始化每线程执行一次；业务流程在 Scheduler 结束前持续循环
- 思考时间：业务 Loop 下放置 Uniform Random Timer，500–1500 ms

## 2. 抓包筛选结果

### 2.1 保留的业务流量

- 登录、免责声明接受和 Home 初始化。
- Active Case Inbox、随机选择案件、Incident Summary、Police Report 列表和新建 Property Release Form。
- 联系人、车辆、财物、财物处置的弹窗、Dropdown、IDReader、MasterName 查重、保存和 partial refresh。
- CreateIntake、打开生成的报告、auto-confirm 和返回 Police Report 列表。

### 2.2 排除或折叠的流量

- 排除 CONNECT：SAZ 01、12、55–59。
- 排除静态资源：SAZ 11、28、54、60–75。
- 排除数量、Tab 计数或状态请求：SAZ 13、16、18、21、76、79。
- 排除只展示协议正文且不为后续请求提供参数的 iframe：SAZ 07。
- 使用 `follow_redirects=true` 折叠显式重定向目标：SAZ 04–06 由 SAZ 03 覆盖，SAZ 09 由 SAZ 08 覆盖，SAZ 20 由 SAZ 19 覆盖。
- 最终保留 41 个 HTTP Sampler。

## 3. JMeter 测试树预览

```text
Test Plan — PA40 Property Release Form
└── Thread Group — PA40 Property Release Form Stable Load
    ├── users = 5
    ├── ramp-up = 5s
    ├── duration = 600s
    ├── thread-group loop = 1，Scheduler 控制最长运行时间
    ├── CSV Data Set Config — pa40_property_release_users.csv
    ├── HTTP Request Defaults — https / parms42test.csitech.com / 443
    ├── HTTP Cookie Manager — clear_each_iteration=false
    ├── HTTP Cache Manager
    ├── Once Only Controller — Authentication and initialization
    │   └── Transaction Controller — Login and disclaimer
    │       ├── GET /RMS/Login — Load login page
    │       ├── POST /RMS/Login — Authenticate user
    │       ├── POST /RMS/DisclaimerRedirect — Accept disclaimer
    │       └── GET /RMS/Home — Initialize authenticated home
    ├── Loop Controller — Property Release Form business flow (forever)
    │   ├── User Parameters — Generate per-loop values
    │   ├── Uniform Random Timer — 500–1500 ms
    │   ├── Transaction Controller — Select active case
    │   ├── Transaction Controller — Start new Property Release Form
    │   ├── Transaction Controller — Add contact
    │   ├── Transaction Controller — Add vehicle
    │   ├── Transaction Controller — Add property
    │   ├── Transaction Controller — Add property disposition
    │   ├── Transaction Controller — Create and save intake report
    │   └── Transaction Controller — Return to police-report list
    ├── View Results Tree — enabled for debugging only
    └── Simple Data Writer — disabled for debugging
```

正式负载测试前必须禁用 View Results Tree，并启用 Simple Data Writer。

## 4. 通用请求规则

- 每个 HTTP Request 设置 `follow_redirects=true`。
- 全部忽略 `Referer` 请求头；计划、Scenario JSON 和 JMX 均不生成或重建 Referer。
- Cookie 不硬编码，由 HTTP Cookie Manager 管理。
- 不保留 `Authorization`、抓包 Cookie、旧 CSRF token 或其他会话凭据。
- 浏览器指纹头（`sec-ch-ua*`、`Sec-Fetch-*`、压缩和浏览器版本）不作为业务依赖写入。
- 表单 POST 按捕获保留必要的 `Content-Type` 和 `Origin`。
- AJAX 请求按捕获保留 `X-Requested-With: XMLHttpRequest` 和 `RequestVerificationToken`；token 从对应页面响应提取，不硬编码。
- 未单独展开的静态字段和空字段按 SAZ 原始业务语义保留，只替换本计划明确列出的动态字段。
- SAZ 25、34 的 body 保持捕获语义 `{"a":1}`，使用 Body Data，不转换为普通表单参数。

## 5. Sampler 与数据依赖

请求名称使用 `<METHOD> <实际路径> <用途>`，同路径请求由用途和所属 Transaction 区分。

| # | SAZ | Transaction | 请求名称 | 动态输入、输出与说明 |
|---:|---:|---|---|---|
| 1 | 02 | Login and disclaimer | `GET /RMS/Login Load login page` | 提取 `${login_csrf}`。 |
| 2 | 03 | Login and disclaimer | `POST /RMS/Login Authenticate user` | 使用 `${login_id}`、`${login_password_encoded}`、`${login_csrf}`；重定向覆盖 04–06；从最终响应提取 `${disclaimer_csrf}`。 |
| 3 | 08 | Login and disclaimer | `POST /RMS/DisclaimerRedirect Accept disclaimer` | `handler=Jump`、`${disclaimer_csrf}`；重定向覆盖 09。 |
| 4 | 10 | Login and disclaimer | `GET /RMS/Home Initialize authenticated home` | `division_id=3`；提取 `${staff_id}` 和 `${region_id}`。 |
| 5 | 14 | Select active case | `GET /RMS/inbox/list Load active cases` | `${staff_id}`、固定 `inbox_sub_id=10030101`；随机提取 `${case_id}`。 |
| 6 | 15 | Select active case | `GET /RMS/AspSoft/Dispatcher Open incident summary` | `nextPID=inquireIncidentSummary`、`${case_id}`；提取 `${dept_case_no}`。 |
| 7 | 17 | Select active case | `GET /RMS/Aspsoft/Dispatcher Load police reports` | `nextPID=listPoliceReport`、`${case_id}`、`division_id=3`；提取 `${police_csrf}`、`${police_timestamp}`。 |
| 8 | 19 | Start new form | `POST /RMS/Aspsoft/Dispatcher Start property release form` | `${case_id}`、`template_id=2409`、`${police_csrf}`、`${police_timestamp}`；重定向覆盖 20；从最终响应提取 `${FormGUID}`、`${middle_csrf}`、`${case_master_object}`。 |
| 9 | 22 | Add contact | `GET /RMS/aspsoft/popupdispatcher Open contact form` | `${case_id}`、`${FormGUID}`、`${contact_popup_rnd}`；提取 `${contact_csrf}`、`${contact_timestamp}`。 |
| 10 | 23 | Add contact | `POST /RMS/aspsoft/EngineService/Dropdown Load contact municipality` | 保留捕获的 `par`、rowID 和 parents；header token 使用 `${contact_csrf}`。 |
| 11 | 24 | Add contact | `POST /RMS/aspsoft/EngineService/Dropdown Load contact location` | 保留 other-location dropdown 参数；header token 使用 `${contact_csrf}`。 |
| 12 | 25 | Add contact | `POST /RMS/include/RmsData/PostIDReader Initialize contact ID reader` | `action=IDREADEREABLE`；Body Data `{"a":1}`；header token 使用 `${contact_csrf}`。 |
| 13 | 26 | Add contact | `POST /RMS/AspSoft/MasterName Start contact lookup session` | `action=setsession`、`${contact_mn_rnd}` 和捕获的对象映射；header token 使用 `${contact_csrf}`。 |
| 14 | 27 | Add contact | `GET /RMS/AspSoft/MasterName Check contact uniqueness` | `${lastName}`、`${firstName}`，复用 `${contact_mn_rnd}`。 |
| 15 | 29 | Add contact | `POST /RMS/AspSoft/MasterName End contact lookup session` | `action=removesession`，复用 `${contact_mn_rnd}`；header token 使用 `${contact_csrf}`。 |
| 16 | 30 | Add contact | `POST /RMS/aspsoft/popupdispatcher Save contact` | `${lastName}`、`${firstName}`、`${case_id}`、`${contact_csrf}`、`${contact_timestamp}`。 |
| 17 | 31 | Add contact | `GET /RMS/Aspsoft/IntakeForm/middlepage Refresh contacts` | `${case_id}`、`${FormGUID}`、`${middle_csrf}`；按本轮姓名所在行提取 `${contact_master_object}`。 |
| 18 | 32 | Add vehicle | `GET /RMS/aspsoft/popupdispatcher Open vehicle form` | `${case_id}`、`${vehicle_popup_rnd}`；提取 `${vehicle_csrf}`、`${vehicle_timestamp}`。 |
| 19 | 33 | Add vehicle | `POST /RMS/aspsoft/EngineService/Dropdown Load vehicle location` | 保留 county/municipality 参数；header token 使用 `${vehicle_csrf}`。 |
| 20 | 34 | Add vehicle | `POST /RMS/include/RmsData/PostIDReader Initialize vehicle ID reader` | Body Data `{"a":1}`；header token 使用 `${vehicle_csrf}`。 |
| 21 | 35 | Add vehicle | `POST /RMS/AspSoft/MasterName Start plate lookup session` | `action=setsession`，`${vehicle_mn_rnd_1}`；header token 使用 `${vehicle_csrf}`。 |
| 22 | 36 | Add vehicle | `GET /RMS/AspSoft/MasterName Check plate uniqueness` | `${plateNo}`、空 VIN，复用 `${vehicle_mn_rnd_1}`。 |
| 23 | 37 | Add vehicle | `POST /RMS/AspSoft/MasterName End plate lookup session` | 复用 `${vehicle_mn_rnd_1}`；header token 使用 `${vehicle_csrf}`。 |
| 24 | 38 | Add vehicle | `POST /RMS/aspsoft/EngineService/Dropdown Load vehicle model` | 保留 `make=AUDI` 到 model 的联动参数；header token 使用 `${vehicle_csrf}`。 |
| 25 | 39 | Add vehicle | `POST /RMS/AspSoft/MasterName Start VIN lookup session` | `action=setsession`，`${vehicle_mn_rnd_2}`；header token 使用 `${vehicle_csrf}`。 |
| 26 | 40 | Add vehicle | `GET /RMS/AspSoft/MasterName Check vehicle uniqueness` | `${plateNo}`、`${vinNo}`，复用 `${vehicle_mn_rnd_2}`。 |
| 27 | 41 | Add vehicle | `POST /RMS/AspSoft/MasterName End VIN lookup session` | 复用 `${vehicle_mn_rnd_2}`；header token 使用 `${vehicle_csrf}`。 |
| 28 | 42 | Add vehicle | `POST /RMS/aspsoft/popupdispatcher Save vehicle` | `${plateNo}`、`${vinNo}`、`${case_id}`、`${vehicle_csrf}`、`${vehicle_timestamp}`。 |
| 29 | 43 | Add vehicle | `GET /RMS/Aspsoft/IntakeForm/middlepage Refresh vehicles` | `${FormGUID}`、`${middle_csrf}`；按 `${plateNo}` 所在行提取 `${vehicle_master_object}` 和 `${vehicle_id}`。 |
| 30 | 44 | Add property | `GET /RMS/aspsoft/popupdispatcher Open property form` | `${case_id}`、`${property_popup_rnd}`；提取 `${property_csrf}`、`${property_timestamp}`。 |
| 31 | 45 | Add property | `POST /RMS/aspsoft/EngineService/Dropdown Load property subtype` | 保留 `property_type=VEHICLE` 的联动参数；header token 使用 `${property_csrf}`。 |
| 32 | 46 | Add property | `GET /RMS/Include/CommonModule/Remote Validate case vehicle` | `${case_id}`、`${vehicle_id}`、`property_status=23`；header token 使用 `${property_csrf}`。 |
| 33 | 47 | Add property | `POST /RMS/aspsoft/popupdispatcher Save property` | `${case_id}`、`${vehicle_id}`、`${property_csrf}`、`${property_timestamp}`；价值字段保持捕获值。 |
| 34 | 48 | Add property | `GET /RMS/Aspsoft/IntakeForm/middlepage Refresh properties` | `${FormGUID}`、`${middle_csrf}`；按包含 `${plateNo}` 的财物行提取 `${property_master_object}`。 |
| 35 | 49 | Add property disposition | `GET /RMS/Aspsoft/PopUpDispatcher Open disposition form` | `${case_id}`、`${disposition_popup_rnd}`；提取 `${disposition_csrf}`、`${disposition_timestamp}`。 |
| 36 | 50 | Add property disposition | `POST /RMS/Aspsoft/PopUpDispatcher Save disposition` | `${releaseDate}`、`${case_id}`、`${disposition_csrf}`、`${disposition_timestamp}`；`DispositionStatus=Complete`。 |
| 37 | 51 | Add property disposition | `GET /RMS/Aspsoft/IntakeForm/middlepage Refresh dispositions` | `${FormGUID}`、`${middle_csrf}`；提取本轮 `${disposition_master_object}`。 |
| 38 | 52 | Create and save report | `POST /RMS/Aspsoft/IntakeForm/middlepage Create intake report` | `${case_id}`、`${FormGUID}`、`${middle_csrf}`；动态重建并编码对象字段；JSON 提取 `${report_id}`。 |
| 39 | 53 | Create and save report | `GET /RMS/Aspsoft/IntakeForm/Intake Open created report` | `${case_id}`、`${report_id}`、`${intake_page_rnd}`；提取 `${intake_csrf}`。 |
| 40 | 77 | Create and save report | `POST /RMS/AspSoft/IntakeForm/Intake Confirm intake report` | body/header token 使用 `${intake_csrf}`；动态使用 `${dept_case_no}`、`${case_id}`、`${report_id}`、`${region_id}`、`${releaseDate}`。 |
| 41 | 78 | Return to list | `GET /RMS/Aspsoft/Dispatcher Return to police reports` | `${case_id}`、`report_workflow_type=INTAKE`、`division_id=3`。 |

## 6. 参数化设计

### 6.1 CSV Data Set

JMX 同级文件：`pa40_property_release_users.csv`

```csv
login_id,login_password_encoded
```

- 不复制 SAZ 中捕获的凭据；由用户填写 5 行不同的有效测试账号。
- `login_password_encoded` 必须是登录 POST 需要的前端编码值，不是明文密码。
- 建议配置：`ignoreFirstLine=true`、`recycle=false`、`stopThread=true`、`sharingMode=shareMode.all`。
- CSV 位于 Thread Group 作用域，Thread Group 只迭代一次，因此每线程读取一行并在该线程生命周期内复用。
- 少于 5 行有效数据时停止缺少账号的线程，不能静默复用同一账号冒充 5 个独立用户。

### 6.2 每轮生成的变量

以下变量位于业务 Loop Controller 内的 User Parameters，每轮生成一次并在相关请求间复用：

| 变量 | 生成规则 | 使用位置 |
|---|---|---|
| `firstName` | `TEST${__Random(1000,9999,)}` | 联系人查重、保存和刷新行定位 |
| `lastName` | `TEST${__Random(1000,9999,)}` | 联系人查重、保存和刷新行定位 |
| `plateNo` | `P${__Random(100000,999999,)}` | 两次车辆查重、车辆保存、车辆/财物行定位 |
| `vinNo` | `W${__RandomString(15,0123456789,)}` | 第二次车辆查重和车辆保存 |
| `releaseDate` | `${__time(MM/dd/yyyy,)}` | 财物处置保存和 auto-confirm |
| `contact_popup_rnd` | `0.${__Random(100000000,999999999,)}` | Contact popup GET/POST |
| `contact_mn_rnd` | `0.${__Random(100000000,999999999,)}` | Contact set/search/remove session |
| `vehicle_popup_rnd` | `0.${__Random(100000000,999999999,)}` | Vehicle popup GET/POST |
| `vehicle_mn_rnd_1` | `0.${__Random(100000000,999999999,)}` | 第一组 vehicle set/search/remove |
| `vehicle_mn_rnd_2` | `0.${__Random(100000000,999999999,)}` | 第二组 vehicle set/search/remove |
| `property_popup_rnd` | `0.${__Random(100000000,999999999,)}` | Property popup GET/POST |
| `disposition_popup_rnd` | `0.${__Random(100000000,999999999,)}` | Disposition popup GET/POST |
| `intake_page_rnd` | `0.${__Random(100000000,999999999,)}` | Intake GET 和 auto-confirm |

只出现一次且无需复用的其他 `rnd` 可在对应请求中内联生成。捕获中的 SSN 和 Driver License 为空，因此不生成这两个值。

### 6.3 静态字段

- `division_id=3`、`inbox_sub_id=10030101`、`template_id=2409`、`report_type=C`、`indicator_type=1`。
- 联系人：DOB `05/05/1998`、sex `M`、race `A`、ethnicity `H`、state `PA`、county `36` 等。
- 车辆：state `PA`、year `2020`、make `AUDI`、model `2000 TT-COUPE`、body type `4 DOOR`、color `BLACK` 等。
- 财物：type `VEHICLE`、status `23`、value `3000`、value type `FAIR MARKET VALUE`。
- 报告：narrative `test note`、template code `RMS_PROPERTYRELEASEFORM`、disposition status `Complete`。

auto-confirm 中的案件号、case ID、report ID 和 `ORG_IMAGE` 内的 region ID 必须分别引用 `${dept_case_no}`、`${case_id}`、`${report_id}`、`${region_id}`，禁止使用抓包旧值。

## 7. 关联与提取器

| 来源 | 变量 | 提取方式与作用域 |
|---|---|---|
| GET Login | `login_csrf` | CSS：`input[name="__RequestVerificationToken"]` 的 `value`；主响应。 |
| POST Login 重定向最终页 | `disclaimer_csrf` | CSS hidden token；main sample and sub-samples。 |
| GET Home | `staff_id`, `region_id` | 从 Home HTML 的 Inbox URL 和 ImageHandler URL 提取。 |
| GET Inbox | `case_id` | CSS：`input[name="case_id"]` 的 `value`，Match No. 0 随机选择候选。 |
| GET Incident Summary | `dept_case_no` | Boundary 或正则提取 `PD Case #:` 后的案件编号。 |
| GET Police Report list | `police_csrf`, `police_timestamp` | CSS hidden token/timestamp。 |
| POST New Report 重定向最终页 | `FormGUID`, `middle_csrf`, `case_master_object` | 从最终 middlepage 提取；main sample and sub-samples。 |
| 各 popup GET | `<scope>_csrf`, `<scope>_timestamp` | 从各自 popup 提取，只供同一 popup 请求使用。 |
| Contact partial refresh | `contact_master_object` | 按 `${lastName}, ${firstName}` 所在行提取 `master_id_list`。 |
| Vehicle partial refresh | `vehicle_master_object`, `vehicle_id` | 按 `${plateNo}` 所在行提取，不使用捕获 ID。 |
| Property partial refresh | `property_master_object` | 按包含 `${plateNo}` 的 property 行提取。 |
| Disposition partial refresh | `disposition_master_object` | 同时限定 `${releaseDate}` 和 `COMPLETE`，选择最新匹配行。 |
| CreateIntake JSON | `report_id` | JSON Extractor：`$.report_id`。 |
| GET Intake | `intake_csrf` | 从 Intake 页面提取，只供 auto-confirm 使用。 |

各 token 按页面作用域单独命名。跟随重定向请求的提取器覆盖最终响应；其他提取器只检查直接响应。任何动态提取失败都不得回退到抓包中的旧 ID 或 token。

## 8. CreateIntake 特殊编码

SAZ 52 的 `objects_parameter` 和 `objects_data_index` 包含本轮创建的对象 ID，不能使用捕获的 Base64 常量。

- 从 `${contact_master_object}`、`${vehicle_master_object}`、`${property_master_object}`、`${disposition_master_object}`、`${case_master_object}` 重建业务字符串。
- `objects_parameter` 的五个对象组使用 ETX（U+0003）连接。
- `objects_data_index` 的五个对象组使用 STX（U+0002）连接，并由各 master object 解析出对应 ID 组成索引前缀。
- 在 SAZ 52 Sampler 前使用必要的 Groovy JSR223 PreProcessor 完成解析、拼接和 Base64；启用编译缓存，通过 `vars.get(...)` 读取变量。
- JSR223 仅处理该跨响应组合编码，不用于候选随机选择或普通字段提取。

## 9. 建议断言（本计划不生成断言节点）

依据技能规则，阶段 1 只给出建议，后续生成的 JMX 也不加入 Assertion：

- 登录后：验证 GET Home 响应包含已登录页面特征，例如 `/RMS/Logout`。
- CreateIntake：验证 JSON `message` 为 `OK`，并且 `report_id` 为正整数。
- auto-confirm：验证响应正文符合业务成功内容，例如 `(?s)^\s*OK\s*$`。
- 最终列表：可人工或在独立校验脚本中确认本轮 `${report_id}` 已出现。

不建议添加仅判断 HTTP 200 的断言。

## 10. 风险、停止条件与数据规模

- 该场景会持续创建 person、vehicle、property、disposition 和 report 测试数据，不是只读压测。
- 5 个线程会并行选择 Active Case；如果候选案件数量不足，多个线程可能写入同一案件。
- 500–1500 ms Timer 作用于业务 Loop 下的 Sampler。忽略响应耗时时，每轮仅 Timer 约消耗 41 秒，10 分钟理论上限约为每线程 14 轮、合计约 70 份报告；实际数量取决于服务响应时间和错误率。
- Inbox 无候选、任一关键 token/master object 未提取、CreateIntake 未返回有效 report ID 或账号权限不足时，对应线程应明确失败并停止，不能使用捕获旧值继续写入。
- 随机姓名、车牌和 VIN 仍有低概率碰撞；目标环境若有严格格式规则，需在生成 JMX 前提供规则。
- SAZ 没有捕获清理流程，本计划不会自动删除所创建的数据；运行后数据清理由环境负责人处理。

## 11. 批准记录和执行前置条件

已确认：

- 5 个并发用户。
- 5 秒 Ramp-up。
- 600 秒持续时间。
- 业务流程持续循环，Uniform Random Timer 为 500–1500 ms。
- 用户已明确回复“确认通过，生成 JMX”。

以下事项不阻塞 JMX 生成，但在执行负载测试前必须确认：

1. 提供或准备 5 个不同的有效测试账号及登录 POST 所需的已编码密码。
2. 确认 `parms42test.csitech.com` 是获准压测的环境，并允许在 10 分钟内持续创建上述测试数据。
3. 确认测试后数据清理责任人或接受保留测试数据。

执行正式负载测试前还必须：

1. 完成单用户冒烟验证，确认全部动态关联和保存链路成功。
2. 禁用 View Results Tree，启用 Simple Data Writer。
3. 指定 JTL 和 JMeter 日志输出位置，避免覆盖已有结果。
4. 确认 5 个账号、目标案件和 template 2409 均具有新增及保存权限。
