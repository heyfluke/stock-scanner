-- MySQL 数据库初始化脚本
-- 用于微服务架构的MySQL数据库初始化

-- 设置时区
SET time_zone = '+00:00';

-- 设置字符集
SET NAMES utf8mb4;

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- 创建用户收藏表
CREATE TABLE IF NOT EXISTS user_favorites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    stock_code VARCHAR(20) NOT NULL,
    market_type VARCHAR(10) NOT NULL,
    display_name VARCHAR(100),
    tags TEXT, -- JSON格式
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_stock (user_id, stock_code, market_type),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 创建分析历史表
CREATE TABLE IF NOT EXISTS analysis_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    stock_codes TEXT NOT NULL, -- JSON格式
    market_type VARCHAR(10) NOT NULL,
    analysis_days INT DEFAULT 30,
    analysis_result TEXT, -- JSON格式
    ai_output TEXT,
    chart_data TEXT, -- JSON格式
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 创建对话表
CREATE TABLE IF NOT EXISTS conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    history_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (history_id) REFERENCES analysis_history(id) ON DELETE CASCADE
);

-- 创建对话消息表
CREATE TABLE IF NOT EXISTS conversation_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT NOT NULL,
    role VARCHAR(20) NOT NULL, -- 'user' 或 'assistant'
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- 创建用户设置表
CREATE TABLE IF NOT EXISTS user_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNIQUE NOT NULL,
    default_market_type VARCHAR(10) DEFAULT 'A',
    default_analysis_days INT DEFAULT 30,
    api_preferences TEXT, -- JSON格式
    ui_preferences TEXT, -- JSON格式
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 创建数据库版本表
CREATE TABLE IF NOT EXISTS database_version (
    id INT AUTO_INCREMENT PRIMARY KEY,
    version INT NOT NULL,
    migration_name TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- 创建索引以提高查询性能
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_user_favorites_user_id ON user_favorites(user_id);
CREATE INDEX idx_analysis_history_user_id ON analysis_history(user_id);
CREATE INDEX idx_analysis_history_created_at ON analysis_history(created_at);
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_history_id ON conversations(history_id);
CREATE INDEX idx_conversation_messages_conversation_id ON conversation_messages(conversation_id);
CREATE INDEX idx_database_version_version ON database_version(version);

-- 插入初始版本记录
INSERT INTO database_version (version, migration_name, description) 
VALUES (1, 'initial_schema', 'Initial database schema') 
ON DUPLICATE KEY UPDATE description = VALUES(description);

-- 注意：MySQL的TIMESTAMP字段已经配置了ON UPDATE CURRENT_TIMESTAMP
-- 所以不需要额外的触发器来更新时间戳

-- 创建演示用户（可选）
INSERT INTO users (username, email, password_hash, display_name) 
VALUES ('demo', 'demo@example.com', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', '演示用户')
ON DUPLICATE KEY UPDATE display_name = VALUES(display_name);

-- 创建演示用户的设置
INSERT INTO user_settings (user_id, default_market_type, default_analysis_days) 
SELECT id, 'A', 30 FROM users WHERE username = 'demo'
ON DUPLICATE KEY UPDATE default_market_type = VALUES(default_market_type); 