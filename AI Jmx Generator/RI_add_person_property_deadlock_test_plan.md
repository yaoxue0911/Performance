# RI Add Person / Add Property 死锁测试计划（审批稿）

## 1. 目标与范围

- 输入抓包：`Fiddler file/RI_add person and property.saz`
- 目标链路：登录 → 打开 case → Add Person → 打开 Add Property → 选择本线程刚新增的 person → 20 个线程同时 Save Property。
- 测试目的：制造 5 个 case 上的并发写入和 Property 保存瞬时冲击，观察 Save Property 是否长时间阻塞、超时、返回应用错误，或导致后续 Property List 无法刷新。
- 场景类型：峰值/突发场景；每线程只执行 1 次。
- 本文档是阶段 1 文字计划，不生成、修改或验证任何 `.jmx` 文件。

## 2. 压测配置

| 项目 | 值 |
|---|---|
| JMeter 目标版本 | 5.6.3 |
| 协议 | `https` |
| 主机 | `rirmsint.csitech.com` |
| 端口 | `443` |
| 编码 | UTF-8 |
| 线程数 | 20 |
| Ramp-up | 1 秒 |
| 循环次数 | 1 |
| Thread Group duration | 1,800 秒（scheduler 上限；正常情况下单次流程完成即退出） |
| HTTP connect timeout | 10,000 ms |
| HTTP response timeout | 300,000 ms |
| Synchronizing Timer 分组数 | 20 |
| Synchronizing Timer 超时 | 300,000 ms |

case 分配使用原生 **User Parameters**，变量名为 `case_id`，配置 5 个用户值：

1. `<CASE_ID_1>`
2. `<CASE_ID_2>`
3. `<CASE_ID_3>`
4. `<CASE_ID_4>`
5. `<CASE_ID_5>`

20 个线程按 User Parameters 的用户行循环映射，因此每个 case 预计分配 4 个线程。Synchronizing Timer 在整个线程组内等待 20 个线程，所以 20 个 Save Property 请求会一起释放，而不是按 case 分为 5 个同步组。

## 3. 公共配置元件

- **HTTP Request Defaults**
  - Protocol：`https`
  - Server Name：`rirmsint.csitech.com`
  - Port：`443`
  - Content Encoding：`UTF-8`
  - Connect Timeout：`10000`
  - Response Timeout：`300000`
- **HTTP Cookie Manager**
  - `clear_each_iteration=false`
  - 每个线程维护独立登录会话。
- **HTTP Header Manager（公共）**
  - `Accept-Language: en-US,en;q=0.9`
  - 使用抓包中的浏览器 `User-Agent`。
  - HTML 页面使用抓包中的 HTML `Accept`；AJAX 请求使用抓包中的 `Accept` 和 `X-Requested-With: XMLHttpRequest`。
  - 所有 POST 按抓包使用 `application/x-www-form-urlencoded` 或 `application/x-www-form-urlencoded; charset=UTF-8`。
  - 不生成 `Referer` 请求头。
- **CSV Data Set Config：users.csv**
  - 列：`user_name,password,staff_id,staff_region_id`
  - 3 行账号数据由用户填写；模板不保留抓包密码。
  - `shareMode.all`、`recycle=true`、`stopThread=false`，20 个线程循环使用 3 个账号，预计分配为 7/7/6 个线程。
- **User Defined Variables**
  - `division_id=3`
  - `inbox_sub_id=10030121`
  - `STX=${__groovy((char)2,)}`，运行时生成字符 `\u0002`，供 ShowCountInTab 的 `urls` 多段值拼接，同时避免在 XML 中写入非法控制字符。
- **User Parameters：Case IDs**
  - 变量：`case_id`
  - 5 行值为用户提供的 5 个 case ID。
- **User Parameters：Dynamic Person Data**（业务 Loop Controller 内、Add Person 前）
  - 每轮更新一次，保证一个线程内查询、保存和选择人员复用同一组值。
  - `firstName=DLKF${__threadNum}${__Random(1000,9999)}`
  - `lastName=DLKL${__threadNum}${__Random(1000,9999)}`
  - `mn_rnd=${__RandomString(16,0123456789,)}`

