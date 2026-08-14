---
name: "jmeter-loader-skills"
description: "Automates JMeter load testing: JMX generation (template + dynamic build). Invoke when user needs JMeter/performance/load testing."
---

# JMeter 压测自动化生成脚本技能

🚀 版本: 1.0.0

## 技能概述

根据用户需求生成 JMeter 测试计划（JMX）。

## 触发条件

当用户提到以下关键词时触发此技能：

- JMeter 压测、JMeter 测试
- 性能测试、负载测试、压力测试
- JMX 文件生成
- JMeter 函数、组件配置
- JMeter 属性调优

## 参考文档索引

| 文档                                   | 说明                         |
| ------------------------------------ | -------------------------- |
| `references/component_reference.md`  | JMeter 全部 129 个组件参考（9 大类）  |
| `references/functions_reference.md`  | JMeter 全部 49 个内置函数参考（8 大类） |
| `references/best_practices.md`       | 最佳实践、测试计划结构、术语表            |
| `references/properties_reference.md` | 性能测试关键属性参考（20 大类）          |
| `references/jmx_structure.md`        | JMX XML 结构参考               |
| `references/sampler_types.md`        | Sampler 类型配置说明             |
| `references/RIRMS_Add_NIBRS_Report/RIRMS_Add_NIBRS_Report.jmx`        | 可运行的示例jmx             |
| `references/CAD_Center and MDT.jmx`        | 可运行的示例jmx             |

## 工作流程


### 步骤 1：生成文字版Jmeter 测试计划并发给用户进行预览和调整

**输入**：用户提供的.saz文件、压测需求描述
**处理**：
1. 先解析 SAZ 中的所有 HTTP 会话，并过滤非业务流量：

- 排除 SignalR 请求、轮询请求、心跳/status 检查、静态资源、版本检查、CSS/JS/image/font 文件。
- 不要排除有实际操作的请求，例如inbox页面的请求。凡是会初始化控件、dropdown、地址组件、tab 计数、流程状态的请求要保留。
- 关注实际业务操作请求，例如：表单提交、创建、更新、保存、唯一性检查、相关列表刷新请求。

2. 获取压测关键参数：

- 从请求中提取目标服务信息（主机、端口、协议）
- 确认并发策略（并发数、ramp-up 时间、持续时间）
- 确定压测场景：负载场景（目标并发持续 10～30 分钟，看稳定态）；峰值/突发（短时高并发，看限流和恢复）

**关键参数提取**：

- `target_host`: 目标主机地址
- `target_port`: 目标端口
- `protocol`: 协议类型（http/https）
- `concurrency`: 并发用户数
- `rampup`: ramp-up 时间（秒）
- `duration`: 压测持续时间（秒）

3. 生成一份中间文件：JMeter 测试计划文字版架构。根据用户的需求描述产生合理的测试计划结构，该架构应参考 JMeter 图形界面的树形结构并包含提取器等元件，易于让用户预览。

4. 完成文字版架构后，必须立即停止并把架构发给用户。
此时只能输出 .md/.txt 架构文件，严禁创建、修改、验证任何 .jmx 文件。
用户可提出修改意见，需按照意见进行修改直到用户通过该测试计划。
只有用户在后续消息中明确说“确认通过，生成JMX”或等价表达，才允许进入步骤 2。

**输出**：预览和确认后的测试计划文字版架构

#### 测试计划架构规则

1. 测试计划需包含Thread Group、Loop Controller、Transaction Controller、Sampler、Extractor、Assertion、Timer、Listener等必须的元件
2. 每个单独的事务要包在 TransactionController 里
2. 每个请求的命名格式为 <GET OR POST> <请求路径>，例如：GET /RMS/AspSoft/MasterName，不要加序号。
3. 在每个请求下列出包含的参数化决策及提取器,说明是从 response 中提取、从 CSV 文件中提取，还是使用动态随机值，使用静态值或为空则无需列出；说明要从 response 中提取哪些值。

