
## 术语表

### Elapsed Time（经过时间/耗时）

JMeter 从**发送请求之前**到**接收到最后一个响应之后**的时间。**不包括**渲染响应的时间，也不处理任何客户端代码（如 JavaScript）。

### Latency（延迟时间）

JMeter 从**发送请求之前**到**接收到第一个响应之后**的时间。包含组装请求和组装响应第一部分所需的处理时间。

### Connect Time（连接时间）

建立连接所需的时间，包括 SSL 握手。**连接时间不会自动从延迟时间中减去。** 自 JMeter 3.1 起，仅对 TCP Sampler、HTTP Request 和 JDBC Request 计算。

### Median（中位数）

将样本分成两等分的数值。等同于第 50 百分位数。

### 90% Line（第 90 百分位数）

90% 的样本低于此值。

### Standard Deviation（标准差）

JMeter 计算的是**总体标准差**（STDEVP），而非样本标准差（STDEV）。

### Thread Name（线程名称）

格式：`groupName + " " + groupIndex + "-" + threadIndex`

示例：
```
Thread Group 1-1
Thread Group 1-2
Thread Group 2-1
Thread Group 2-2
```

### Throughput（吞吐量）

计算公式：**吞吐量 = 请求数 / 总时间**

时间从第一个样本开始到最后一个样本结束。包含样本之间的间隔时间，旨在代表服务器上的负载。