## 4. JMeter GUI 测试树

```text
Test Plan - RI Add Person and Property Deadlock
├── User Defined Variables
├── HTTP Request Defaults
├── HTTP Cookie Manager
├── HTTP Header Manager
├── CSV Data Set Config - users.csv
├── Thread Group - 20 Users / 1s Ramp-up / 1 Loop
│   ├── Once Only Controller - Login and Home Initialization
│   │   └── Transaction Controller - Login and Initialize Session
│   │       ├── GET /RMS/Login.aspx load login page
│   │       │   ├── CSS Extractor - login_viewstate
│   │       │   └── CSS Extractor - login_viewstate_generator
│   │       ├── POST /RMS/Login.aspx submit login
│   │       │   ├── CSS Extractor - disclaimer_viewstate
│   │       │   ├── CSS Extractor - disclaimer_viewstate_generator
│   │       │   └── CSS Extractor - disclaimer_event_validation
│   │       ├── GET /RMS/AspSoft/Disclaimer/Disclaimer.htm load disclaimer
│   │       ├── POST /RMS/DisclaimerRedirect.aspx accept disclaimer
│   │       ├── GET /RMS/HomeA.aspx initialize home
│   │       ├── POST /RMS/AspSoft/Inbox/inboxService.ashx initialize inbox counts
│   │       └── GET /RMS/AspSoft/inbox/inboxTaskList.aspx initialize active cases
│   └── Loop Controller - Add Person and Property (1 Loop)
│       ├── User Parameters - Case IDs
│       ├── User Parameters - Dynamic Person Data
│       ├── Transaction Controller - Open Case
│       │   ├── GET /RMS/AspSoft/Dispatcher.aspx open incident summary
│       │   └── POST /RMS/AspSoft/EngineService.ashx load case tab counts
│       ├── Transaction Controller - Add Person
│       │   ├── GET /RMS/Aspsoft/Dispatcher.aspx open party list
│       │   ├── POST /RMS/AspSoft/EngineService.ashx load party tab count
│       │   ├── GET /RMS/Aspsoft/PopUpDispatcher.aspx open Add Party
│       │   ├── POST /RMS/Aspsoft/engineservice.ashx load driver-license states
│       │   ├── POST /RMS/Aspsoft/engineservice.ashx load place-of-birth states
│       │   ├── POST /RMS/Include/CommonModule/Remote.ashx load city list
│       │   ├── GET /RMS/Include/RMS/IDReaderHandler.ashx initialize ID reader control
│       │   ├── POST /RMS/AspSoft/MasterName.aspx initialize master-name search session
│       │   ├── GET /RMS/AspSoft/MasterName.aspx search generated person name
│       │   ├── POST /RMS/AspSoft/MasterName.aspx remove master-name search session
│       │   ├── POST /RMS/Aspsoft/PopUpDispatcher.aspx save suspect
│       │   ├── GET /RMS/Aspsoft/Dispatcher.aspx refresh party list
│       │   └── POST /RMS/AspSoft/EngineService.ashx refresh party tab count
│       ├── Transaction Controller - Open Add Property and Select Person
│       │   ├── GET /RMS/Aspsoft/Dispatcher.aspx open property list
│       │   │   ├── CSS Extractor - property_list_viewstate
│       │   │   └── CSS Extractor - property_list_viewstate_generator
│       │   ├── POST /RMS/AspSoft/EngineService.ashx load property tab count
│       │   ├── GET /RMS/Aspsoft/PopUpDispatcher.aspx open Add Property
│       │   │   ├── CSS Extractor - add_property_viewstate
│       │   │   ├── CSS Extractor - add_property_viewstate_generator
│       │   │   ├── CSS Extractor - add_property_event_validation
│       │   │   ├── CSS Extractor - add_property_double_entry_timestamp
│       │   │   └── Regular Expression Extractor - person_id_for_property
│       │   └── POST /RMS/Aspsoft/engineservice.ashx load property subtypes
│       ├── Transaction Controller - Synchronized Save Property
│       │   ├── Synchronizing Timer - release 20 users together
│       │   └── POST /RMS/Aspsoft/PopUpDispatcher.aspx save property
│       └── Transaction Controller - Refresh Property Result
│           ├── POST /RMS/Aspsoft/Dispatcher.aspx refresh property list
│           └── POST /RMS/AspSoft/EngineService.ashx refresh property tab count
├── View Results Tree (enabled for debugging)
└── Simple Data Writer (disabled; file RI_add_person_property_deadlock.jtl)
```