#### 参数化规则

1. 在决定某个请求参数如何取值时，按以下优先级处理：
- 从前置 response 中提取的值优先级最高，例如 case_id、cfsID、person_id、vehicle_id、CSRF token、session 派生 ID。
- 需要每次循环变化的业务字段使用动态随机值，例如姓名、SSN、Driver License、Plate Number。
- 必须来自固定数据集的值使用 CSV 或本地文件，例如登录账号、固定地址、unit ID、agency ID。
- 当字段不是服务端动态返回值、不在动态随机字段表里时，使用 SAZ 中的静态值,例如sex、race。
2. 当saz脚本中添加了两条同类别信息时，要对其进行区分。例如：先加了Offender person信息，再加了Victim person信息。两条person信息的字段名相同，但其值不同，参数化时必须在测试计划中区分开来。
3. 遇到 __hdnTempMultisection_* 字段时，用 STX = \u0002和${STX} 拼接多行/多对象值，而不是普通逗号或固定文本。
4. 遇到 multipart 原始表单时：
- 必须保留原始 boundary、Content-Disposition、Content-Type 和 body 分段结构。
- 但仍然必须对每个 part 内容做参数化替换。
- 至少替换：case_id、report_id、template_id、FormGUID、STX、__RequestVerificationToken以及在该请求之前出现过的参数。
- 禁止因为 multipart 是 raw body 就跳过字段级参数化。
5. 遇到请求体为Json格式时，在Body Data中填写请求，不要在Parameters中填写参数。


##### 参数化优先级
在决定某个请求参数如何取值时，按以下优先级处理：
1. 从前置 response 中提取的值优先级最高，例如 cfsID、personID、vehicleID、CSRF token、session 派生 ID。
2. 需要每次循环变化的业务字段使用动态随机值，例如姓名、SSN、Driver License、Plate Number。
3. 询问用户是否有需要从本地 CSV 文件读取的参数，如果有，则使用 CSV 数据集配置。
4. 只有当字段不是用户相关、不是唯一值、也不是服务端动态返回值时，才允许继续使用 SAZ 中抓包得到的静态值。


##### 从前置 response 中提取值的规则
1. 一类请求是在前置请求中返回了一个列表，该列表包含多个值，需要从中**随机提取**一个值作为后续请求的参数。
- 例如inbox页面的case_id。
- 随机提取使用提取器Match.No = 0,不要用jsr223 postprocessor。
2. 另一类请求是在前置请求中返回了一个唯一值，该值需要在后续请求中使用。
3. ASP.NET WebForms 隐藏字段关联规则
每次 GET/POST 页面响应后，仅当响应中存在该参数时，用css提取器提取并回填：__VIEWSTATE，__VIEWSTATEGENERATOR，__EVENTVALIDATION，__RequestVerificationToken, doubleEntryTimeStamp
后续 POST 必须根据saz文件替换这些字段。

###### 弹窗选择回填型请求识别规则
当业务表现为“输入关键字 -> 弹窗列表 -> 选择一条记录 -> 弹窗关闭 -> 主页面字段被回填 -> 保存 POST”时，必须按数据依赖生成 JMX，不能只复制抓包 POST 中的固定值。

识别条件：
- 前置请求返回 HTML/JSON 列表，URL 或参数常见特征包括 `listPopup`、`Popup`、`lookup`、`search`、`statute`、`charge`。
- 列表响应中存在候选记录值，后续 POST body 中出现这些候选记录拆分后的字段值。
- 候选记录被选择后，后续 1 到 5 个请求可能出现补充接口，例如 grade、NIBRS、NCIC、smart code 查询。
- 如果满足以上条件，判定为“弹窗选择回填型请求”，在列表请求后添加 Extractor随机获取列表中的一项数据，并在保存 POST 前使用提取值替换固定值。

