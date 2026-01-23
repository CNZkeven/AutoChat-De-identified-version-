# Achieve 数据同步与读库说明

## 目标
将 Achieve 的教务数据定期同步到 Autochat 本地 `dm` schema，供智能体通过内部工具读取，避免直接跨域访问外部系统。

## 环境变量
- `ACHIEVE_DB_DSN`: Achieve 数据库只读 DSN
- `SYNC_TERM_WINDOW`: 逗号分隔的学期名称（可选）
- `SYNC_BATCH_SIZE`: 批量 upsert 大小（默认 2000）
- `SYNC_SCHEDULE_CRON`: 定时任务建议（默认 `0 3 * * *`）

## 一次性同步
```bash
python scripts/sync_dm.py --job dm_sync_manual
```

可选参数：
- `--entities students,courses,course_offerings,enrollments,student_scores`
- `--terms 2025FA,2026SP`
- `--batch-size 2000`

## 管理员手动触发
管理员接口：
- `POST /api/admin/dm-sync`

请求示例：
```json
{
  "job_name": "dm_sync_manual",
  "entities": ["students", "courses", "course_offerings"],
  "term_window": ["2025FA"],
  "batch_size": 2000
}
```

## 内部读取接口（供智能体调用）
- `GET /api/dm/me/sections?term=2025FA`
- `GET /api/dm/me/scores?term=2025FA`
- `GET /api/dm/me/sections/{offering_id}/summary?min_sample=10`

## 同步日志
- `ops.sync_job_log`: 作业状态、开始/结束时间、详情
- `ops.sync_watermark`: 增量水位

## 数据隔离
- `dm.student_scores`、`dm.enrollments`、`dm.section_grade_summary` 等表启用 RLS。
- 服务层会在查询前设置 `app.student_no`，仅允许读取本人范围。
- 同步作业通过 `app.role = 'sync'` 写入。

## 排错建议
1. 检查 `ACHIEVE_DB_DSN` 是否可用。
2. 检查 `ops.sync_job_log` 中 `detail.error`。
3. 若数据为空，确认 `SYNC_TERM_WINDOW` 是否与 Achieve 学期名称一致。
