# SAZ 参数化与关联规则

## 目录

- [取值优先级](#取值优先级)
- [前置响应关联](#前置响应关联)
- [弹窗选择回填](#弹窗选择回填)
- [动态随机字段](#动态随机字段)
- [CSV 数据](#csv-数据)
- [静态字段](#静态字段)
- [复杂请求体](#复杂请求体)

## 取值优先级

按以下顺序决定参数来源：

1. 前置响应返回的动态值，例如 case ID、person ID、vehicle ID、CSRF token 和 session 派生 ID。
2. 每次业务循环必须变化的字段，例如姓名、SSN、Driver License 和 Plate Number。
3. 固定数据集提供的账号或组织数据，例如用户名、地址、unit ID 和 agency ID。
4. 当字段不是用户相关值、唯一值或服务端动态值，或用户指定无需参数化时，保留 SAZ 中的静态值。
5. 若无明确说明，不能添加JDBC从数据库中取值。

同一类别出现多个业务对象时使用带角色或序号语义的不同变量，例如 offender 与 victim；不得因为字段名相同而复用错误值。

## 前置响应关联

- 前置响应返回候选列表时，使用提取器随机选择一项；JMeter 提取器使用 `Match No. = 0`，不要为了随机选择添加 JSR223 PostProcessor。
- 前置响应返回唯一值时，提取为单值变量供后续请求复用。
- 每次 GET/POST 页面响应后，仅当响应包含对应字段时，使用 CSS 提取器提取 ASP.NET WebForms 隐藏字段：`__VIEWSTATE`、`__VIEWSTATEGENERATOR`、`__EVENTVALIDATION`、`__RequestVerificationToken`、`doubleEntryTimeStamp`。
- 后续 POST 仅替换捕获中实际出现并且已提取的隐藏字段。
- `inbox_staff_id` 参数化为当前登录用户的 `staff_id`。

## 弹窗选择回填

根据用户需求，当用户需要为流程“输入关键字 → 弹窗列表 → 选择记录 → 主页面回填 → 保存 POST”参数化时，按数据依赖生成，不能复制抓包中的固定候选值。

识别信号包括：

- 前置 HTML/JSON 返回候选列表，URL 或参数包含 `listPopup`、`Popup`、`lookup`、`search`、`statute` 或 `charge` 等特征。
- 后续 POST 包含候选记录拆分后的字段值。
- 选择后 1～5 个请求出现 grade、NIBRS、NCIC 或 smart code 等补充查询。

候选记录优先从以下形式提取：

1. Hidden input：`name="return_value~|list~|D" value="..."`
   - 正则：`name="return_value~\|list~\|D"[^>]+value="([^"]+)"`
2. CloseDialog 链接：`JavaScript:CloseDialog(&#39;...&#39;)`
   - 正则：`CloseDialog\(&#39;(.+?)&#39;\)`
   - 兼容：`CloseDialog\('(.+?)'\)`

提取候选值后先进行 URL Decode 和 HTML Decode，再按 `~` 拆分。

## 动态随机字段

当 POST body 中以下字段存在非空捕获值时，在最近的业务 Loop Controller 中、相关请求之前添加一个 User Parameters 元件：

| 业务字段 | 精确匹配示例 | 变量 | 默认生成规则 |
|---|---|---|---|
| First Name | `FirstName`, `firstName`, `first_name` | `firstName` | `TEST${__Random(1000,9999)}` |
| Last Name | `LastName`, `lastName`, `last_name` | `lastName` | `TEST${__Random(1000,9999)}` |
| SSN | `Ssn`, `SSN`, `ssn` | `ssn` | `${__Random(100,999)}-${__Random(10,99)}-${__Random(1000,9999)}` |
| Driver License | `DriverLicense`, `driverLic`, `driver_license` | `driverLicense` | `DL${__Random(100000,999999)}` |
| Plate Number | `PlateNo`, `plateNo`, `PlateNumber`, `plate_no` | `plateNo` | `P${__Random(100000,999999)}` |

字段分类使用精确字段名和已知映射，不使用模糊包含判断。对于 `xxx~|xxx_xxx~|A_xxx` 形式，第一个 `~|` 前为基础字段名；最后一个 `|` 后的后缀有时也是字段名的一部分。例如：

- `driver_license_state~|person_add~|A` → `driver_license_state`
- `driver_license~|person_add~|A` → `driver_license`
- `driver_license_expire_date~|person_add~|A_txtDate` → `driver_license_expire_date_txtDate`

不要用 `contains("driver_license")` 把相关字段全部识别为 Driver License。同一业务值用于唯一性检查和提交时，所有请求引用同一个变量，不要在多个 Sampler 中分别调用随机函数。

文字计划包含动态随机参数时，增加独立参数化章节，列出变量、生成位置、生成规则和使用请求。

## CSV 数据

- `UserName`、`RegionID`/`region_id`、`StaffID`/`staff_id`、`UnitID`/`unit_id` 等固定数据集字段使用 CSV Data Set Config。
- 生成 CSV 文件并放在 JMX 同级目录；第一行是列名。
- 请求通过 `${column_name}` 引用 CSV Data Set 变量，不要同时使用 `__CSVRead` 读取同一文件。
- 其他 CSV 字段由用户提供的数据集需求决定。

## 静态字段

在没有更高优先级动态来源时，下列字段保留 SAZ 静态值：

- `driver_license_state`
- `driver_license_expire_date`
- `driver_license_expire_date_txtDate`
- `division_id`
- `inbox_sub_id`
- `device_info`
- `template_id`

若捕获证明这些字段来自前置响应，仍按前置响应关联规则处理。没有特殊要求时，location/address 相关字段保持静态。

## 复杂请求体

### Multisection

遇到 `__hdnTempMultisection_*` 字段时，使用 STX（`\u0002`）和 `${STX}` 拼接多行或多对象值，不使用普通逗号或固定拼接文本。

### Multipart

- 保留原始 boundary、Content-Disposition、Content-Type 和分段结构。
- 对每个 part 内容继续进行参数化替换。
- 至少替换已在前置响应或当前上下文确定的 case ID、report ID、FormGUID、STX、`__RequestVerificationToken` 及其他依赖值。
- 不得因为 multipart 使用 raw body 就跳过字段级参数化。

### JSON

JSON 请求写入 Body Data，不放在 Parameters 中。
