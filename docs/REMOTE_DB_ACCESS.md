# Achieve Analysis 远程只读访问（SSH 隧道）

> 适用场景：开发机通过 SSH 隧道读取服务器数据库（只读），不对外暴露 5432。
> **注意：本文件为脱敏版本，实际凭证请通过环境变量或密钥管理工具获取。**

## 连接方式（SSH 隧道）

1) 在服务器上获取数据库容器 IP：

```bash
podman inspect -f '{{(index .NetworkSettings.Networks "achieve-network").IPAddress}}' achieve-analysis-db
```

2) 在开发机建立 SSH 隧道（示例本地端口 15432）：

```bash
ssh -L 15432:<db-container-ip>:5432 <user>@<your-server-domain>
```

3) 在本地设置连接字符串（ACHIEVE_DB_DSN）：

```text
postgresql+psycopg://<db_user>:<db_password>@127.0.0.1:15432/<db_name>?sslmode=require
```

## 当前数据库连接信息

- DB 名称：`<db_name>`
- 只读账号：`<db_user>`
- 密码：`<db_password>`（通过环境变量 `ACHIEVE_DB_DSN` 配置）
- SSL：已开启（`ssl = on`），本地建议 `sslmode=require`

## 服务器端已做的配置

- **开启 SSL**
  - 配置文件：`<pg_data_dir>/postgresql.conf`
  - 已修改项：`ssl = on`
  - 证书文件：
    - `<pg_data_dir>/server.crt`
    - `<pg_data_dir>/server.key`
- **只读账号与授权**
  - 账号：`<db_user>`（无 BYPASSRLS）
  - 权限：
    - `GRANT CONNECT ON DATABASE <db_name> TO <db_user>;`
    - `GRANT USAGE ON SCHEMA public TO <db_user>;`
    - `GRANT SELECT ON ALL TABLES IN SCHEMA public TO <db_user>;`
    - `GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO <db_user>;`
    - `ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO <db_user>;`
    - `ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO <db_user>;`
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
PGPASSWORD='<db_password>' psql "host=127.0.0.1 port=15432 dbname=<db_name> user=<db_user> sslmode=require" -c "select 1;"
```
