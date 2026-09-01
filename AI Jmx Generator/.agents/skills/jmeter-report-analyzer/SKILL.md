---
name: "jmeter-report-analyzer"
description: "Automates JMeter load testing: test execution, result parsing, and optimization. Invoke when user needs JMeter/performance/load testing."
---

# JMeter 压测自动化分析技能

🚀 版本: 2.0.0

## 技能概述

根据用户需求生成 JMeter 测试计划（JMX）。

## 触发条件

当用户提到以下关键词时触发此技能：

- JMeter 压测、JMeter 测试
- 压测结果分析
- 性能优化建议
- 分布式压测
- HTML 报告生成


## 参考文档索引

| 文档                                   | 说明                         |
| ------------------------------------ | -------------------------- |
| `references/best_practices.md`       | 术语表            |
| `references/distributed_testing.md`  | 分布式测试完整指南                  |
| `references/dashboard_report.md`     | HTML 仪表板报告生成、JTL 格式        |
| `references/properties_reference.md` | 性能测试关键属性参考（20 大类）          |

## 工作流程

### 步骤 1：压测执行与监控

**输入**：生成的 JMX 文件路径、可选的运行时参数
**处理**：

1. 检查 JMeter 环境（版本 5.4+）
2. 构建 JMeter CLI 命令
3. 执行压测（支持分布式压测）
4. 实时监控执行状态
5. 处理执行错误和异常
   **输出**：JTL 结果文件、JMeter 日志文件

**JMeter 执行命令规范**：

1. **基础命令格式**：
   ```bash
   jmeter -n -t ${jmx_file_path} -l ${result_jtl_path} -j ${jmeter_log_path}
   ```
2. **分布式压测配置**：
   ```bash
   jmeter -n -t test.jmx -l result.jtl -r -R slave1,slave2,slave3
   ```
3. **命令参数说明**：
   - `-n`: 非 GUI 模式运行
   - `-t`: 指定 JMX 文件路径
   - `-l`: 指定结果文件（JTL）路径
   - `-j`: 指定日志文件路径
   - `-G`: 在所有服务器上定义属性（分布式模式）
   - `-r`: 启动远程服务器
   - `-R`: 指定远程服务器列表
   - `-X`: 测试结束后退出远程服务器
   - `-q`: 加载额外属性文件
   - `-e`: 测试结束后生成 HTML 报告
   - `-o`: HTML 报告输出目录
4. **环境检查**：
   - 执行前检查 `jmeter --version` 确认版本 >= 5.4
   - 验证 JMX 文件存在且格式正确
   - 确认输出目录有写入权限
5. **HTML 报告生成**：
   ```bash
   # 测试后自动生成
   jmeter -n -t test.jmx -l result.jtl -e -o report/

   # 从已有 JTL 生成
   jmeter -g result.jtl -o report/
   ```

### 步骤 2：结果解析与报告生成

**输入**：JTL 结果文件路径
**处理**：

1. 读取并解析 JTL 文件（CSV 或 XML 格式）
2. 计算核心性能指标
3. 生成多维度分析报告
4. 检测性能异常
   **输出**：结构化的性能报告、异常检测结果

**结果解析规范**：

1. **核心聚合指标**：
   - **Average（平均响应时间）**: 所有请求的平均响应时间（毫秒）
   - **TP90（90% 响应时间）**: 90% 的请求在此时间内完成（毫秒）
   - **TP95（95% 响应时间）**: 95% 的请求在此时间内完成（毫秒）
   - **TP99（99% 响应时间）**: 99% 的请求在此时间内完成（毫秒）
   - **Min（最小响应时间）**: 最快的请求响应时间（毫秒）
   - **Max（最大响应时间）**: 最慢的请求响应时间（毫秒）
   - **Error%（错误率）**: 失败请求占总请求的百分比
   - **Throughput（吞吐量）**: 每秒处理的请求数（requests/sec）
   - **Received KB/sec**: 每秒接收的数据量
   - **Sent KB/sec**: 每秒发送的数据量
2. **多维度分析**：
   - **按请求标签分组**: 分析每个接口的性能表现
   - **时间趋势分析**: 响应时间和吞吐量随时间的变化趋势
   - **错误类型统计**: 统计不同错误类型的分布
   - **并发与响应时间关系**: 分析并发数对响应时间的影响