所有 HTTP Request Sampler 均设置 `follow_redirects=true`。

## 5. 请求、参数与关联契约

### 5.1 Once Only：登录和初始化

| 请求名称 | Method / Path | 关键参数与关联 |
|---|---|---|
| `GET /RMS/Login.aspx load login page` | GET `/RMS/Login.aspx` | 从响应 CSS `input#__VIEWSTATE`、`input#__VIEWSTATEGENERATOR` 提取登录隐藏字段。 |
| `POST /RMS/Login.aspx submit login` | POST `/RMS/Login.aspx` | `__VIEWSTATE=${login_viewstate}`、`__VIEWSTATEGENERATOR=${login_viewstate_generator}`、`txtUserName=${user_name}`、`txtPassword=${password}`、`btnLogin=Login`；其他字段按抓包保留。跟随 302 到 `/RMS/Index.aspx`，从最终响应提取 Disclaimer 所需的 `__VIEWSTATE`、`__VIEWSTATEGENERATOR`、`__EVENTVALIDATION`。 |
| `GET /RMS/AspSoft/Disclaimer/Disclaimer.htm load disclaimer` | GET `/RMS/AspSoft/Disclaimer/Disclaimer.htm?rnd=0.7382110518734248` | 保留抓包查询参数。 |
| `POST /RMS/DisclaimerRedirect.aspx accept disclaimer` | POST `/RMS/DisclaimerRedirect.aspx?division_id=${division_id}` | 使用上一步登录重定向页提取的三个 WebForms 隐藏字段；`btnJump` 保持空值。 |
| `GET /RMS/HomeA.aspx initialize home` | GET `/RMS/HomeA.aspx?division_id=${division_id}` | 初始化受保护主页。 |
| `POST /RMS/AspSoft/Inbox/inboxService.ashx initialize inbox counts` | POST `/RMS/AspSoft/Inbox/inboxService.ashx?debug_connection=0` | `Action=GetInboxCaseCountOneTime`、`iStaffID=${staff_id}`、`iDivisionID=${division_id}`、`staff_region_id=${staff_region_id}`；`REGION` 和 `sListPageID` 保留抓包值。 |
| `GET /RMS/AspSoft/inbox/inboxTaskList.aspx initialize active cases` | GET `/RMS/AspSoft/inbox/inboxTaskList.aspx` | `nextPID=listInbox_MyActiveCase_Primary`、`inbox_staff_id=${staff_id}`、`inbox_sub_id=${inbox_sub_id}`、`UseDefault=1`、`is_temp_page_size=1`、`page_size=100`。 |

### 5.2 Open Case

| 请求名称 | Method / Path | 关键参数与关联 |
|---|---|---|
| `GET /RMS/AspSoft/Dispatcher.aspx open incident summary` | GET `/RMS/AspSoft/Dispatcher.aspx` | `nextPID=inquireIncidentSummary`、`case_id=${case_id}`。 |
| `POST /RMS/AspSoft/EngineService.ashx load case tab counts` | POST `/RMS/AspSoft/EngineService.ashx` | Query：`menu_id=1`、`action=ShowCountInTab`、`nextPID=inquireIncidentSummary`、`case_id=${case_id}`、`division_id=${division_id}`、`check_menu=1`、抓包 `rnd`；Body 的 `urls` 与 `currentUrl` 中所有捕获 case ID 替换为 `${case_id}`，多 URL 继续使用 `${STX}` 分隔。 |

### 5.3 Add Person