候选记录来源按以下顺序识别：
1. Hidden input 型：
   - 示例：`name="return_value~|list~|D" value="..."`
   - 推荐正则：`name="return_value~\|list~\|D"[^>]+value="([^"]+)"`
2. CloseDialog 链接型：
   - 示例：`JavaScript:CloseDialog(&#39;...&#39;)`
   - 推荐正则：`CloseDialog\(&#39;(.+?)&#39;\)`
   - 也兼容：`CloseDialog\('(.+?)'\)`

候选值提取后必须先做 URL Decode 和 HTML Decode，再按 `~` 拆分。

##### 动态随机参数识别规则

当 POST 请求体中包含以下字段，并且 SAZ 抓包中该字段有非空值时，在最近的业务 `Loop Controller` 下添加一个 `User Parameters` 元件，并把它放在相关请求之前，作为该循环里的第一步。

字段匹配时不区分大小写，并识别常见字段名变体：

| 业务字段 | 匹配示例 | 生成变量名 | 默认生成规则 |
|---|---|---|---|
| First Name | `FirstName`, `firstName`, `first_name` | `firstName` | `TEST${__Random(1000,9999)}` |
| Last Name | `LastName`, `lastName`, `last_name` | `lastName` | `TEST${__Random(1000,9999)}` |
| SSN | `Ssn`, `SSN`, `ssn` | `ssn` | `${__Random(100,999)}-${__Random(10,99)}-${__Random(1000,9999)}` |
| Driver License | `DriverLicense`, `driverLic`, `driver_license` | `driverLicense` | `DL${__Random(100000,999999)}` |
| Plate Number | `PlateNo`, `plateNo`, `PlateNumber`, `plate_no` | `plateNo` | `P${__Random(100000,999999)}` |

在测试计划文字版架构中，应体现为：

```text
Loop Controller: Business Iteration
|-- User Parameters: Generate Dynamic Person/Vehicle Data
|   |-- firstName = TEST${__Random(1000,9999)}
|   |-- lastName = TEST${__Random(1000,9999)}
|   |-- ssn = ${__Random(100,999)}-${__Random(10,99)}-${__Random(1000,9999)}
|   |-- driverLicense = DL${__Random(100000,999999)}
|   |-- plateNo = P${__Random(100000,999999)}
|-- HTTP Request: uniqueness check
|-- HTTP Request: submit/save
```
然后把请求中抓包得到的固定值替换成变量引用：
- 将 FirstName=<抓包值> 替换为 FirstName=${firstName}
- 将 LastName=<抓包值> 替换为 LastName=${lastName}
- 将 Ssn=<抓包值> 或 ssn=<抓包值> 替换为 ${ssn}
- 将 DriverLicense=<抓包值> 或 driverLic=<抓包值> 替换为 ${driverLicense}
- 将 PlateNo=<抓包值> 或 plateNo=<抓包值> 替换为 ${plateNo}
如果同一个业务值同时出现在唯一性校验请求和提交请求中，这两个请求必须引用同一个变量。不要在多个 HTTP Sampler 中分别直接写随机函数。

2. 字段分类必须按精确字段名匹配和已知业务字段映射进行处理。不能使用模糊匹配。

- 对 `xxx~|xxx_xxx~|A_xxx` 这类字段，第一个 `~|` 前面的部分是字段名，此外有些字段最后一个|后面的部分也是字段名的一部分。
- 例如：
  - `driver_license_state~|person_add~|A` -> `driver_license_state`
  - `driver_license~|person_add~|A` -> `driver_license`
  - `driver_license_expire_date~|person_add~|A` -> `driver_license_expire_date`
  - `driver_license_expire_date~|person_add~|A_txtDate` -> `driver_license_expire_date_txtDate`

不要用 `contains("driver_license")` 直接把所有字段都识别成 Driver License。