3. **JTL 文件格式**：
   - 默认使用 CSV 格式，字段顺序：
     timeStamp,elapsed,label,responseCode,responseMessage,
     threadName,dataType,success,failureMessage,bytes,
     sentBytes,grpThreads,allThreads,URL,Latency,IdleTime,Connect
4. **JMeter 术语说明**：
   - **Elapsed Time**: 从发送请求前到接收最后一个响应后的时间（不含渲染和 JS 执行）
   - **Latency**: 从发送请求前到接收第一个响应后的时间
   - **Connect Time**: 建立连接所需时间（含 SSL 握手），不会从 Latency 中减去
   - **Throughput**: 请求数 / 总时间（从第一个样本到最后一个样本）

### 步骤 3：优化建议提供

**输入**：性能报告、异常检测结果
**处理**：

1. 评估系统性能瓶颈
2. 分析根本原因
3. 提供针对性优化建议
4. 制定迭代优化方案
   **输出**：详细的优化建议报告

**性能评估标准**：

| 指标        | 优秀      | 良好      | 一般   | 需优化   |
| --------- | ------- | ------- | ---- | ----- |
| 平均响应时间    | < 200ms | < 500ms | < 1s | >= 1s |
| TP90 响应时间 | < 500ms | < 1s    | < 2s | >= 2s |
| 错误率       | < 0.1%  | < 1%    | < 5% | >= 5% |
| 吞吐量       | 达到目标    | 接近目标    | 低于目标 | 远低于目标 |

**优化建议分类**：

1. **服务器配置优化**：
   - 增加服务器 CPU/内存资源
   - 优化数据库连接池配置
   - 调整 JVM 参数（堆大小、垃圾回收）
   - 启用缓存机制（Redis、Memcached）
2. **接口性能优化**：
   - SQL 语句优化（添加索引、避免全表扫描）
   - 减少不必要的数据库查询
   - 接口合并减少网络往返
   - 异步处理非核心业务逻辑
3. **并发策略优化**：
   - 调整 ramp-up 时间避免瞬时压力
   - 实施阶梯式并发递增
   - 识别系统瓶颈并设置合理并发上限
   - 考虑使用分布式压测
4. **架构级优化**：
   - 引入负载均衡
   - 实施读写分离
   - 考虑微服务拆分
   - 引入 CDN 加速静态资源
5. **JMeter 测试计划优化**：
   - 使用 CLI 模式运行
   - 减少监听器数量（负载测试时禁用 View Results Tree）
   - 使用 CSV 格式而非 XML 格式存储结果
   - 使用 Groovy 脚本（JSR223）替代 BeanShell
   - 勾选"Cache compiled script if available"
   - 脚本中使用 `vars.get()` 而非 `${varName}` 以确保缓存有效
   - 使用 CSV Data Set 替代大量相似采样器
   - 只保存需要的数据字段


## 脚本使用指南

### run\_jmeter.py

用于执行 JMeter 压测并管理进程。

**用法**：

```bash
python run_jmeter.py --jmx test.jmx --result result.jtl \
  --log jmeter.log
```

**参数**：

- `--jmx`: JMX 文件路径
- `--result`: 结果文件路径
- `--log`: 日志文件路径
- `--distributed`: 启用分布式压测
- `--remote-hosts`: 远程服务器列表

### parse\_jtl.py

用于解析 JTL 结果文件并生成报告。

**用法**：

```bash
python parse_jtl.py --jtl result.jtl --output report.json \
  --format json --charts
```

**参数**：

- `--jtl`: JTL 文件路径
- `--output`: 输出报告路径
- `--format`: 输出格式（json, html, csv）
- `--charts`: 生成图表（需要 matplotlib）


## HTML 报告生成

### 生成方式

```bash
# 从已有 JTL 生成
jmeter -g result.jtl -o report/

# 测试后自动生成
jmeter -n -t test.jmx -l result.jtl -e -o report/
```

### 关键配置

```properties
# APDEX 阈值
jmeter.reportgenerator.apdex_satisfied_threshold=500
jmeter.reportgenerator.apdex_tolerated_threshold=1500

# 时间粒度
jmeter.reportgenerator.overall_granularity=60000

# 百分位数
aggregate_rpt_pct1=90
aggregate_rpt_pct2=95
aggregate_rpt_pct3=99
```

### JTL 必需字段

为生成完整报告，CSV 文件必须包含：
bytes, label, latency, response\_code, response\_message, successful, thread\_counts, thread\_name, time, connect\_time, assertion\_results\_failure\_message, timestamp\_format=ms