| 请求名称 | Method / Path | 关键参数与关联 |
|---|---|---|
| `GET /RMS/Aspsoft/Dispatcher.aspx open party list` | GET `/RMS/Aspsoft/Dispatcher.aspx` | `nextPID=showCaseContact`、`case_id=${case_id}`、`division_id=${division_id}`。 |
| `POST /RMS/AspSoft/EngineService.ashx load party tab count` | POST `/RMS/AspSoft/EngineService.ashx` | `nextPID=showCaseContact`；Body 中所有 case ID 替换为 `${case_id}`。 |
| `GET /RMS/Aspsoft/PopUpDispatcher.aspx open Add Party` | GET `/RMS/Aspsoft/PopUpDispatcher.aspx` | `nextPID=addCaseVW`、`case_id=${case_id}`、抓包 `rnd`；用于人员检索和控件初始化。 |
| `POST /RMS/Aspsoft/engineservice.ashx load driver-license states` | POST `/RMS/Aspsoft/engineservice.ashx?action=dropdown&row_id=497130` | `param=US@*addCaseVW@driver_license_state@driver_license_country`。 |
| `POST /RMS/Aspsoft/engineservice.ashx load place-of-birth states` | POST `/RMS/Aspsoft/engineservice.ashx?action=dropdown&row_id=497146` | `param=US@*addCaseVW@pob_state@pob_country`。 |
| `POST /RMS/Include/CommonModule/Remote.ashx load city list` | POST `/RMS/Include/CommonModule/Remote.ashx?action=GET_CITY_LIST` | 抓包中 Body 为空。 |
| `GET /RMS/Include/RMS/IDReaderHandler.ashx initialize ID reader control` | GET `/RMS/Include/RMS/IDReaderHandler.ashx?action=IDREADEREABLE` | 控件初始化请求。 |
| `POST /RMS/AspSoft/MasterName.aspx initialize master-name search session` | POST `/RMS/AspSoft/MasterName.aspx` | Query：`PageID=SearchMasterNameSys_MasterPerson`、`action=setsession`、`rnd=${mn_rnd}`；Body 的 `MN_rnd=${mn_rnd}`，`ToObjects` 和 `ToAliasObjects` 保留抓包值。 |
| `GET /RMS/AspSoft/MasterName.aspx search generated person name` | GET `/RMS/AspSoft/MasterName.aspx` | `PageID=SearchMasterNameSys_MasterPerson`、`last_name=${lastName}`、`first_name=${firstName}`、`middle_name=`、`suffix_name=`、`dob=`、`paramsSource=session`、`MN_rnd=${mn_rnd}`；其余查询参数按抓包保留。 |
| `POST /RMS/AspSoft/MasterName.aspx remove master-name search session` | POST `/RMS/AspSoft/MasterName.aspx` | `PageID=SearchMasterNameSys_MasterPerson`、`action=removesession`、`MN_rnd=${mn_rnd}`；Body 为空。 |
| `POST /RMS/Aspsoft/PopUpDispatcher.aspx save suspect` | POST `/RMS/Aspsoft/PopUpDispatcher.aspx` | **替换来源：`Fiddler file/Add suspect.saz`。** Query：`nextPID=addSuspect`、`case_id=${case_id}`、`stage_id=2`、`rnd=0.3125118115257862`。Body 完整保留该 SAZ 的 WebForms 表单与空字段；替换 `last_name=${lastName}`、`first_name=${firstName}`、所有 case ID 为 `${case_id}`、region ID 为 `${staff_region_id}`。角色字段保持 `contact_type_name=SUSPECT`、`contact_type=DE`，并保留抓包的 DOB `08/11/2010`、juvenile `6`、sex `F`、race `A`、ethnicity `H`、`PID=addSuspect` 和 `submit_button=Save`。由于该 SAZ 只包含 POST，没有匹配的打开 Add Suspect GET，请求中的 `__VIEWSTATE`、`__VIEWSTATEGENERATOR`、`__EVENTVALIDATION` 和 `doubleEntryTimeStamp` 按该 SAZ 静态保留。 |
| `GET /RMS/Aspsoft/Dispatcher.aspx refresh party list` | GET `/RMS/Aspsoft/Dispatcher.aspx` | `nextPID=showCaseContact`、`case_id=${case_id}`、`division_id=${division_id}`。 |
| `POST /RMS/AspSoft/EngineService.ashx refresh party tab count` | POST `/RMS/AspSoft/EngineService.ashx` | `nextPID=showCaseContact`；Body 中所有 case ID 替换为 `${case_id}`。 |