3. 如果同一个业务值同时出现在唯一性校验请求和提交请求中，这两个请求必须引用同一个变量。不要在多个 HTTP Sampler 中分别直接写随机函数。
4. 在 JMeter 测试计划文字版架构中如果包含动态随机参数，必须包含类似下面的单独章节：
- lastName / firstName: 通过 User Parameters 生成，规则 TEST${__Random(1000,9999)}
- ssn / Driver License / Plate Number: 通过 User Parameters 生成，规则 xxxxxx

##### 从 csv 中提取值的规则
1. UserName，RegionID(region_id)，StaffID(staff_id)，UnitID(unit_id)等字段必须从 csv 文件中提取。当saz文件出现这些字段时，生成csv文件放在 JMeter 测试计划同级目录下，脚本中参数值从csv文件中读取。
2. inbox_staff_id应被参数化为当前登录用户的staff_id
##### 从saz 文件中提取静态值的规则

1. 以下字段应该使用 SAZ 中的静态值，不能替换，无需参数化。

driver_license_state，driver_license_expire_date，driver_license_expire_date_txtDate
division_id, inbox_sub_id，division_id, device_info, template_id

2. 若无特殊说明，地址(location/address)相关的字段使用静态值。

#### 断言规则：
   - 不要添加任何断言。
   - 列举出所有建议添加断言的请求以及建议添加的断言内容。

### 步骤 2：JMX 测试计划生成

**输入**：用户提供的.saz文件和用户通过的最终版测试计划架构
**处理**：
1. 选择动态组装模式：根据最终版测试计划架构和组件列表构建 JMX，相关数据从.saz文件和用户补充的信息中提取。
2. 验证 JMX 结构完整性
**输出**：在当前文件夹输出完整可执行的 JMX 测试计划文件  

**生成模式**：

| 模式   | 适用场景        | 命令示例                                                                       |
| ---- | ----------- | -------------------------------------------------------------------------- |
| 动态组装 | 多接口、自定义组件组合 | `python generate_jmx.py --build --output test.jmx --http-sampler ...`      |

**动态组装模式支持的组件**（8 大类 24 种）：

| 类别          | 组件                                                                                                     |
| ----------- | ------------------------------------------------------------------------------------------------------ |
| Samplers    | http\_sampler, debug\_sampler                                                                          |
| Controllers | if\_controller, transaction\_controller, once\_only\_controller, loop\_controller, foreach\_controller |
| Timers      | constant\_timer, gaussian\_timer, uniform\_timer, synchronizing\_timer                                 |
| Extractors  | json\_extractor, boundary\_extractor, regex\_extractor                                                 |
| Assertions  | response\_assertion, duration\_assertion, json\_assertion                                              |
| Config      | http\_defaults, header\_manager, cookie\_manager, cache\_manager, csv\_data\_set                       |
| Processors  | jsr223\_postprocessor, jsr223\_preprocessor                                                            |
| Listeners   | result\_collector, backend\_listener\_influxdb                                                         |

**动态组装示例**：
把最终文字计划映射成 generate_jmx.py --build 参数，调用generate_jmx.py来组装jmx脚本。只有当最终测试计划包含现有生成器无法表达的结构时，才创建一次性辅助脚本，并说明“为什么不用现有生成器”。

```bash
python generate_jmx.py --build --output test.jmx \
  --param target_host=api.example.com \
  --http-sampler name=GetUsers,path=/api/users,method=GET \
  --http-sampler name=CreateOrder,path=/api/orders,method=POST,body='{"item":"test"}' \
  --timer timer_type=gaussian,delay_ms=300,range_ms=100 \
  --assertion type=response,patterns=200 \
  --backend-listener type=influxdb,influxdb_url=http://localhost:8086
```

**JMX 生成规范**：

1. **强制要求**：
   - 参照步骤 2 生成文字版Jmeter 测试计划
   - 所有压测参数使用 ${__P(propname,default)} 形式，default 为默认值，propname 为属性名。
   - 数据集参数使用 ${__CSVRead(file,variable)} 形式，文件第一行为参数名
   - 所有的HTTP Request Sampler必须Follow redirects = true。 POST请求若使用Parameters，必须设置 HTTPArgument.always_encode=true。
   - 当请求头包含“Referer”时，说明这个请求会重定向，要考虑提取器是否应该选择“Main sample and sub-samples”而非“Main sample only”。

