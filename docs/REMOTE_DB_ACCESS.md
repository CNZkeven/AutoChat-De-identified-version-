# Achieve Analysis 远程只读访问（SSH 隧道）

> 适用场景：开发机通过 SSH 隧道读取服务器数据库（只读），不对外暴露 5432。

## 连接方式（SSH 隧道）

1) 在服务器上获取数据库容器 IP：

```bash
podman inspect -f '{{(index .NetworkSettings.Networks "achieve-network").IPAddress}}' achieve-analysis-db
```

最新获取IP：10.89.0.149

2) 在开发机建立 SSH 隧道（示例本地端口 15432）：

```bash
ssh -L 15432:10.89.0.149:5432 root@achieve.adapt-learn.online
```

3) 在本地设置连接字符串（ACHIEVE_DB_DSN）：

```text
postgresql+psycopg://dm_reader:dm_reader%40Achieve@127.0.0.1:15432/course_analysis_db?sslmode=require
```

> 说明：`dm_reader@Achieve` 中的 `@` 需要 URL 编码为 `%40`。

## 当前数据库连接信息

- DB 名称：`course_analysis_db`
- 只读账号：`dm_reader`
- 密码：`dm_reader@Achieve`
- SSL：已开启（`ssl = on`），本地建议 `sslmode=require`

## 服务器端已做的配置

- **开启 SSL**
  - 配置文件：`/var/lib/containers/storage/volumes/achieve_postgres_data/_data/postgresql.conf`
  - 已修改项：`ssl = on`
  - 证书文件：
    - `/var/lib/containers/storage/volumes/achieve_postgres_data/_data/server.crt`
    - `/var/lib/containers/storage/volumes/achieve_postgres_data/_data/server.key`
- **只读账号与授权**
  - 账号：`dm_reader`（无 BYPASSRLS）
  - 权限：
    - `GRANT CONNECT ON DATABASE course_analysis_db TO dm_reader;`
    - `GRANT USAGE ON SCHEMA public TO dm_reader;`
    - `GRANT SELECT ON ALL TABLES IN SCHEMA public TO dm_reader;`
    - `GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO dm_reader;`
    - `ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO dm_reader;`
    - `ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO dm_reader;`
- **未改动项**
  - 未暴露 5432 到公网或宿主机
  - 未修改 `docker-compose.production.yml`
  - 未修改防火墙/安全组

## 备注与维护

- 容器 IP 可能在重启后变化，需重新执行获取 IP 命令并更新 SSH 隧道目标。
- 当前数据库所有业务表都在 `public` schema；已覆盖你要求的表清单。
- `postgres` 仍是超级用户并具备 BYPASSRLS（系统默认），生产读写账号建议单独创建并最小权限化。

## 本地连通性测试（开发机）

```bash
PGPASSWORD='dm_reader@Achieve' psql "host=127.0.0.1 port=15432 dbname=course_analysis_db user=dm_reader sslmode=require" -c "select 1;"
```