### 5.4 Open Add Property、选择本线程 person

| 请求名称 | Method / Path | 关键参数与关联 |
|---|---|---|
| `GET /RMS/Aspsoft/Dispatcher.aspx open property list` | GET `/RMS/Aspsoft/Dispatcher.aspx` | `nextPID=listCaseProperty`、`case_id=${case_id}`、`division_id=${division_id}`。提取 Property List 的 `__VIEWSTATE` 和 `__VIEWSTATEGENERATOR`，供保存后的列表刷新 POST 使用。 |
| `POST /RMS/AspSoft/EngineService.ashx load property tab count` | POST `/RMS/AspSoft/EngineService.ashx` | `nextPID=listCaseProperty`；Body 中所有 case ID 替换为 `${case_id}`。 |
| `GET /RMS/Aspsoft/PopUpDispatcher.aspx open Add Property` | GET `/RMS/Aspsoft/PopUpDispatcher.aspx` | `nextPID=addCaseProperty`、`case_id=${case_id}`、抓包 `rnd`。提取 Property 表单的 `__VIEWSTATE`、`__VIEWSTATEGENERATOR`、`__EVENTVALIDATION`、`doubleEntryTimeStamp`。 |
| `Regular Expression Extractor - person_id_for_property` | Add Property 响应子元件 | 在同一个 `<tr>` 中同时匹配 `name='c_person_id' value='<ID>'` 和 `contact_name=${lastName}, ${firstName}`，捕获该行 ID 为 `${person_id_for_property}`。不得使用 Match No. 0 随机选人，因为同一 case 会同时出现其他线程新增的人员。 |
| `POST /RMS/Aspsoft/engineservice.ashx load property subtypes` | POST `/RMS/Aspsoft/engineservice.ashx?action=dropdown&row_id=479399` | `param=CLOTHING@*addCaseProperty@property_sub_type@property_type`。 |

### 5.5 同步 Save Property

Synchronizing Timer 紧邻 Save Property，并置于 `Synchronized Save Property` Transaction Controller 内：

- Number of Simulated Users to Group by：`20`
- Timeout in milliseconds：`300000`
- 只有所有线程完成登录、Add Person、打开 Add Property、提取隐藏字段和 person ID 后，才一起发送 Save Property。

| 请求名称 | Method / Path | 关键参数与关联 |
|---|---|---|
| `POST /RMS/Aspsoft/PopUpDispatcher.aspx save property` | POST `/RMS/Aspsoft/PopUpDispatcher.aspx` | Query：`nextPID=addCaseProperty`、`case_id=${case_id}`、与打开弹窗相同的抓包 `rnd`。Body 完整保留抓包表单和空字段；动态替换三个 WebForms 隐藏字段、`c_person_id=${person_id_for_property}`、表单 case ID `${case_id}`、`doubleEntryTimeStamp=${add_property_double_entry_timestamp}`。静态业务值：`property_type=CLOTHING`、`property_sub_type=131`（JACKET）、`property_status=23`（BURNED）、`quantity=1`、`value=200`、`value_type=FAIR MARKET VALUE`、`submit_button=Save`。 |

### 5.6 保存后刷新

| 请求名称 | Method / Path | 关键参数与关联 |
|---|---|---|
| `POST /RMS/Aspsoft/Dispatcher.aspx refresh property list` | POST `/RMS/Aspsoft/Dispatcher.aspx` | `nextPID=listCaseProperty`、`case_id=${case_id}`、`division_id=${division_id}`；Body 使用打开 Property List 时提取的 `__VIEWSTATE`、`__VIEWSTATEGENERATOR`，`PID=listCaseProperty` 和提取的列表 `doubleEntryTimeStamp`（若页面存在），其余字段按抓包保留。 |
| `POST /RMS/AspSoft/EngineService.ashx refresh property tab count` | POST `/RMS/AspSoft/EngineService.ashx` | `nextPID=listCaseProperty`；Body 中所有 case ID 替换为 `${case_id}`。 |