2. **必需组件**：
   - **ThreadGroup（线程组）**：
     - `num_threads`: `${__P(concurrency,10)}`
     - `ramp_time`: `${__P(rampup,10)}`
     - `scheduler`: `true`
     - `duration`: `${__P(duration,60)}`
     - `on_sample_error`: `continue`
   - **ResultCollector（结果收集器）**：
     - 配置为保存 .jtl 格式结果
     - 启用所有必需字段：timeStamp, elapsed, label, responseCode, responseMessage, threadName, dataType, success, failureMessage, bytes, sentBytes, grpThreads, allThreads, URL, Latency, IdleTime, Connect
3. **支持的 Sampler 类型**：
   - HTTP Request Sampler（默认）
   - JDBC Request Sampler
   - TCP Sampler
   - Java Request Sampler
   - FTP Request Sampler
   - SMTP Sampler
   - LDAP Request Sampler
   - JMS Publisher/Subscriber/Point-to-Point
   - OS Process Sampler
   - JSR223 Sampler
   - Bolt Request（Neo4j）
4. **组件选择指南**：
   | 需求场景     | 推荐组件                                                               |
   | -------- | ------------------------------------------------------------------ |
   | API 接口压测 | HTTP Request + HTTP Header Manager                                 |
   | 数据库压测    | JDBC Request + JDBC Connection Configuration                       |
   | 需要鉴权的接口  | HTTP Request + HTTP Cookie Manager + JSON Extractor                |
   | 数据驱动测试   | HTTP Request + CSV Data Set Config                                 |
   | 业务流程压测   | Transaction Controller + Once Only Controller                      |
   | 条件分支     | If Controller（使用 `${__jexl3()}`）                                   |
   | 循环遍历     | ForEach Controller + Regular Expression Extractor                  |
   | 并发同步     | Synchronizing Timer                                                |
   | 思考时间     | Gaussian Random Timer / Uniform Random Timer                       |
   | 吞吐量控制    | Precise Throughput Timer                                           |
   | 响应验证     | Response Assertion / JSON Assertion / Duration Assertion           |
   | 数据提取     | JSON Extractor / Boundary Extractor / Regular Expression Extractor |
   | 实时监控     | Backend Listener（Graphite/InfluxDB）                                |

- 对于POST 请求，若无特殊规定，尽量使用parameters而不是 body data，使每个参数的"HTTPArgument.always_encode"=true
- 对于提取器，尽量使用元素的objectname属性进行定位

## 脚本使用指南

### generate\_jmx.py

用于根据参数动态生成 JMX 文件。

**用法**：

```bash
python generate_jmx.py --template base.jmx --output test.jmx \
  --param target_host=example.com \
  --param target_port=80 \
  --param concurrency=50 \
  --param duration=300
```

**参数**：

- `--template`: 模板文件名（位于 assets/templates/）
- `--output`: 输出 JMX 文件路径
- `--param`: 参数键值对，可多次使用




## JMeter 内置函数速查

### 常用函数

