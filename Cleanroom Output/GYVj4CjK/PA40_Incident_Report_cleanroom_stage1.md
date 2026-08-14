# PA40 Incident Report — Clean-room JMeter Stage 1 分析方案

> 状态：**等待用户重新确认，尚未生成 JMX，也不会执行测试。**

## 1. Clean-room 边界与来源

本方案从零分析，读取范围严格限定为：

- 输入：`PA40_Incident_report.saz`
- 规则：`jmeter-loader-skills/SKILL.md`
- 规则引用：`jmeter-loader-skills/references/saz-analysis.md`
- 规则引用：`jmeter-loader-skills/references/parameterization-rules.md`
- SAZ 在隔离目录解包后产生的原始会话文件（它们只是上述 SAZ 的派生内容）

没有读取 Git 历史，也没有读取项目中的已有 JMX、Markdown、报告、Output、HAR、TXT、场景文件或其他既有产物。

- SAZ SHA-256：`bab23a4e45513e28f1a93fd0d4f4e24abc7b0eb63fb7670f7ced0f7d24b9f602`
- SAZ 会话数：90 个请求、90 个响应、90 个元数据文件
- 目标站点：`https://parms42test.csitech.com:443`

## 2. 当前需求与待确认假设

| 项目 | Stage 1 方案 | 状态 |
|---|---|---|
| 并发用户 | 1 | 用户已指定 |
| 持续时间 | 300 秒（5 分钟） | 用户已指定 |
| Ramp-up | 1 秒 | 建议值，待确认 |
| 循环方式 | Scheduler 300 秒 + Forever Loop | 建议值，保证业务持续运行满 5 分钟 |
| 登录位置 | Once Only Controller | 建议值；同一线程只登录一次，业务流循环 |
| 思考时间 | 每个业务请求前 Uniform Random Timer 500–1500 ms | 建议值，待确认；不是对录制间隔的逐秒回放 |
| 吞吐量控制器 | 不添加 | 未给出目标吞吐量 |
| 重定向 | `Follow Redirects=true`，折叠 5 个纯重定向目标会话 | 来自 SAZ 链路 |
| 测试账户 | CSV：`username,password,staff_id,region_id`，使用录制账户作为首行 | 账户值不在本文展示 |
| 执行测试 | 不执行 | 用户明确要求 |

说明：若用“固定 1 次循环”，业务可能在 5 分钟前结束；因此推荐线程组由 Scheduler 控制 300 秒，登录只执行一次，核心业务持续循环。线程启动和登录时间包含在 300 秒内。

## 3. 流量筛选结果

### 3.1 保留规则

- 登录、免责声明、首页、Inbox、案件选择、Incident Summary、Police Report。
- 新建 Incident Report 的受害人、车辆、PA charge、CreateIntake、保存确认及工作流提交。
- 业务所需的 Dropdown、MasterName、GIS、IDReader 和 partial refresh 请求。
- 302/页面跳转由 JMeter 的 `Follow Redirects` 完成，避免把浏览器重定向拆成重复采样器。

### 3.2 排除规则

- 状态/数量轮询：SAZ 10、13、15、21、81、90。
- 静态资源：SAZ 18–20、23–26、30–31、34、61–63、67–80、82–83。
- HTTPS CONNECT：SAZ 64–66。
- 被发起请求的 `Follow Redirects` 覆盖的跳转目标：SAZ 03–05、08、17。

原始业务请求保留 52 个；折叠 5 个跳转目标后，JMX 计划包含 **47 个 HTTP Sampler**。

## 4. 计划中的 JMeter 树

```text
Test Plan
└── Thread Group — PA40 Incident Report (users=1, ramp-up=1s, duration=300s, forever)
    ├── User Defined Variables
    ├── CSV Data Set Config — credentials.csv
    ├── HTTP Request Defaults — https / parms42test.csitech.com / 443
    ├── HTTP Cookie Manager
    ├── HTTP Cache Manager
    ├── Once Only Controller — Login
    │   ├── 01 GET Login
    │   ├── 02 POST Login
    │   ├── 03 GET Disclaimer page
    │   ├── 04 POST Disclaimer acceptance
    │   └── 05 GET Home
    ├── Loop Controller — Incident report business flow
    │   ├── Inbox and select random active case
    │   ├── Incident summary / police-report list / New Report
    │   ├── Add victim and refresh contact list
    │   ├── Add vehicle and refresh vehicle list
    │   ├── Select and save two PA charges
    │   ├── CreateIntake and open generated report
    │   ├── Save / auto-confirm
    │   ├── Route and save workflow
    │   └── Return to police-report list
    ├── View Results Tree — enabled for debug by default
    └── Simple Data Writer — disabled by default for later load execution
```

