# SAZ/Fiddler 会话分析与文字计划规则

## 目录

- [输入与输出](#输入与输出)
- [过滤非业务流量](#过滤非业务流量)
- [提取压测参数](#提取压测参数)
- [设计文字版测试树](#设计文字版测试树)
- [认证与初始化流程](#认证与初始化流程)
- [请求说明契约](#请求说明契约)
- [断言处理](#断言处理)

## 输入与输出

输入为用户提供的 `.saz` 文件或 Fiddler HTTP 会话以及压测需求描述。输出为便于用户审阅的 `.md` 文字版 JMeter 测试树；本阶段不得生成JMX。

## 过滤非业务流量

解析全部 HTTP 会话，并按业务作用判断是否保留：

- 排除 SignalR、轮询、心跳或 status 检查、版本检查以及 CSS、JavaScript、图片、字体等静态资源。
- 保留会初始化控件、dropdown、地址组件、tab 计数或流程状态的页面请求，例如具有实际初始化作用的 inbox 页面请求。
- 保留表单提交、创建、更新、保存、唯一性检查和相关列表刷新等业务操作。
- 保留打开case的步骤，即使用户单独提供了case_id。

## 提取压测参数

从捕获和用户需求确定：

- `target_host`：目标主机。
- `target_port`：目标端口。
- `protocol`：`http` 或 `https`。
- `concurrency`：并发用户数。
- `rampup`：加压时间，单位秒。
- `duration`：持续时间，单位秒。

同时明确场景类型：

- 稳定负载：达到目标并发后通常持续 10～20 分钟，观察稳定态。
- 峰值或突发：短时高并发，每个线程只执行一次。观察限流、错误和恢复。

缺少并发策略时使用并发数=1,rampup=1,duration=600。并在文字计划的“待用户确认”章节集中列出；不得在生成计划前逐项追问。

## 设计文字版测试树

文字计划使用 JMeter GUI 树形结构表达，并满足：

1. 包含适用于当前场景的 Thread Group、业务 Loop Controller、Transaction Controller、Sampler、Extractor、Timer 和 Listener。
2. 每个独立业务事务放在 Transaction Controller 中。
3. 请求名称采用 `<METHOD> <实际路径> <用途>`，使用英文，不加序号。所有请求名称、方法、路径、headers、params、body 和业务步骤必须来自捕获内容及用户批准的计划；不得复制示例文件中的业务值。
4. Controller、Sampler 及其子元件按实际执行顺序排列。
5. 只加入捕获内容和需求能够证明需要的组件，不为满足组件清单创建空节点。
6. HTTP Request Sampler 均使用 `follow_redirects=true`
7. 所有阶段一律忽略 Referer 请求头，不得在测试计划、Scenario JSON 或 JMX 中生成或重建。删除 Referer 后 Header Manager 为空时，不生成该 Header Manager。

## 认证与初始化流程

如果捕获和需求包含每线程执行一次的登录、SSO、Disclaimer、Division 选择或受保护页面初始化流程：

- 把完整流程放在 `Once Only Controller` 的子树中。
- 不要创建空的 Once Only Controller。
- 不要把认证请求放在线程组同级。
- Cookie Manager 使用 `clear_each_iteration=false`。

`Once Only Controller` 是每个线程执行一次，不是整个测试只执行一次。如果捕获内容没有认证或初始化流程，不得从示例推断或自行补充。

## 请求说明契约

在每个请求下列出：

- 来自前置响应的变量及其提取器。
- 来自 CSV Data Set 的列。
- 每轮动态生成的随机变量。
- 同一业务值被哪些请求共同复用。
- 特殊 body 编码、multipart 或 WebForms 关联要求。

静态值和空值通常无需逐项列出，但不得因此遗漏可能造成跨线程冲突或失效的字段。

## 断言处理

本工作流不把断言加入文字计划或生成的 JMX。单独列出建议添加断言的请求、验证字段和期望内容，供用户选择添加。

- 建议用户在Login请求后断言验证是否正确打开home页。
- 对于关键的POST请求，建议用户在后续页面断言验证数据是否成功添加/返回。
- 不要建议添加任何仅判断返回是否是200的断言。
