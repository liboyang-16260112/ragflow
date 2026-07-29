# deployment-container-identity Specification

## Purpose

规范仓库内 Docker Compose 容器的品牌化命名，并确保服务发现契约保持不变。

## Requirements

### Requirement: Compose 容器名使用 FMoss-RAG 前缀
仓库内维护的 Docker Compose 启动入口 SHALL 为每个活动 service 设置显式 `container_name`，且名称 SHALL 以 `fmoss-rag-` 开头。该要求 SHALL 覆盖默认依赖、应用 CPU/GPU 变体、可选 profiles、CN、macOS 和独立 sandbox 入口。

#### Scenario: 启动默认 CPU 部署
- **WHEN** 用户使用 `docker/docker-compose.yml` 和默认 profiles 启动系统
- **THEN** Elasticsearch、MySQL、MinIO、Redis 和应用容器均使用唯一的 `fmoss-rag-` 前缀名称

#### Scenario: 切换可选 profile 或替代入口
- **WHEN** 用户启用任一可选 profile，或使用 CN、macOS、独立 sandbox Compose
- **THEN** 所有实际启动的容器仍具有唯一的 `fmoss-rag-` 前缀名称

### Requirement: 显式容器名不得改变服务发现契约
容器命名变更 MUST 保留现有 Compose service key、`depends_on` 关系、网络和内部 DNS 主机名，使应用继续通过 `mysql`、`redis`、`es01` 等 service key 连接依赖。

#### Scenario: 容器之间解析依赖服务
- **WHEN** 应用容器通过现有环境变量连接数据库、缓存、对象存储或文档引擎
- **THEN** 连接仍使用现有 service DNS 名称，不要求改写后端配置