监听器仅按技能要求写入未来的 JMX；本阶段不生成 JMX，也不运行测试。

## 5. 47 个计划 Sampler 与来源

路径中的固定业务参数会保留；下表中 `${...}` 表示必须在 JMeter 中动态生成或从先前响应提取。

| # | SAZ | Method | 计划名称 / 路径要点 | 关键动态输入或输出 |
|---:|---:|---|---|---|
| 1 | 01 | GET | Login `/RMS/Login` | 提取 `login_csrf` |
| 2 | 02 | POST | Submit Login `/RMS/Login` | CSV 凭据 + `login_csrf`；Follow Redirects 覆盖 SAZ 03–05 |
| 3 | 06 | GET | Disclaimer page | `rnd` 动态化 |
| 4 | 07 | POST | Accept Disclaimer `/RMS/DisclaimerRedirect?handler=Jump` | 使用免责声明页 CSRF；Follow Redirects 覆盖 SAZ 08 |
| 5 | 09 | GET | Home `/RMS/Home?division_id=3` | 断言 Logout 链接；确认会话已登录 |
| 6 | 11 | GET | Inbox `/RMS/inbox/list` | `staff_id`、固定 inbox 参数；提取 MappingKey 和随机 `case_id` |
| 7 | 12 | GET | Incident Summary Dispatcher | `${case_id}` |
| 8 | 14 | GET | Police Report list | `${case_id}`；提取 `police_csrf`、`doubleEntryTimeStamp` |
| 9 | 16 | POST | New Report | `${case_id}` + 上一步 token/timestamp；Follow Redirects 覆盖 SAZ 17；从最终页面提取 `FormGUID`、`middle_csrf`、案件对象 ID |
| 10 | 22 | GET | Add Victim popup | `${case_id}`、`${FormGUID}`、`${victim_popup_rnd}`；提取 `victim_csrf`、popup timestamp |
| 11 | 27 | POST | Victim dropdown 1 | `victim_csrf` 与捕获表单参数 |
| 12 | 28 | POST | Victim dropdown 2 | `victim_csrf` 与捕获表单参数 |
| 13 | 29 | POST | Victim IDReader | Body Data 为原始 JSON `{"a":1}`；保留捕获的 form Content-Type |
| 14 | 32 | POST | Set MasterName session — name | `${contact_name_mn_rnd}`、`victim_csrf` |
| 15 | 33 | GET | Search unique victim name | `${lastName}`、`${firstName}`，复用 `${contact_name_mn_rnd}` |
| 16 | 35 | POST | Remove MasterName session — name | 复用 `${contact_name_mn_rnd}`、`victim_csrf` |
| 17 | 36 | POST | Set MasterName session — SSN | `${contact_ssn_mn_rnd}`、`victim_csrf` |
| 18 | 37 | GET | Search unique victim SSN | `${ssn}`，复用 `${contact_ssn_mn_rnd}` |
| 19 | 38 | POST | Remove MasterName session — SSN | 复用 `${contact_ssn_mn_rnd}`、`victim_csrf` |
| 20 | 39 | GET | GIS GeoCode | `${mapping_key}`、`${region_id}`；不得硬编码捕获 key |
| 21 | 40 | GET | GIS MasterLocation children | `${mapping_key}`、`${region_id}`、固定 master location ID |
| 22 | 41 | GET | GIS CommonPlaces | `${mapping_key}`、`${region_id}`、固定 master location ID |
| 23 | 42 | POST | Victim address dropdown | `victim_csrf` 与捕获表单参数 |
| 24 | 43 | POST | Save Victim | `${firstName}`、`${lastName}`、`${ssn}`、`${case_id}`、`victim_csrf`、popup timestamp |
| 25 | 44 | GET | Refresh contact list | `${FormGUID}`、`${middle_csrf}`；按姓名所在行提取 `${contact_master_object}` |
| 26 | 45 | GET | Add Vehicle popup | `${case_id}`、`${vehicle_popup_rnd}`；提取 `vehicle_csrf`、popup timestamp |
| 27 | 46 | POST | Vehicle dropdown | `vehicle_csrf` 与捕获表单参数 |
| 28 | 47 | POST | Vehicle IDReader | Body Data 为原始 JSON `{"a":1}`；保留捕获的 form Content-Type |
| 29 | 48 | POST | Set MasterVehicle session | `${vehicle_mn_rnd}`、`vehicle_csrf` |
| 30 | 49 | GET | Search unique plate | `${plateNo}`，复用 `${vehicle_mn_rnd}` |
| 31 | 50 | POST | Remove MasterVehicle session | 复用 `${vehicle_mn_rnd}`、`vehicle_csrf` |
| 32 | 51 | POST | Vehicle dropdown 2 | `vehicle_csrf` 与捕获表单参数 |
| 33 | 52 | POST | Save Vehicle | `${plateNo}`、`${case_id}`、`vehicle_csrf`、popup timestamp |
| 34 | 53 | GET | Refresh vehicle list | `${FormGUID}`、`${middle_csrf}`；按 plate 所在行提取 `${vehicle_master_object}` |
| 35 | 54 | GET | Add NJS/Charge popup | `${case_id}`、`${njs_popup_rnd}`；提取 `njs_csrf`、popup timestamp |
| 36 | 55 | GET | PA charge candidate list — role 4 | 从 100 个候选值随机提取 code/description |
| 37 | 56 | GET | PA charge candidate list — role 3 | 从 100 个候选值随机提取 code/description |
| 38 | 57 | POST | Save two PA charges | `${charge_1_code/description}`、`${charge_2_code/description}`、`njs_csrf`、popup timestamp |
| 39 | 58 | GET | Refresh charge list | `${middle_csrf}`；按两个 code 所在行分别提取 `${inv_njs_id_1}`、`${inv_njs_id_2}` |
| 40 | 59 | POST | CreateIntake | 重建并 Base64 编码对象参数；提取 `${report_id}` |
| 41 | 60 | GET | Open Intake report | `${report_id}`、`${intake_page_rnd}`；提取 `intake_csrf` |
| 42 | 84 | POST | Intake auto-confirm | `${report_id}`、`intake_csrf`；复用 `${intake_page_rnd}` 作为 Referer；复用两组动态 charge |
| 43 | 85 | GET | Assign Workflow | `${report_id}`、`${workflow_rnd_1}`、`${workflow_rnd_2}`；提取 `workflow_csrf` |
| 44 | 86 | POST | Workflow next-step changed | `${report_id}`、`workflow_csrf`；Referer 复用两个 workflow rnd |
| 45 | 87 | POST | Save Workflow | `${report_id}`、`workflow_csrf`；Referer 复用两个 workflow rnd |
| 46 | 88 | POST | Clear Workflow | multipart；`${report_id}`、`workflow_csrf`；保留捕获 boundary/part 结构 |
| 47 | 89 | GET | Final Police Report list | `${case_id}`、固定 `division_id=3` |