## 6. 过滤的抓包流量

不进入测试计划：

- Fiddler 更新检查和 CONNECT 隧道。
- CAD `signalr/ping`、`GetCfsParTimerCount`。
- `WebResource.axd`、CSS、JavaScript、图片和字体。
- `EngineService.ashx?action=get_process_flag`、`set_process_flag` 等轮询/流程标志请求。
- CrimeMapping 脚本、地址自动完成静态初始化，以及本次表单未使用的其他页面资源。

保留了 Home/Inbox、case tab count、Add Person 控件初始化、Master Name 查询、Property subtype dropdown 和保存后列表刷新，因为这些请求具有会话初始化、控件初始化、业务校验或结果刷新作用。

## 7. 结果判读与建议断言（不写入 JMX）

按技能约束，本计划不在 JMX 中添加断言。建议人工审批后另行决定是否加入以下业务断言：

- Login：最终响应确实打开受保护的 Index/Home，而不是返回登录页或登录错误。
- Save Suspect：响应包含 `parent.CloseDialog(1, '')`，并在后续 Party List 出现 `${lastName}, ${firstName}`，角色为 SUSPECT。
- Open Add Property：页面中能找到同时包含 `${lastName}, ${firstName}` 和 `${person_id_for_property}` 的同一人员行。
- Save Property：响应包含 `parent.CloseDialog(1, '')`。
- Refresh Property List：出现本次保存的 Property，且 Property 计数正常增加。

死锁/阻塞重点观察：

- `save property` 的 elapsed、latency、connect time、响应码和响应内容。
- 是否有请求一直等待到 300 秒 response timeout。
- 是否只有同一 case 的 4 个请求成组阻塞，还是 5 个 case 全部阻塞。
- 超时后 Property List 是否仍可刷新，以及服务是否自行恢复。
- 应用/数据库端同时采集死锁图、blocked session、lock wait 和异常日志；仅凭客户端超时不能证明数据库死锁。

## 8. 假设、默认值与待一次性确认

1. **case ID**：请把 5 个 `<CASE_ID_n>` 替换为实际值；每个 case 承受 4 个并发线程。
2. **并发模型**：默认 Ramp-up 为 1 秒、每线程执行 1 次；Synchronizing Timer 全局同步 20 个 Save Property。
3. **同步等待**：默认 Synchronizing Timer 超时 300 秒。若任何线程在前置步骤失败，其他线程最多等待 300 秒后释放；这次运行不再是严格 20 路同时保存，应判为无效并修复前置失败后重测。
4. **人员数据**：保存请求改用 `Add suspect.saz`；First/Last Name 按线程动态生成，SUSPECT、DOB、juvenile、sex、race、ethnicity 等其他值保持该抓包静态值。
5. **Property 数据**：保持抓包值 CLOTHING / JACKET / BURNED / quantity 1 / value 200 / FAIR MARKET VALUE。
6. **person 选择**：按唯一姓名在 Add Property 页的同一行提取 person ID；不随机选择，避免线程把 Property 关联到其他线程新增的人。
7. **超时**：HTTP response timeout 默认 300 秒，用于把长期阻塞转为可计数失败；如服务端死锁检测周期更长，需要提高该值。
8. **Listener**：调试阶段启用 View Results Tree、禁用 Simple Data Writer。正式负载测试前必须禁用 View Results Tree，并启用 Simple Data Writer 写入 `RI_add_person_property_deadlock.jtl`。

## 9. 审批门槛

用户已明确确认生成 JMX。5 个 case ID 保留在原生 User Parameters 中作为可编辑值；3 个登录账号保留在 `users.csv` 模板中作为可编辑行。阶段 2 生成 Scenario JSON、JMX 及配套 CSV，并执行结构与参数化验证。
