# CMOEM Permission + Investigation Report — JMeter 测试计划

## 1. 输入与负载模型

- 抓包：`Fiddler file/CMOEM_permission_report.saz`（40 个 HTTP 会话）。
- 目标：`http://10.1.3.248:80`，应用根路径 `/InfoRMS30`。
- 线程数：1；Ramp-up：1 秒；持续时间：600 秒。
- 线程组持续循环；登录和初始化仅在线程首次启动时执行一次。
- `case_id` 每轮从与 JMX 同目录的 `CMOEM case id.csv` 读取；初始值为抓包案件 `1100260052`。
- 登录账号和编码密码使用抓包静态值，不做参数化。
- 不添加任何断言。

## 2. 业务树

```text
Test Plan — CMOEM Permission and Investigation Report
└── Thread Group — CMOEM Permission and Report Stable Load
    ├── CSV Data Set Config — CMOEM case id.csv
    ├── HTTP Request Defaults — https / 10.1.3.248 / 443
    ├── HTTP Cookie Manager — clear_each_iteration=false
    ├── HTTP Cache Manager
    ├── Once Only Controller
    │   ├── GET /InfoRMS30/Login.aspx
    │   ├── POST /InfoRMS30/Login.aspx
    │   ├── POST /InfoRMS30/DisclaimerRedirect.aspx
    │   └── GET /InfoRMS30/Home.aspx
    ├── Loop Controller — Case permission and report loop
    │   ├── GET /InfoRMS30/AspSoft/Dispatcher.aspx?nextPID=inquireIncidentSummary&case_id=${case_id}
    │   ├── Transaction Controller — Modify case permission
    │   │   ├── GET /InfoRMS30/AspSoft/Security/CasePermission.aspx
    │   │   └── POST /InfoRMS30/AspSoft/Security/CasePermission.aspx
    │   └── Transaction Controller — Add investigation report
    │       ├── GET /InfoRMS30/Aspsoft/Dispatcher.aspx
    │       ├── POST /InfoRMS30/Aspsoft/Dispatcher.aspx
    │       ├── GET /InfoRMS30/aspsoft/popupdispatcher.aspx
    │       ├── POST /InfoRMS30/aspsoft/popupdispatcher.aspx
    │       ├── GET /InfoRMS30/Aspsoft/IntakeForm/middlepage.aspx
    │       ├── POST /InfoRMS30/Aspsoft/IntakeForm/middlepage.aspx
    │       ├── GET /InfoRMS30/Aspsoft/IntakeForm/Intake.aspx
    │       ├── POST /InfoRMS30/AspSoft/IntakeForm/Intake.aspx
    │       ├── GET /InfoRMS30/AspSoft/IntakeForm/IntakeReportAssignWorkflow.aspx
    │       ├── POST /InfoRMS30/AspSoft/IntakeForm/IntakeReportAssignWorkflow.aspx (选择下一步)
    │       ├── POST /InfoRMS30/AspSoft/IntakeForm/IntakeReportAssignWorkflow.aspx (clear)
    │       ├── POST /InfoRMS30/AspSoft/IntakeForm/IntakeReportAssignWorkflow.aspx (保存)
    │       └── GET /InfoRMS30/Aspsoft/Dispatcher.aspx
    ├── View Results Tree — enabled
    └── Simple Data Writer — disabled
```

## 3. 关联与静态数据

- 登录页、Disclaimer、权限页、Report 列表、NJS popup、Intake 和 Workflow 页面分别提取各自的 WebForms 隐藏字段。
- 新建 Report 的重定向最终页提取 `FormGUID` 和当前 `${case_id}` 对应的 case master object。
- NJS partial refresh 提取本轮新增的 `inv_njs_id`；Create Report 前用 Groovy 按抓包格式组合 NJS 与 case object，并进行 Base64 编码。
- Create Report 的纯文本响应提取 `${report_id}`，供 Intake 保存、Workflow 和返回列表使用。
- NJS 固定使用抓包值：描述 `POSS MARIHUAN >25G`，代码 `24:21-20A(4)`。
- 删除只用于返回 NJS 候选值的 `GET ...nextPID=listPopupChargeSub`，不从该前置请求获取 NJS 值。
- 抓包中的两个 case ID 全部替换为同一个 `${case_id}`；同一轮权限修改和添加 Report 操作同一案件。
- 每轮读取 `${case_id}` 后先打开该案件的 Incident Summary，再修改权限和添加 Report；打开案件请求不计入两个业务 Transaction。

## 4. 流量清理

- 排除 CONNECT、图片、JavaScript 等静态资源。
- 排除 `ShowCountInTab`、`set_process_flag`、Remote 开关及地址自动补全等非核心流量。
- POST 的 302 跳转由 `follow_redirects=true` 覆盖，不重复保留显式重定向 GET。

## 5. 运行前置条件

- 在 `CMOEM case id.csv` 的表头下补充 CMOEM 站点的有效 case ID，每行一个。
- 正式负载测试前禁用 View Results Tree，并启用 Simple Data Writer。
- 该脚本会真实修改案件权限并创建/送审 Investigation Report，只能在允许写入的测试环境运行。