## 6. 参数化设计

### 6.1 CSV 数据

`credentials.csv`：

```csv
username,password,staff_id,region_id
<captured-user>,<captured-password>,1,100000
```

实际 CSV 可在 Stage 2 从 SAZ 登录表单写入，但本文不暴露凭据。`recycle=true`、`stopThread=false`、`sharingMode=shareMode.all`；当前只有 1 个线程。

### 6.2 每次业务循环生成

| 变量 | 规则 | 复用位置 |
|---|---|---|
| `firstName` | `TEST${__Random(1000,9999)}` | 姓名查重、Save Victim、刷新行定位 |
| `lastName` | `TEST${__Random(1000,9999)}` | 姓名查重、Save Victim、刷新行定位 |
| `ssn` | 按技能规定生成随机合法格式 | SSN 查重、Save Victim |
| `plateNo` | `P` + 随机数字 | 车辆查重、Save Vehicle、刷新行定位 |
| `victim_popup_rnd` | 每循环随机小数 | Add/Save Victim 同一 popup 链 |
| `vehicle_popup_rnd` | 每循环随机小数 | Add/Save Vehicle 同一 popup 链 |
| `njs_popup_rnd` | 每循环随机小数 | Add/Save Charge 同一 popup 链 |
| `contact_name_mn_rnd` | 每循环随机小数 | name set/search/remove 三请求复用 |
| `contact_ssn_mn_rnd` | 每循环随机小数 | SSN set/search/remove 三请求复用 |
| `vehicle_mn_rnd` | 每循环随机小数 | vehicle set/search/remove 三请求复用 |
| `intake_page_rnd` | 每循环随机小数 | GET Intake 与 POST84 Referer 复用 |
| `workflow_rnd_1/2` | 每循环两个随机小数 | GET85 URL 与 POST86–88 Referer 复用 |

