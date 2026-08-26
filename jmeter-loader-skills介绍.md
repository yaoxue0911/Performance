jmeter-loader-skills介绍

利用 AI 自动理解 Fiddler 抓包中的业务请求，并将其转换为JMeter性能测试脚本

## 基本介绍

参数化：把请求里固定写死的数据，替换成可变化的数据。
username=test001 --> username=${username}
关联：从前一个请求的响应中提取动态值，再传给后面的请求。
打开inbox，提取case_id，传给后面查看case页面的请求。


在做性能测试，或利用接口批量添加数据时，我们的测试过程是：
1. 在页面上操作，同时用fiddler抓取请求信息。
2. 使用pan总的解析工具将fiddler抓包内容解析为性能脚本，工具可以将case_id/rnd等常见参数自动参数化。
3. 人工处理脚本中其它要参数化的字段和提取参数的步骤。添加Transaction组织脚本结构。
4. 执行测试，根据性能结果调整性能压力
或者
1. 在页面上操作，同时用fiddler抓取请求信息。
2. 转换为Jmeter脚本，完全人工处理所有的参数和关联。添加Transaction,loop等元件组织脚本结构。
3. 执行测试，根据性能结果调整性能压力

## 传统方式存在的问题：
1. 脚本结构简单，导致性能压力被分散
例如：脚本流程为：登录 - 打开home页面 - 添加case 
- 要测试整个站点所有重要功能的性能时，这个流程没问题
- 要重点测试多个用户并发/循环添加case信息时，由于每个线程每次循环都会登录一次，性能压力被分散到了登录功能
同样的，对于**在intake case页面选择master location**这个操作，
- 要测试并发添加case这一个POST请求的性能时，选择master location这个操作对性能结果没有影响，为了不分散压力，应该使用固定参数。
- 要测试选择master location这个操作的性能，或者要测试添加case完整流程的性能时，需要从前置请求的返回值中读取返回的master location。
2. 每个站点的同一个功能存在差别
- 例如report功能，在不同站点的report有时名字相同但页面功能不同，template_id不同。
3. 参数关联经常有意外
例如case_id这个参数，有些功能里写成了case_ld
middlepage写成了middelpage
参数名前后不一致导致取不到数据

综上所述，同一个脚本并不适用于所有测试场景；编写脚本耗时耗力。

将以上编写性能脚本的经验总结成SKILL，经过反复调整和多次实战验证。

## 使用AI编写Jmeter脚本的测试流程
1. 在页面上操作，同时用fiddler抓取请求信息。
2. 说明需求，使用SKILL将fiddler抓包内容转换为Jmeter脚本
3. 执行测试，根据性能结果调整性能压力

## SKILL结构

主技能
- 阶段一
  references
  生成测试计划，用户审阅，补充细节和计划
- 阶段二
  references
  根据测试计划生成JSON
  JSON文件 -> 生成器 -> Jmeter脚本

1. 使用主SKILL+references的结构
由于技能描述太长的话，xxx，所以将描述拆分，只有使用到对应内容时才会加载。
2. 根据测试计划生成JSON
Jmeter脚本的本质是XML文件，【Jmeter脚本的元件包含属性ABCDE】，将文字测试计划转换为JSON，提供属性ABC
生成器读取JSON文件以及其中的属性ABC，同时DE使用默认属性，生成Jmeter脚本
3. assets
JSON示例，JMX示例
4. 参数化取值
根据实际业务总结。分为：动态参数，静态值，从文件中读取，动态随机参数，特殊参数

比如登录用户的用户名密码需要从文件中读取
添加Person信息时，person name，driver license等唯一的值需要随机变化，每个线程不能重复。
Person的性别种族等其它信息，可以使用fiddler抓包的值
添加Person后如果要用person信息来创建report，需要在添加person的请求后面动态获取person_id。



## Agent
使用Agent执行完整流程

1. Jmx generator
- 调用jmeter-loader-skills
- 在生成脚本后调用Jmx validator Agent进行验证
- 使用命令行运行Jmeter，执行脚本
- [尚未完成]调用Report Analyzer分析报告

2. Jmx validator
- 重点检测脚本中容易出现的问题

3. [尚未完成]Report Analyzer
- 获取运行后保存的测试结果
- 调用jmeter-report-analyzer分析报告

由于每个Agent调用agent的方式不同，有些甚至不支持这种模式，