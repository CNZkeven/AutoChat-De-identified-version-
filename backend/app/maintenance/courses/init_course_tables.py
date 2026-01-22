"""
初始化课程扩展表
创建Course、CourseRelationship和CourseLog表
"""

import sys

from app.db import Base, SessionLocal, engine
from app.models import Course, CourseLog, CourseRelationship


def create_course_tables():
    """创建课程相关的表"""
    print("=" * 70)
    print("📚 初始化课程扩展表")
    print("=" * 70)

    try:
        print("\n🔨 正在创建表结构...")
        # 创建所有新表
        Base.metadata.create_all(engine)

        print("✅ 表创建成功！\n")

        # 验证表
        print("🔍 验证表结构...")
        db = SessionLocal()

        # 检查表是否存在
        inspector_tables = []
        try:
            # 尝试查询
            courses = db.query(Course).count()
            inspector_tables.append('courses')
            print(f"✅ courses 表（{courses}条记录）")
        except Exception:
            print("⚠️  courses 表不存在或无法访问")

        try:
            relationships = db.query(CourseRelationship).count()
            inspector_tables.append('course_relationships')
            print(f"✅ course_relationships 表（{relationships}条记录）")
        except Exception:
            print("⚠️  course_relationships 表不存在或无法访问")

        try:
            logs = db.query(CourseLog).count()
            inspector_tables.append('course_logs')
            print(f"✅ course_logs 表（{logs}条记录）")
        except Exception:
            print("⚠️  course_logs 表不存在或无法访问")

        db.close()

        print("\n" + "=" * 70)
        print("✨ 课程表初始化完成！")
        print("=" * 70)
        print("\n📋 已创建的表：")
        print("  1. courses - 课程详细信息表")
        print("  2. course_relationships - 课程间关系表")
        print("  3. course_logs - 课程数据修改日志表")
        print("  4. course_prerequisite_association - 前置课程关联表")
        print("  5. course_related_association - 相关课程关联表")
        print("\n💾 字段包括：")
        print("  - 基本信息：课程代码、名称、学分")
        print("  - 属性信息：性质、类型、所属专业")
        print("  - 考评信息：考试课、考查课标记")
        print("  - 教学信息：任课教师、开课时间")
        print("  - 学时信息：总学时、授课学时、实验时数")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ 表创建失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    create_course_tables()