其他仅出现一次的 `rnd` 可在对应请求中内联生成。驾驶证字段在捕获流量中为空，没有可靠来源，因此不凭空添加驾驶证随机值。Narrative 保持 SAZ 捕获的静态业务文本，除非用户另行要求参数化。

### 6.3 保留的静态业务值

- `division_id=3`、`inbox_sub_id=10030101`、`template_id=1318`、`report_type=C`、`indicator_type=1`。
- 地址业务字段保持捕获值：`6 ACORN BLVD, LANCASTER PA 17602`、county 36、municipality 36215、经纬度、country US、source master。
- 车辆业务字段保持捕获值：PA、2020、AUDI、5000、CONVERTIBLE、BLACK、DMV 等；车牌号动态化。
- 工作流值保持捕获语义：`ROUTE1`、`PENDING`、`INTAKE_1LEVELGROUP`、`GROUP`、`OFFICER` 等。

这些值在本次 SAZ 中没有展示可替换来源，Stage 2 不应为了“更随机”而虚构参数化。

## 7. 关联提取与作用域

| 来源响应 | 提取变量 | 使用范围 / 方法 |
|---|---|---|
| SAZ 01 | `login_csrf` | POST02；HTML token extractor |
| SAZ 05（POST02 redirect 最终响应） | `disclaimer_csrf` | POST07 |
| SAZ 09 | 登录成功标志 | Response Assertion：包含 `/RMS/Logout` |
| SAZ 11 | `mapping_key` | GIS 39–41；从 `sessionStorage.setItem("MappingKey", ...)` 提取 |
| SAZ 11 | `case_id` | 100 个 active-case 链接中 Match No. 0 随机选择 |
| SAZ 14 | `police_csrf`, `doubleEntryTimeStamp` | POST16 |
| SAZ 17（POST16 redirect 最终响应） | `FormGUID`, `middle_csrf`, `case_location_id`, `case_master_object` | 后续 middlepage partial refresh 和 CreateIntake |
| SAZ 22 | `victim_csrf`, `victim_timestamp` | Victim popup 请求 27–43 |
| SAZ 44 | `contact_master_object` | XPath：定位 `${lastName}, ${firstName}` 所在行的 `master_id_list` |
| SAZ 45 | `vehicle_csrf`, `vehicle_timestamp` | Vehicle popup 请求 46–52 |
| SAZ 53 | `vehicle_master_object` | XPath：定位 `${plateNo}` 所在行的 `master_id_list` |
| SAZ 54 | `njs_csrf`, `njs_timestamp` | Charge save 57 |
| SAZ 55 | `charge_1_code`, `charge_1_description` | 100 个 `return_value~|list~|D` 候选中随机选择、URL/HTML 解码并按 `~` 分割 |
| SAZ 56 | `charge_2_code`, `charge_2_description` | 同上，但保持第二种 charge role 独立 |
| SAZ 58 | `inv_njs_id_1`, `inv_njs_id_2` | XPath：分别按动态 code 定位对应行 |
| SAZ 59 | `report_id` | JSON Extractor；要求正整数 |
| SAZ 60 | `intake_csrf` | POST84 header/form |
| SAZ 85 | `workflow_csrf` | POST86、87 header 与 POST88 multipart part |

