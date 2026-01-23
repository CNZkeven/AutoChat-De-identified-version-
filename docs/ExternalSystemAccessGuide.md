# 外部系统数据访问说明（已弃用）

该外部接口已停止使用，改为 **Achieve → Autochat dm 读库** 的内部同步方案；智能体仅通过内部工具读取本地 dm 数据，不再暴露外部 API。

历史接口与说明保留如下，供回溯参考。

## 1. 鉴权方式（JWT）
- **签发方**：外部系统签发 JWT，本系统仅校验签名与 `iss/aud`。
- **算法**：HS256（与 `EXTERNAL_JWT_SECRET` 对应）。
- **学号**：使用学号作为唯一身份标识。

### 1.1 必填/推荐声明
- `student_no`（或 `studentNo`/`student_id_number`/`studentIdNumber`/`sub`）：学号
- `scopes`：字符串数组或空格分隔字符串
- `iss`：发行方（建议与 `EXTERNAL_JWT_ISSUER` 一致）
- `aud`：受众（建议与 `EXTERNAL_JWT_AUDIENCE` 一致）
- `exp`：过期时间（建议 30-60 分钟）

### 1.2 Scope 列表
- `syllabus:read`：课程基础信息、课程目标
- `grades:read:own`：个人成绩与个人达成度
- `grades:distribution:read`：班级成绩分布（需满足最小样本阈值）

## 2. API 端点

### 2.1 课程基础信息
- `GET /external/v1/students/me/course-offerings`
  - 说明：查询该学生已选课程列表
- `GET /external/v1/course-offerings/{offeringId}`
  - 说明：查询课程开设基本信息
- `GET /external/v1/course-offerings/{offeringId}/objectives`
  - 说明：课程目标（教学大纲目标）

### 2.2 个人成绩与达成度
- `GET /external/v1/students/me/course-offerings/{offeringId}/grades`
  - 说明：个人成绩（原始成绩 + 计算成绩 + 备注）
- `GET /external/v1/students/me/course-offerings/{offeringId}/achievements`
  - 说明：个人达成度（基于成绩达成度计算结果）

### 2.3 班级成绩分布
- `GET /external/v1/course-offerings/{offeringId}/grades/distribution?minSample=10`
  - 说明：班级成绩分布（仅分布/桶计数）
  - 默认 `minSample=10`，不足时返回 `available=false`

## 3. 示例请求

```bash
curl -H "Authorization: Bearer <JWT>" \
  http://localhost:3000/external/v1/students/me/course-offerings
```

```bash
curl -H "Authorization: Bearer <JWT>" \
  http://localhost:3000/external/v1/students/me/course-offerings/123/grades
```

## 4. 响应与错误约定
- `401 Unauthorized`：JWT 缺失/无效/学号不存在
- `403 Forbidden`：缺少 scope 或未选该课
- `404 Not Found`：课程/目标/达成度/分布不存在

## 5. 安全与隐私
- 所有成绩相关接口均要求学号与选课关系匹配。
- 班级成绩分布仅返回桶计数，不返回个人成绩；且需满足最小样本阈值。

## 6. 环境变量
以下外部接口配置已弃用（保留历史记录）：
- `EXTERNAL_JWT_SECRET`
- `EXTERNAL_JWT_ISSUER`
- `EXTERNAL_JWT_AUDIENCE`
