"""
课程数据导入脚本
将extracted_courses_data.json中的140门课程数据导入到数据库Knowledge表
"""

import argparse
import json
import os
import sys
from pathlib import Path

from app.config import PROJECT_ROOT
from app.db import SessionLocal
from app.models import Knowledge

# JSON数据文件默认路径（可通过 --json 或 COURSES_JSON_PATH 覆盖）
DEFAULT_JSON_PATH = PROJECT_ROOT / "data" / "extracted_courses_data.json"


def resolve_json_path(cli_value: str | None = None) -> Path:
    env_value = os.environ.get("COURSES_JSON_PATH")
    candidate = cli_value or env_value or str(DEFAULT_JSON_PATH)
    path = Path(candidate)
    if not path.is_file():
        print(
            "❌ 错误：找不到课程数据文件 "
            f"{path}（可通过 --json 或 COURSES_JSON_PATH 指定）"
        )
        sys.exit(1)
    return path


def load_json_data(json_path: Path):
    """加载JSON数据"""
    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"❌ 错误：找不到文件 {json_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ 错误：JSON文件格式错误 - {e}")
        sys.exit(1)


def format_course_content(course):
    """格式化课程内容为知识库条目"""
    content = f"""
【课程基本信息】
课程代码：{course.get('课程代码', '未明确')}
课程名称：{course.get('课程名称', '未明确')}
所属专业：{course.get('所属专业', '未明确')}
学分：{course.get('学分', '未明确')}
课程性质：{course.get('课程性质', '未明确')}

【课程考评】
是否为考试课：{course.get('是否为考试课', '未明确')}
是否为考查课：{course.get('是否为考查课', '未明确')}

【教学信息】
任课教师：{course.get('任课教师', '未明确')}
开课时间：{course.get('开课时间', '未明确')}

【学时信息】
总学时：{course.get('总学时', '未明确')}
授课学时：{course.get('授课学时', '未明确')}
实验时数：{course.get('实验时数', '未明确')}

【课程大纲】
{course.get('课程大纲', '暂无详细大纲')}
"""
    return content.strip()


def create_knowledge_entry(course):
    """创建Knowledge数据库条目"""
    return Knowledge(
        title=f"{course.get('课程代码', 'UNKNOWN')} - {course.get('课程名称', '未命名课程')}",
        content=format_course_content(course),
        category=f"course_{course.get('所属专业', '其他')}",
        source=f"course_system|{course.get('课程代码', 'UNKNOWN')}|{course.get('所属专业', '')}",
        is_active=True
    )


def import_courses(json_path: str | None = None):
    """执行导入操作"""
    print("=" * 60)
    print("📚 开始导入课程数据到数据库...")
    print("=" * 60)

    # 加载JSON数据
    print("\n📖 正在加载JSON数据...")
    resolved_path = resolve_json_path(json_path)
    data = load_json_data(resolved_path)
    print(f"   - 数据文件：{resolved_path}")

    courses = data.get('courses', [])
    summary = data.get('summary', {})

    print("✅ 加载成功！")
    print(f"   - 总课程数：{summary.get('total_courses', 0)}门")
    print(f"   - 电气工程及其自动化：{summary.get('courses_by_major', {}).get('电气工程及其自动化', 0)}门")
    print(f"   - 测控技术与仪器：{summary.get('courses_by_major', {}).get('测控技术与仪器', 0)}门")
    print(f"   - 智能感知工程：{summary.get('courses_by_major', {}).get('智能感知工程', 0)}门")

    # 连接数据库
    print("\n🔗 正在连接数据库...")
    try:
        db = SessionLocal()
        print("✅ 数据库连接成功！")
    except Exception as e:
        print(f"❌ 数据库连接失败：{e}")
        sys.exit(1)

    # 导入数据
    print("\n📥 正在导入课程数据...")
    success_count = 0
    failed_count = 0
    major_stats = {}

    try:
        for idx, course in enumerate(courses, 1):
            try:
                # 创建Knowledge条目
                knowledge = create_knowledge_entry(course)
                db.add(knowledge)
                success_count += 1

                # 统计各专业课程
                major = course.get('所属专业', '其他')
                major_stats[major] = major_stats.get(major, 0) + 1

                # 每50条提交一次
                if idx % 50 == 0:
                    db.commit()
                    print(f"   已导入 {idx}/{len(courses)} 条记录...")

            except Exception as e:
                print(f"⚠️  第{idx}条课程导入失败：{e}")
                failed_count += 1
                continue

        # 最后提交剩余数据
        db.commit()

        print("\n✅ 导入完成！")
        print(f"   - 成功导入：{success_count}条")
        print(f"   - 导入失败：{failed_count}条")
        print("\n📊 各专业导入统计：")
        for major, count in sorted(major_stats.items()):
            print(f"   - {major}：{count}门")

    except Exception as e:
        print(f"\n❌ 导入过程中出错：{e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

    print("\n" + "=" * 60)
    print("✨ 数据导入操作完成！")
    print("=" * 60)

    return success_count, failed_count


def verify_import():
    """验证导入结果"""
    print("\n🔍 正在验证导入结果...")

    try:
        db = SessionLocal()

        # 统计总数
        total = db.query(Knowledge).count()
        print(f"✅ 数据库中Knowledge表总记录数：{total}条")

        # 按分类统计
        categories = db.query(Knowledge.category).distinct().all()
        print("\n📂 按类别统计：")
        for (cat,) in categories:
            if cat and cat.startswith('course_'):
                count = db.query(Knowledge).filter(Knowledge.category == cat).count()
                major_name = cat.replace('course_', '')
                print(f"   - {major_name}：{count}条")

        db.close()

    except Exception as e:
        print(f"❌ 验证失败：{e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="导入课程 JSON 数据到 Knowledge 表")
    parser.add_argument("--json", dest="json_path", help="课程 JSON 文件路径")
    args = parser.parse_args()
    success, failed = import_courses(args.json_path)
    verify_import()