没有在 SAZ 中发现 `__VIEWSTATE`、`__VIEWSTATEGENERATOR` 或 `__EVENTVALIDATION`，因此不添加这些关联。

### 7.1 CSRF 的实际作用域

- POST02 ← SAZ 01。
- POST07 ← SAZ 05。
- POST16 的 CSRF/timestamp ← SAZ 14。
- SAZ 27、28、29、32、35、36、38、39、40、41、42、43 ← SAZ 22。
- SAZ 44、53、58、59 的 header token ← SAZ 17 的 middlepage token。
- SAZ 46、47、48、50、51、52 ← SAZ 45。
- SAZ 57 ← SAZ 54。
- SAZ 84 ← SAZ 60。
- SAZ 86、87、88 ← SAZ 85。

### 7.2 CreateIntake 特殊编码

SAZ 59 的 `objects_parameter` 与 `objects_data_index` 不是安全的静态常量：

- `objects_parameter` 的对象组之间使用 ETX（U+0003），两个 NJS ID 之间使用 STX（U+0002）。
- `objects_data_index` 的各组之间使用 STX（U+0002）。
- Stage 2 必须从 `${contact_master_object}`、`${vehicle_master_object}`、`${inv_njs_id_1}`、`${inv_njs_id_2}` 和案件对象 ID 重建字节序列，再 Base64 编码。
- 禁止沿用 SAZ 中捕获的 Base64，否则会引用旧对象 ID。

### 7.3 特殊请求体

- SAZ 29、47：请求体必须用 JMeter **Body Data** 原样发送 JSON `{"a":1}`，不能转换成 Parameters；同时保留 SAZ 捕获的 `application/x-www-form-urlencoded; charset=UTF-8`。
- SAZ 88：保留 multipart boundary 和两个 part（`report_ids`、`__RequestVerificationToken`）的结构，只替换动态 report ID/token。

## 8. 断言设计（用户已要求 3 组）

| 组 | 位置 | 断言 | JMeter 节点数 |
|---:|---|---|---:|
| 1 | Home（SAZ 09） | Response Assertion：响应包含 `href="/RMS/Logout"` | 1 |
| 2 | CreateIntake（SAZ 59） | JSON Assertion：`message == OK`；JSON Assertion：`report_id` 为正整数 | 2 |
| 3 | auto-confirm（SAZ 84） | Response Assertion：响应匹配 `(?s)^\s*WF\s*$` | 1 |

合计 3 组、4 个 JMeter Assertion 节点。它们会在 Stage 2 写入 JMX；本阶段仅记录设计。

## 9. 风险与前置条件

- 当前 1 个用户仍会创建真实业务数据；运行前应确认测试环境允许持续创建 report、person、vehicle 和 charge 数据。
- 一个账户能否反复创建 Incident Report、案件候选是否始终非空，需要环境侧保证。
- Inbox 的随机 `case_id` 来自当次响应，不使用捕获的固定 case ID；若没有候选，线程应明确失败而不是继续提交旧 ID。
- MappingKey 必须从当次 Inbox 响应提取，不能硬编码 SAZ 中的 key。
- 两个 charge 候选列表和对应 ID 必须保持角色/行关系；不能交叉复用。
- CSRF token 有页面作用域，不能用一个全局 token 覆盖所有页面。
- 由于持续 300 秒，最后一轮业务可能在 Scheduler 截止时被中断，这是 duration 模式的正常行为。

## 10. Stage 2 前需要重新确认

请确认或修改以下内容后再生成 JMX：

1. Ramp-up 使用 1 秒。
2. Scheduler 300 秒 + Forever Loop，且登录/启动时间包含在 300 秒内。
3. 每个业务请求前使用 500–1500 ms Uniform Random Timer。
4. 使用 SAZ 中捕获的账户生成单行 `credentials.csv`，但不在分析文档中显示凭据。
5. 写入上述 3 组断言（4 个 Assertion 节点）。

在收到新的明确批准前，流程停留在 Stage 1：**不生成 JMX，不验证 JMX，不执行测试。**