| 函数               | 语法                                    | 用途                          |
| ---------------- | ------------------------------------- | --------------------------- |
| `__P`            | `${__P(prop,default)}`                | 读取属性（命令行覆盖）                 |
| `__property`     | `${__property(prop,var,default)}`     | 读取属性（完整版）                   |
| `__setProperty`  | `${__setProperty(prop,value,)}`       | 设置属性（线程间通信）                 |
| `__time`         | `${__time(format,)}`                  | 获取当前时间                      |
| `__timeShift`    | `${__timeShift(format,date,shift,,)}` | 时间偏移                        |
| `__Random`       | `${__Random(min,max,)}`               | 随机整数                        |
| `__RandomString` | `${__RandomString(len,chars,)}`       | 随机字符串                       |
| `__UUID`         | `${__UUID()}`                         | 生成 UUID                     |
| `__counter`      | `${__counter(TRUE,)}`                 | 递增计数器                       |
| `__V`            | `${__V(Var${N},)}`                    | 嵌套变量引用                      |
| `__groovy`       | `${__groovy(expr,)}`                  | Groovy 脚本                   |
| `__jexl3`        | `${__jexl3(expr,)}`                   | JEXL3 表达式（If Controller 推荐） |
| `__digest`       | `${__digest(algo,str,,,)}`            | 哈希摘要                        |
| `__split`        | `${__split(str,var,delim)}`           | 字符串拆分                       |
| `__eval`         | `${__eval(${var})}`                   | 表达式求值                       |
| `__log`          | `${__log(msg,level,,)}`               | 日志记录                        |
| `__threadNum`    | `${__threadNum}`                      | 当前线程号                       |
| `__machineIP`    | `${__machineIP}`                      | 本机 IP                       |

### 脚本语言性能排序

**Groovy（JSR223 + 缓存）> JEXL3 > JavaScript > BeanShell**

关键：使用 JSR223 元素时务必勾选 "Cache compiled script if available"，且脚本内使用 `vars.get("varName")` 而非 `${varName}`。

## JMeter 组件速查

### 执行顺序

1. Configuration elements → 2. Pre-Processors → 3. Timers → 4. Sampler → 5. Post-Processors → 6. Assertions → 7. Listeners

### 作用域规则

- 层次型元素（Listeners、Config、Post/Pre-Processors、Assertions、Timers）：应用于其父元素及所有后代
- 有序型元素（Controllers、Samplers）：按树中出现的顺序处理
- Manager 类元素（Header/Cookie/Authorization Manager）不合并，只使用一个

### 常用控制器

| 控制器                         | 用途                          |
| --------------------------- | --------------------------- |
| If Controller               | 条件分支（推荐 `${__jexl3()}` 表达式） |
| While Controller            | 循环直到条件为 false               |
| ForEach Controller          | 遍历变量组                       |
| Transaction Controller      | 测量事务总耗时                     |
| Once Only Controller        | 仅执行一次（如登录）                  |
| Loop Controller             | 循环执行                        |
| Throughput Controller       | 控制执行频率                      |
| Critical Section Controller | 线程互斥锁                       |
| Module Controller           | 引用测试片段                      |
| Include Controller          | 引用外部 JMX                    |

### 常用提取器

| 提取器                          | 适用场景                   |
| ---------------------------- | ---------------------- |
| JSON Extractor               | JSON 响应提取（JSON Path）   |
| JSON JMESPath Extractor      | JSON 响应提取（JMESPath）    |
| Boundary Extractor           | 简单边界提取（无需正则）           |
| Regular Expression Extractor | 通用正则提取                 |
| CSS Selector Extractor       | HTML 提取（CSS 选择器）       |
| XPath Extractor              | XML/HTML 提取（XPath，推荐） |

### 常用断言

| 断言                      | 用途           |
| ----------------------- | ------------ |
| Response Assertion      | 响应码/消息/文本断言  |
| JSON Assertion          | JSON Path 断言 |
| JSON JMESPath Assertion | JMESPath 断言  |
| Duration Assertion      | 响应时间断言       |
| Size Assertion          | 响应大小断言       |


### 常用定时器

| 定时器                      | 特点        |
| ------------------------ | --------- |
| Constant Timer           | 固定延迟      |
| Gaussian Random Timer    | 高斯分布随机延迟  |
| Uniform Random Timer     | 均匀分布随机延迟  |
| Precise Throughput Timer | 精确吞吐量控制   |
| Synchronizing Timer      | 并发同步（集合点） |
| Poisson Random Timer     | 泊松分布随机延迟  |
