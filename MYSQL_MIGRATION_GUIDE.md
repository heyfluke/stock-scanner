# PostgreSQL到MySQL迁移指南

## 概述

本指南详细说明了如何将Stock Scanner项目从PostgreSQL迁移到MySQL数据库。

## 迁移可行性评估

### ✅ 高度可行的原因

1. **ORM层透明性**
   - 使用SQLModel + SQLAlchemy，对数据库类型透明
   - 所有数据库操作都通过ORM，无需修改业务逻辑
   - 数据模型定义完全兼容

2. **现有架构支持**
   - 数据库连接通过环境变量配置
   - 迁移系统已支持多数据库类型检测
   - 初始化脚本可轻松适配

3. **依赖包支持**
   - 已添加MySQL驱动：`PyMySQL==1.1.0`（纯Python实现，无需编译）
   - 保留PostgreSQL驱动以支持两种数据库

### ⚠️ 需要注意的差异

1. **SQL语法差异**
   ```sql
   -- PostgreSQL
   CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
   SET timezone = 'UTC';
   
   -- MySQL
   -- 无需扩展，内置UUID函数
   SET time_zone = '+00:00';
   ```

2. **数据类型差异**
   ```sql
   -- PostgreSQL
   SERIAL PRIMARY KEY
   TIMESTAMP WITH TIME ZONE
   
   -- MySQL
   AUTO_INCREMENT PRIMARY KEY
   TIMESTAMP
   ```

3. **系统表查询差异**
   ```sql
   -- PostgreSQL
   SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'
   
   -- MySQL
   SHOW TABLES
   ```

## 迁移步骤

### 1. 环境准备

确保已安装MySQL驱动：
```bash
pip install PyMySQL==1.1.0
```

### 2. 数据库配置

#### 环境变量配置
```bash
# MySQL配置
DATABASE_URL=mysql://stock_user:stock_password@mysql:3306/stock_scanner
MYSQL_USER=stock_user
MYSQL_PASSWORD=stock_password
MYSQL_DATABASE=stock_scanner
MYSQL_ROOT_PASSWORD=root_password
```

#### 连接字符串格式
```
mysql+pymysql://username:password@host:port/database
```

### 3. 部署方式

#### 方式一：使用MySQL微服务配置
```bash
# 使用MySQL版本的Docker Compose
docker-compose -f docker-compose.mysql.yml up -d
```

#### 方式二：使用部署脚本
```bash
# 运行MySQL部署脚本
./deploy-mysql.sh
```

#### 方式三：手动部署
```bash
# 1. 构建镜像
docker-compose -f docker-compose.mysql.yml build

# 2. 启动服务
docker-compose -f docker-compose.mysql.yml up -d

# 3. 检查状态
docker-compose -f docker-compose.mysql.yml ps
```

### 4. 数据迁移

#### 从PostgreSQL迁移到MySQL
```bash
# 1. 备份PostgreSQL数据
docker exec stock-scanner-postgres pg_dump -U stock_user stock_scanner > backup.sql

# 2. 转换SQL语法（手动或使用工具）
# 注意：需要处理PostgreSQL特有的语法

# 3. 导入MySQL
docker exec -i stock-scanner-mysql mysql -u stock_user -pstock_password stock_scanner < converted_backup.sql
```

#### 从SQLite迁移到MySQL
```bash
# 1. 导出SQLite数据
sqlite3 data/stock_scanner.db .dump > sqlite_backup.sql

# 2. 转换SQL语法
# 注意：需要处理SQLite特有的语法

# 3. 导入MySQL
docker exec -i stock-scanner-mysql mysql -u stock_user -pstock_password stock_scanner < converted_backup.sql
```

## 配置文件说明

### 新增文件

1. **`docker-compose.mysql.yml`**
   - MySQL版本的微服务配置
   - 使用MySQL 8.0镜像
   - 配置MySQL健康检查

2. **`init-scripts/02-init-mysql.sql`**
   - MySQL数据库初始化脚本
   - 创建所有必要的表和索引
   - 适配MySQL语法

3. **`deploy-mysql.sh`**
   - MySQL部署脚本
   - 自动化部署流程
   - 健康检查和服务验证

### 修改文件

1. **`requirements.txt`**
   - 添加：`PyMySQL==1.1.0`

2. **`utils/database_migrator.py`**
   - 添加MySQL语法支持
   - 更新版本检测逻辑
   - 支持MySQL迁移

3. **`Dockerfile.backend`**
   - 移除MySQL客户端开发库（使用PyMySQL无需编译）
   - 简化构建过程

4. **`docker-entrypoint.sh`**
   - 添加MySQL连接检测
   - 支持MySQL版本查询

## 性能对比

### MySQL优势
- **资源占用更低**：相比PostgreSQL，MySQL通常占用更少的内存和CPU
- **部署简单**：MySQL配置相对简单，适合快速部署
- **生态丰富**：MySQL有更多的管理工具和GUI客户端

### PostgreSQL优势
- **功能更强大**：支持更复杂的SQL特性，如JSON操作、全文搜索等
- **数据一致性**：ACID事务支持更完善
- **扩展性更好**：支持自定义数据类型和函数

### 选择建议

1. **选择MySQL的场景**
   - 资源受限的环境
   - 团队对MySQL更熟悉
   - 需要更简单的部署和维护
   - 主要进行简单的CRUD操作

2. **选择PostgreSQL的场景**
   - 需要复杂的数据处理
   - 对数据一致性要求很高
   - 需要JSON操作等高级功能
   - 团队对PostgreSQL更熟悉

## 故障排除

### 常见问题

1. **MySQL连接失败**
   ```bash
   # 检查MySQL服务状态
   docker-compose -f docker-compose.mysql.yml logs mysql
   
   # 检查网络连接
   docker network ls
   docker network inspect stock-scanner_stock-scanner-network
   ```

2. **字符集问题**
   ```sql
   -- 在MySQL中设置字符集
   SET NAMES utf8mb4;
   ALTER DATABASE stock_scanner CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

3. **权限问题**
   ```sql
   -- 确保用户有足够权限
   GRANT ALL PRIVILEGES ON stock_scanner.* TO 'stock_user'@'%';
   FLUSH PRIVILEGES;
   ```

### 日志查看
```bash
# 查看MySQL日志
docker-compose -f docker-compose.mysql.yml logs mysql

# 查看应用日志
docker-compose -f docker-compose.mysql.yml logs backend

# 查看所有服务日志
docker-compose -f docker-compose.mysql.yml logs -f
```

## 回滚方案

如果需要回滚到PostgreSQL：

1. **停止MySQL服务**
   ```bash
   docker-compose -f docker-compose.mysql.yml down
   ```

2. **启动PostgreSQL服务**
   ```bash
   docker-compose -f docker-compose.microservices.yml up -d
   ```

3. **恢复数据**
   ```bash
   # 从备份恢复PostgreSQL数据
   docker exec -i stock-scanner-postgres psql -U stock_user stock_scanner < backup.sql
   ```

## 总结

PostgreSQL到MySQL的迁移是完全可行的，主要优势包括：

1. **技术可行性高**：ORM层透明，业务逻辑无需修改
2. **部署简单**：提供了完整的自动化部署方案
3. **维护成本低**：MySQL配置相对简单
4. **资源占用少**：适合资源受限的环境

建议在迁移前进行充分的测试，确保所有功能正常工作。 