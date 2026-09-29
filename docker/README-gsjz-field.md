# 甘肃现场 RAGFlow 部署配置

本目录采用“通用默认配置 + 现场私密覆盖”的方式部署：

- `.env`：仓库通用默认值，保留在版本控制中，不写现场密码。
- `.env.gsjz-field.example`：最小化、脱敏的现场覆盖模板，可提交。
- `.env.gsjz-field`：实际现场值，已被 `.gitignore` 排除，不得提交。
- `docker-compose-qkq-field.yml`：正式应用容器覆盖文件，只启动 `fmoss-rag-server-cpu`，复用外部 `dev` 网络上的 `base-*` 基础服务。

早期 `*rehearsal*` 文件用于并行演练或独立数据卷验证，生产归位后不再作为后续部署入口。

## 1. 准备现场变量

```bash
cd docker
cp .env.gsjz-field.example .env.gsjz-field
chmod 600 .env.gsjz-field
```

编辑 `.env.gsjz-field`：

1. 将所有 `CHANGE_ME` 替换为现场值；
2. `RAGFLOW_IMAGE` 使用已构建并导入的版本化镜像；
3. `MYSQL_DBNAME`、`MINIO_BUCKET/MINIO_PREFIX_PATH`、`REDIS_DB` 使用 0.27.2 独立逻辑空间；
4. 首次初始化共享租户和模板 Chat 后填写 `QKQ_EMBEDDED_CHAT_TEMPLATE_CHAT_ID`；
5. 不要把共享授权、数据库密码或模型密钥写回 `.env` 或 example 文件。

## 2. 渲染检查

```bash
docker compose \
  --env-file .env \
  --env-file .env.gsjz-field \
  -f docker-compose.yml \
  -f docker-compose-qkq-field.yml \
  config > /tmp/ragflow-gsjz-compose.yml
```

检查渲染结果：

- 项目名为 `ragflow-gsjz-0272`；
- 仅 `ragflow-cpu` 属于启用的 `cpu` profile；
- 容器名为 `fmoss-rag-server-cpu`；
- 网络为外部 `dev`；
- Web/API 端口为 `280/281/2443`、`9380-9384`，其中 `281` 是原生登录入口；
- MySQL、Elasticsearch、MinIO、Redis 均指向既有 `base-*` 服务。

## 3. 更新应用容器

先记录当前镜像和配置。若当前容器由旧 rehearsal 项目创建，需要先删除旧容器；镜像和回滚配置应继续保留。

```bash
docker inspect fmoss-rag-server-cpu > /FMoss/ragflow/releases/rollback/fmoss-rag-server-cpu.before-update.json
docker rm -f fmoss-rag-server-cpu

docker compose \
  --env-file .env \
  --env-file .env.gsjz-field \
  -f docker-compose.yml \
  -f docker-compose-qkq-field.yml \
  up -d --no-deps ragflow-cpu
```

`--no-deps` 是强制要求，避免创建或替换现场 `base-*` 基础服务。

## 4. 验证

```bash
docker inspect -f 'status={{.State.Status}} restart={{.RestartCount}} image={{.Config.Image}}' fmoss-rag-server-cpu
docker port fmoss-rag-server-cpu
curl -fsS http://127.0.0.1:9380/api/v1/system/healthz
```

还需通过 66 的统一入口验证 `/ragflow/`、`/ragflow-api/`、知识库管理和知识问答流式响应。

原生登录入口使用同一份 `web/dist`，不是第二套前端，也不会启动第二个 Nginx：

```bash
curl -I http://127.0.0.1:281/
curl -fsS http://127.0.0.1:281/ragflow/runtime-config.js
```

浏览器访问 `http://<RAGFlow主机>:281/ragflow/login`。80 监听继续由 FMOSS 统一入口使用嵌入认证，81 监听通过运行时配置关闭嵌入认证。前端代码变化时只需重新执行一次 `npm run build` 并更新挂载的 `web/dist`，不需要为两种认证模式分别构建，也不需要重建 RAGFlow 镜像。

后端运行源码也按目录挂载到原路径：`admin`、`agent`、`api`、`common`、`deepdoc`、`mcp`、`memory`、`rag`、`tools`。修改这些目录中的 Python 代码后，重启应用容器即可：

```bash
docker restart fmoss-rag-server-cpu
```

不要把整个仓库挂载到 `/ragflow`，否则会覆盖镜像中的 `.venv`、运行依赖和其他启动所需文件。`conf/service_conf.yaml.template` 和 `docker/entrypoint.sh` 继续使用已有的单文件挂载。

## 5. 回滚

将 `.env.gsjz-field` 中 `RAGFLOW_IMAGE` 改回保留的旧镜像，并使用同一组 Compose 命令重新创建应用容器。若需要回到 0.26.4，应使用已留存的旧配置和原逻辑数据显式重建，不做反向数据同步。
