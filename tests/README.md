# 股票分析系统测试套件

本测试套件专门针对**HTTP API接口**进行测试，验证股票分析系统的各项功能。

## 🌐 HTTP API测试

### 快速开始

```bash
# 1. 快速A股分析测试（验证修复效果）
python tests/run_api_tests.py quick

# 2. 快速测试指定股票
python tests/test_api_quick.py --code 688385

# 3. 完整API端点测试
python tests/run_api_tests.py full

# 4. 指定服务器地址
python tests/run_api_tests.py quick --url http://localhost:8888
```

### API测试选项

```bash
python tests/run_api_tests.py [测试类型] [选项]

# 测试类型
quick     # 快速A股分析测试（验证修复效果）
full      # 完整API端点测试
health    # 仅测试服务器健康状态
analyze   # 仅测试股票分析接口
stream    # 仅测试流式分析接口
search    # 仅测试搜索接口
scan      # 仅测试扫描接口
perf      # 仅测试性能

# 选项
--url URL        # API服务器地址 (默认: http://localhost:8888)
--code CODE      # 股票代码（快速测试用，默认: 688385）
--username USER  # 登录用户名 (默认: demo)
--password PASS  # 登录密码 (默认: demo)
--verbose, -v    # 详细输出模式
--help           # 显示帮助信息
```

### API测试覆盖范围

**测试股票：**
- 美股：TSLA (特斯拉)
- 港股：01810 (小米集团)  
- A股：688385 (复旦微电)

**测试接口：**
- ✅ `/api/config` - 服务器健康检查（无需认证）
- ✅ `/api/login` - 用户登录认证
- ✅ `POST /api/analyze` - 股票分析（需要认证）
- ✅ `POST /api/scan` - 批量股票扫描（需要认证）
- ✅ `GET /api/search/us` - 美股搜索（需要认证）
- ✅ `GET /api/search/fund` - 基金搜索（需要认证）

### 认证机制

所有测试都会自动进行用户认证：
1. 使用提供的用户名和密码登录
2. 获取JWT Token
3. 在后续请求中携带认证头
4. 如果认证失败，测试会立即报错

### 示例用法

```bash
# 验证A股分析修复效果（默认demo/demo账号）
python tests/test_api_quick.py

# 使用自定义账号测试
python tests/test_api_quick.py --username myuser --password mypass

# 测试不同服务器
python tests/run_api_tests.py quick --url http://192.168.1.100:8888

# 详细模式运行完整测试
python tests/run_api_tests.py full --verbose

# 仅测试分析接口
python tests/run_api_tests.py analyze

# 性能测试
python tests/run_api_tests.py perf
```



## 📁 测试文件说明

### HTTP API测试文件
- `test_api_endpoints.py` - 完整API端点测试（支持认证）
- `test_api_quick.py` - 快速A股分析测试（支持认证）
- `run_api_tests.py` - API测试运行器（统一认证管理）

### 其他文件
- `test-docker-compose.py` - Docker环境测试
- `README.md` - 本文档

## 🔧 环境要求

### 基础依赖
- Python 3.8+
- aiohttp (HTTP客户端)
- 股票分析服务器运行中

### 服务器要求
- 后端服务正常运行
- 用户认证系统启用
- 测试账号可用（默认：demo/demo）

## 📈 测试结果解读

### 成功指标
- ✅ 服务器连接正常
- ✅ 用户登录成功
- ✅ API响应状态码200
- ✅ 返回有效JSON数据
- ✅ 分析结果包含必要字段
- ✅ 流式响应正常完成

### 常见问题
1. **服务器连接失败** - 检查服务器是否启动，端口是否正确
2. **认证失败** - 检查用户名密码是否正确
3. **API响应异常** - 检查请求参数和服务器日志
4. **分析结果错误** - 检查股票代码和市场类型
5. **流式响应中断** - 检查网络连接和超时设置

## 🐛 故障排除

### 1. 服务器连接问题
```bash
# 检查服务器状态
curl http://localhost:8888/api/config

# 检查端口占用
netstat -an | grep 8888
```

### 2. 认证问题
```bash
# 测试登录接口
curl -X POST http://localhost:8888/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo"}'

# 使用自定义账号测试
python tests/run_api_tests.py quick --username myuser --password mypass
```

### 3. API测试问题
```bash
# 详细模式运行
python tests/run_api_tests.py quick --verbose

# 测试特定接口
python tests/run_api_tests.py health
```

### 4. 依赖问题
```bash
# 安装API测试依赖
pip install aiohttp

# 安装完整依赖
pip install -r requirements.txt
```

## 🚀 推荐测试流程

### 日常验证
```bash
# 1. 快速验证（最常用）
python tests/run_api_tests.py quick

# 2. 完整验证
python tests/run_api_tests.py full
```

### 修复验证
```bash
# 1. 测试A股分析修复
python tests/test_api_quick.py --code 688385

# 2. 验证所有市场
python tests/run_api_tests.py analyze
```

### 性能测试
```bash
# API性能测试
python tests/run_api_tests.py perf

# 压力测试（可选）
# 使用外部工具如 ab, wrk 等
```

## 📝 扩展测试

### 添加新的测试股票
在测试类中修改 `test_stocks` 配置：
```python
self.test_stocks = {
    'US': {'code': 'AAPL', 'name': '苹果'},
    'HK': {'code': '00700', 'name': '腾讯'},
    'A': {'code': '000001', 'name': '平安银行'}
}
```

### 添加新的API测试
1. 在 `TestAPIEndpoints` 类中添加新的测试方法
2. 在 `run_all_tests()` 中调用新方法
3. 更新测试结果统计

## 🤝 贡献指南

1. 优先使用HTTP API测试验证功能
2. 添加新功能时编写对应的API测试
3. 保持测试代码简洁和可读性
4. 更新文档说明新功能

## 📞 支持

如遇到测试问题，请：
1. 先检查服务器状态
2. 使用详细模式查看日志
3. 确认网络连接正常
4. 联系开发团队 