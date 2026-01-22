"""
课程数据查询示例脚本
演示如何从数据库中查询和使用课程数据
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR / "backend"))

from app.db import SessionLocal  # noqa: E402
from app.models import Knowledge  # noqa: E402


def search_courses_by_major(major_name):
    """按专业查询课程"""
    print(f"\n📚 查询{major_name}的所有课程：")
    print("-" * 70)

    try:
        db = SessionLocal()

        category = f"course_{major_name}"
        courses = db.query(Knowledge).filter(Knowledge.category == category).all()

        if not courses:
            print(f"未找到相关课程")
            return

        print(f"找到 {len(courses)} 门课程：\n")

        for idx, course in enumerate(courses[:10], 1):  # 显示前10条
            # 从content中提取课程代码和名称
            lines = course.content.split('\n')
            print(f"{idx}. {course.title}")

        if len(courses) > 10:
            print(f"... 还有 {len(courses) - 10} 门课程")

        db.close()

    except Exception as e:
        print(f"❌ 查询失败：{e}")


def search_courses_by_keyword(keyword):
    """按关键词查询课程"""
    print(f"\n🔍 查询包含 '{keyword}' 的课程：")
    print("-" * 70)

    try:
        db = SessionLocal()

        # 在标题和内容中搜索
        courses = db.query(Knowledge).filter(
            (Knowledge.title.ilike(f'%{keyword}%')) |
            (Knowledge.content.ilike(f'%{keyword}%'))
        ).all()

        if not courses:
            print(f"未找到相关课程")
            return

        print(f"找到 {len(courses)} 门课程：\n")

        for idx, course in enumerate(courses[:15], 1):
            print(f"{idx}. {course.title}")
            print(f"   分类：{course.category}")

        if len(courses) > 15:
            print(f"\n... 还有 {len(courses) - 15} 门课程")

        db.close()

    except Exception as e:
        print(f"❌ 查询失败：{e}")


def show_course_details(course_id):
    """显示课程详细信息"""
    print(f"\n📖 课程详细信息（ID: {course_id}）：")
    print("-" * 70)

    try:
        db = SessionLocal()

        course = db.query(Knowledge).filter(Knowledge.id == course_id).first()

        if not course:
            print(f"未找到ID为{course_id}的课程")
            return

        print(f"标题   ：{course.title}")
        print(f"分类   ：{course.category}")
        print(f"来源   ：{course.source}")
        print(f"活跃   ：{'是' if course.is_active else '否'}")
        print(f"创建时间：{course.created_at}")
        print(f"更新时间：{course.updated_at}")
        print(f"\n📝 内容：")
        print("-" * 70)
        print(course.content)

        db.close()

    except Exception as e:
        print(f"❌ 查询失败：{e}")


def get_statistics():
    """获取统计信息"""
    print(f"\n📊 课程统计信息：")
    print("-" * 70)

    try:
        db = SessionLocal()

        # 总数
        total = db.query(Knowledge).count()
        print(f"总课程数         ：{total}门")

        # 按专业统计
        majors = {
            '智能感知工程': 'course_智能感知工程',
            '测控技术与仪器': 'course_测控技术与仪器',
            '电气工程及其自动化': 'course_电气工程及其自动化'
        }

        print(f"\n按专业分布：")
        for major_name, category in majors.items():
            count = db.query(Knowledge).filter(Knowledge.category == category).count()
            print(f"  {major_name:20s}：{count:3d}门")

        # 活跃课程
        active = db.query(Knowledge).filter(Knowledge.is_active == True).count()
        print(f"\n活跃课程数       ：{active}门")
        print(f"非活跃课程数     ：{total - active}门")

        db.close()

    except Exception as e:
        print(f"❌ 查询失败：{e}")


def main():
    """主函数 - 演示各种查询操作"""
    print("=" * 70)
    print("🎓 课程数据库查询演示")
    print("=" * 70)

    # 统计信息
    get_statistics()

    # 按专业查询
    search_courses_by_major('智能感知工程')
    search_courses_by_major('测控技术与仪器')
    search_courses_by_major('电气工程及其自动化')

    # 按关键词查询
    search_courses_by_keyword('控制')
    search_courses_by_keyword('信号')
    search_courses_by_keyword('实验')

    # 显示课程详情（查询前几条）
    try:
        db = SessionLocal()
        first_course = db.query(Knowledge).first()
        if first_course:
            show_course_details(first_course.id)
        db.close()
    except Exception as e:
        pass

    print("\n" + "=" * 70)
    print("✨ 查询演示完成！")
    print("=" * 70)
    print("\n💡 常用查询操作：")
    print("  1. 按专业查询：search_courses_by_major('智能感知工程')")
    print("  2. 按关键词查询：search_courses_by_keyword('控制')")
    print("  3. 查看详情：show_course_details(1)")
    print("  4. 获取统计：get_statistics()")


if __name__ == "__main__":
    main()
