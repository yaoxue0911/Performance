我看完了 `Performance/jmeter-loader-skills介绍.md`。这个文件现在更像“项目说明笔记”，如果直接按原顺序讲，**参数化 → 传统流程 → 问题 → AI流程 → Skill结构 → Agent** 会稍微散。更适合 PPT 的叙事顺序是：

**为什么做 → 原来怎么做 → 痛点是什么 → 现在怎么做 → Skill 怎么实现 → 两阶段怎么工作 → 参数怎么处理 → Agent 怎么扩展 → 实际案例 → 总结。**

我建议做成 **10 页主内容**。

---

# 第 1 页：项目介绍

### 标题

**jmeter-loader-skills**

### 副标题

**利用 AI 自动理解 Fiddler 抓包中的业务请求，并转换为 JMeter 性能测试脚本**

### 页面内容

只放一句核心流程：

```text
Fiddler file
      ↓
SKILL
      ↓
JMeter Script
```

### 演讲重点

先让别人知道这是做什么的：

> 我们原来需要人工分析 Fiddler 抓包、参数化、关联并组织 JMeter 脚本。这个项目把这些经验整理成 Skill，让 AI 根据业务请求自动生成可执行的 JMeter 脚本。

这一页不要讲技术细节。

---

# 第 2 页：人工分析在分析什么

### 标题

**人工分析在分析什么**
### 副标题

**参数化与关联**


左边：

### 参数化

```text
case_id=12345

        ↓

case_id=${case_id}
```

说明：

> 把固定写死的数据转换成测试运行时可以变化的数据。

右边：

### 关联

用你已经做过的 Inbox 例子：

```text
GET Inbox

从请求的返回中提取出参数
${case_id}

     ↓

在后续请求中使用 GET Case
case_id=${case_id}
```

---

# 第 3 页：人工分析在分析什么

### 标题

**人工分析在分析什么**
### 副标题

**传统 JMeter 脚本生成方式**


* 判断哪些字段需要参数化；
* 找出请求之间的关联；
* 根据测试目的调整脚本结构；
* 给不同站点做特殊处理。


### ① 测试压力容易被分散

例如：

```text
Login
 ↓
Home
 ↓
Add Case
```

如果目标是：

> 多用户持续 Add Case

每轮都重新 Login，就会把压力分散到 Login。

所以脚本结构应该根据**测试目标**变化。

---

### ② 同一个功能在不同站点不完全相同

例如：

```text
Report

Site A → template_id = A
Site B → template_id = B
```

页面、参数、业务逻辑都可能不同。

---

### ③ 人工处理容易出错

Offender_id
---

页面最下面一句：

> **同一个固定脚本无法适应所有性能测试场景。**


---

# 第 5 页：解决方案——把经验变成 Skill

### 标题

**从人工经验到 jmeter-loader-skills**

建议中间画：

```text
人工经验
│
├─ 哪些请求应该保留
├─ 哪些参数需要变化
├─ 哪些数据需要关联
├─ Transaction 如何组织
├─ Loop 如何组织
└─ 不同测试目标如何处理
          ↓
    jmeter-loader-skills
          ↓
          AI
```

演示具体效果

---

# 第 6 页：Skill 整体架构

### 标题

**jmeter-loader-skills Architecture**

这里直接使用之前生成的**系统架构图**。

重点只讲三个部分：

```text
SKILL.md
   │
   ├── 阶段 1 references
   │
   └── 阶段 2 references

assets
   ├── JSON examples
   └── JMX examples

scripts
   └── Generator
```

### 演讲重点

重点解释为什么采用：

**主 Skill + references**

原因：

> Skill 内容很多，没有必要每次全部加载。主 Skill 控制流程，只在进入对应阶段时加载需要的 references。

然后自然引出：

```text
阶段 1
Fiddler → 测试计划

阶段 2
测试计划 → JSON → JMX
```

---

# 第 7 页：阶段 1——AI 理解 Fiddler

### 标题

**阶段 1：Fiddler → 测试计划**

这里使用前面生成的**阶段 1 图片**。


### 演讲重点

这一阶段的输出是**人能直接读懂的测试计划**。

因此可以在真正生成 JMX 前检查：

* 请求有没有遗漏；
* 参数化是否合理；
* 关联关系是否正确；
* 脚本结构 是否合理；
* 测试压力是否符合目标。
* 是否要添加断言

这个“用户审阅测试计划”的设计在文档的 Skill 结构里也有明确描述。

---

# 第 8 页：参数化策略

### 标题

**不同的数据，采用不同的参数化方式**

这一页非常值得保留，因为这是这个项目真正体现“业务判断”的地方。

建议做成 5 个卡片：

| 类型     | 示例                           | 处理方式               |
| ------ | ---------------------------- | ------------------ |
| 文件数据   | Username / Password          | CSV                |
| 动态随机参数 | Person Name / Driver License | Random             |
| 静态值    | Sex / Race                   | 保留 Fiddler 值       |
| 关联参数   | person_id / case_id          | Response Extractor |
| 特殊参数   | 特殊编码或组合字段                    | 专门规则               |

然后用 Person 例子串起来：

```text
Username / Password
        ↓
CSV

Person Name / Driver License
        ↓
Random

Sex / Race
        ↓
Captured Value

Add Person Response
        ↓
Extract ${person_id}

Create Report
        ↓
person_id=${person_id}
```

这部分几乎就是 `jmeter-loader-skills介绍.md` 中参数化设计的核心。

---

# 第 9 页：阶段 2——测试计划变成 JMeter Script

### 标题

**阶段 2：数据形式变化**

这一页放刚才生成的：

**阶段 2：数据形式变化**


这里重点解释为什么需要 JSON。

文件里的设计思路非常适合作为讲稿：

> JMeter Script 本质上是 XML。测试计划描述的是业务逻辑，不能直接稳定地生成复杂 XML，因此先转换为结构化 JSON。JSON 提供组件需要的属性，Generator 再结合默认属性生成最终 JMX。

然后下一页继续放你刚生成的第二张图。

---

# 第 10 页：阶段 2——关联和树结构如何保存

### 标题

**关联 + 树结构如何保存**

直接使用刚生成的：

**Inbox → `${case_id}` → Incident Summary**

这一页主要讲两个东西。

### 关联

```text
前置请求
GET Inbox

    ↓ Extract

${case_id}

    ↓

后续请求
case_id=${case_id}
```

### 树结构

```text
Scenario JSON

HTTP Sampler
└── children
    └── Extractor
```

最终映射成：

```text
JMX

HTTPSamplerProxy
└── hashTree
    └── Extractor
```

### 演讲重点

一句话：

> JSON 不只保存请求参数，还保存 JMeter 组件之间的父子关系；Generator 根据这个树形结构生成对应的 JMX XML。



---

# 第 11 页：编写SKILL的经验

1. 拆分
参照日常工作流的思路，把复杂的大 Skill 拆分成多个轻量化小 Skill，再按流程串联调用。
或者按步骤拆成多个独立的SKILL
2. 固化脚本
如果生成的内容是固化的（例如通过公式计算结果、已知元件属性生成Jmx脚本），建议固化成脚本而不是靠大模型对话去输出。
3. 验证
之前我的SKILL没有验证的步骤，但因为我用的模型可能比较注重自测和验证，所以即使脚本里有错误，AI也会自己改正错误 输出正确的版本。
这也导致我一直没有发现这个SKILL里存在一个bug。
但有些模型可能不会自己验证，所以我们最好自己添加验证的部分。
