## 模板使用说明(无需查看，不使用这个模式)

### base.jmx（基础 HTTP 模板）

适用于简单的 HTTP 接口压测，包含：

- 标准线程组配置
- HTTP 请求采样器
- 结果收集器
- 简单的定时器配置

**适用场景**：单接口压测、简单负载测试

### csv\_data.jmx（CSV 数据源模板）

适用于需要从 CSV 读取测试数据的场景，包含：

- CSV 数据集配置
- 参数化 HTTP 请求
- 循环控制器

**适用场景**：多用户登录、参数化请求、数据驱动测试

### auth\_flow\.jmx（带鉴权的业务流程模板）

适用于需要鉴权的业务流程压测，包含：

- 登录请求（获取 Token）
- Token 提取器
- 带认证头的业务请求
- Cookie 管理器

**适用场景**：需要登录的接口、Token 刷新流程、完整业务链路

### multi\_api.jmx（多接口混合压测模板）

适用于多个 API 端点的混合压测，包含：

- 3 个 HTTP 请求采样器（GET/POST 混合）
- 每个请求的 JSON 数据提取器
- 接口间数据串联（user\_id → order\_id）
- Response Assertion 断言
- InfluxDB Backend Listener（默认禁用）

**适用场景**：多接口混合压测、接口间数据依赖、API 链路测试

### staged\_load.jmx（阶梯加压模板）

适用于阶梯式负载测试，包含：

- 3 个顺序执行的 Thread Group（低→中→高负载）
- 每阶段独立的并发数和持续时间配置
- Duration Assertion 响应时间断言
- InfluxDB Backend Listener 实时监控

**适用场景**：性能拐点探测、容量规划、阶梯加压测试

### jdbc\_test.jmx（JDBC 数据库压测模板）

适用于数据库性能测试，包含：

- JDBC Connection Configuration 连接池配置
- 3 个 JDBC 采样器（Select/Insert/Update）
- Prepared Statement 参数绑定
- MySQL 驱动默认配置

**适用场景**：数据库性能测试、SQL 压力测试、连接池调优

### business\_flow\.jmx（业务流程模板）

适用于完整业务流程的事务级压测，包含：

- Once Only Controller（登录仅执行一次）
- 4 个 Transaction Controller（浏览→加购→结算→支付）
- 接口间数据提取与传递（auth\_token → product\_id → cart\_id → order\_id）
- If Controller 条件判断
- Debug Sampler 调试

**适用场景**：电商下单流程、多步骤事务、端到端业务链路压测

