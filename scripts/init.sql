-- AutoOps 数据库初始化脚本
-- 表结构由 SQLAlchemy 自动创建，此脚本仅做补充配置

SET NAMES utf8mb4;
SET time_zone = '+08:00';

-- 确保数据库存在
CREATE DATABASE IF NOT EXISTS autoops CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE autoops;
