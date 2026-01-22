"""
课程关系建立脚本
创建课程间的先修、后续、相关等关系
"""

import sys

from sqlalchemy import func

from app.db import SessionLocal
from app.models import Course, CourseRelationship

# 定义课程关系规则
COURSE_RELATIONSHIPS_RULES = {
    # 格式：(from_code, to_code, relationship_type, strength, description)

    # 数学基础链
    ('05010039a', '05010040a', 'successor', 4, '高数A1后续'),
    ('05010039a', '05030034a', 'recommended_prerequisite', 3, '学习线性代数的基础'),
    ('05010040a', '05030010a', 'prerequisite', 4, '概率论学习基础'),

    # 物理基础链
    ('05020063a', '05020064a', 'successor', 4, '大学物理1之后'),

    # 电路与电子链
    ('03041310a', '03050085a', 'prerequisite', 5, '模拟电子基础'),
    ('03041310a', '03041311a', 'prerequisite', 4, '数字电子必需基础'),
    ('03050085a', '03050085a', 'corequisite', 5, '电路和模拟电子同时学习'),
    ('03050085a', '03041311a', 'recommended_prerequisite', 3, '数字电子的基础'),
    ('03041311a', '03031363a', 'prerequisite', 4, '微机原理基础'),

    # 控制系统链
    ('03010110a', '03031364a', 'prerequisite', 5, '计算机控制系统必需'),
    ('03010110a', '03010080b', 'successor', 3, '课程设计应用'),
    ('03010110a', '03015211a', 'related', 4, '现代控制理论补充'),
    ('03031364a', '03021375b', 'successor', 3, '控制软件基础'),
    ('03031364a', '03010073b', 'successor', 3, '课程设计应用'),

    # 微机原理链
    ('03031363a', '03031364a', 'prerequisite', 4, '计算机控制系统基础'),
    ('03031363a', '03031365b', 'successor', 3, '实验课程'),
    ('03031363a', '03031366b', 'successor', 3, '课程设计'),

    # 信号处理链（测控专业）
    ('05030010a', '03031370a', 'prerequisite', 4, '信号处理基础'),
    ('03031370a', '03031372b', 'prerequisite', 4, '虚拟仪器基础'),
    ('03031370a', '03031373b', 'prerequisite', 4, '智能测控系统基础'),

    # 传感器链
    ('03050085a', '03030092a', 'recommended_prerequisite', 3, '传感器检测基础'),
    ('03030092a', '03031381b', 'successor', 3, '传感器实验'),

    # 控制网络链
    ('03010110a', '03010063b', 'prerequisite', 3, '控制网络基础知识'),
    ('03010063b', '03021842b', 'related', 2, 'PLC应用相关'),

    # 智能感知工程链
    ('03010111b', '03030701b', 'recommended_prerequisite', 3, '反馈控制基础'),
    ('03030702a', '03030714a', 'recommended_prerequisite', 3, '数据结构基础'),
    ('03030704b', '03030705b', 'prerequisite', 4, '传感器调理电路基础'),
    ('03030704b', '03030711b', 'successor', 3, '实验课程'),
    ('03030714a', '03030714b', 'related', 3, '专业综合实训应用'),

    # 通识课程关系
    ('08010134a', '08010135a', 'successor', 4, '大学英语衔接'),
    ('08010135a', '08020002a', 'successor', 4, '大学英语3'),
    ('08020002a', '08020006a', 'successor', 4, '大学英语4'),
    ('09010011b', '09010013b', 'successor', 2, '形势与政策循环'),
    ('07010016a', '07010017a', 'successor', 2, '体育课程序列'),

    # 工程伦理与创业
    ('03010066b', 'option01', 'related', 1, '工程伦理相关'),
    ('04060003b', 'option05', 'related', 2, '创业基础相关'),

    # 实验与设计关系
    ('03041310a', '03101408b', 'successor', 3, '电路实验'),
    ('03050085a', '03101409b', 'successor', 3, '模拟电子技术实验'),
    ('03041311a', '03101410b', 'successor', 3, '数字电子技术实验'),
    ('03101408b', '03101411b', 'predecessor', 2, '电子技术课程设计前置'),

    # 替代课程（不能同时选）
    ('03030909b', '03030099b', 'conflict', 1, 'Java语言课程版本不同'),
    ('03030714a', '03030714b', 'conflict', 1, '机器学习两个版本'),
}


def create_course_relationships():
    """创建课程间的关系"""
    print("=" * 70)
    print("🔗 建立课程间的关系")
    print("=" * 70)

    try:
        db = SessionLocal()

        print("\n🔍 正在查询课程...")
        all_courses = db.query(Course).all()
        course_map = {course.course_code: course for course in all_courses}

        print(f"✅ 找到 {len(all_courses)} 门课程\n")

        print("📥 正在创建课程关系...")
        success_count = 0
        failed_count = 0

        for from_code, to_code, rel_type, strength, desc in COURSE_RELATIONSHIPS_RULES:
            try:
                from_course = course_map.get(from_code)
                to_course = course_map.get(to_code)

                # 允许部分课程不存在（如选修课等特殊代码）
                if not from_course or not to_course:
                    continue

                # 检查关系是否已存在
                existing = db.query(CourseRelationship).filter(
                    (CourseRelationship.from_course_id == from_course.id) &
                    (CourseRelationship.to_course_id == to_course.id) &
                    (CourseRelationship.relationship_type == rel_type)
                ).first()

                if not existing:
                    relationship = CourseRelationship(
                        from_course_id=from_course.id,
                        to_course_id=to_course.id,
                        relationship_type=rel_type,
                        strength=strength,
                        description=desc,
                        is_confirmed=True
                    )
                    db.add(relationship)
                    success_count += 1

            except Exception as e:
                failed_count += 1
                print(f"⚠️  创建关系失败 ({from_code} -> {to_code})：{str(e)[:50]}")

        db.commit()

        print("\n✅ 关系创建完成！")
        print(f"   - 成功创建：{success_count}条关系")
        print(f"   - 失败数量：{failed_count}条")

        # 显示统计信息
        print_relationship_statistics(db)

        db.close()

    except Exception as e:
        print(f"\n❌ 失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def print_relationship_statistics(db):
    """显示关系统计信息"""
    print("\n📊 关系统计信息：")
    print("-" * 70)

    # 按关系类型统计
    rel_types = db.query(CourseRelationship.relationship_type).distinct().all()

    print("按关系类型统计：")
    for (rel_type,) in rel_types:
        count = db.query(CourseRelationship).filter(
            CourseRelationship.relationship_type == rel_type
        ).count()
        print(f"  {rel_type:25s}: {count:3d}条")

    # 总计
    total = db.query(CourseRelationship).count()
    print(f"\n总计：{total}条关系")

    # 节点度数统计
    print("\n📈 课程关系度数统计（TOP 10）：")
    print("-" * 70)

    # 出度（作为前置课程）
    high_outdegree = db.query(
        Course.course_code,
        Course.course_name
    ).filter(
        Course.id.in_(
            db.query(CourseRelationship.from_course_id).group_by(
                CourseRelationship.from_course_id
            ).order_by(func.count(CourseRelationship.id).desc()).limit(10)
        )
    ).all()

    print("出度最高的课程（作为前置课程）：")
    for code, name in high_outdegree:
        count = db.query(CourseRelationship).filter(
            CourseRelationship.from_course_id == db.query(Course.id).filter(
                Course.course_code == code
            ).scalar()
        ).count()
        print(f"  {code:15s} {name:30s}: {count}门后续课程")


def query_course_dependencies(db, course_code):
    """查询课程的依赖关系"""
    print(f"\n🔍 查询课程 {course_code} 的依赖关系")
    print("-" * 70)

    course = db.query(Course).filter(Course.course_code == course_code).first()
    if not course:
        print(f"未找到课程 {course_code}")
        return

    # 查询前置课程
    prerequisites = db.query(CourseRelationship).filter(
        (CourseRelationship.to_course_id == course.id) &
        ((CourseRelationship.relationship_type == 'prerequisite') |
         (CourseRelationship.relationship_type == 'recommended_prerequisite'))
    ).all()

    if prerequisites:
        print("\n前置课程：")
        for rel in prerequisites:
            pre_course = db.query(Course).filter(Course.id == rel.from_course_id).first()
            print(f"  - {pre_course.course_code}: {pre_course.course_name}")
            print(f"    ({rel.relationship_type}, 强度:{rel.strength})")

    # 查询后续课程
    successors = db.query(CourseRelationship).filter(
        CourseRelationship.from_course_id == course.id
    ).all()

    if successors:
        print("\n后续课程/相关课程：")
        for rel in successors:
            suc_course = db.query(Course).filter(Course.id == rel.to_course_id).first()
            print(f"  - {suc_course.course_code}: {suc_course.course_name}")
            print(f"    ({rel.relationship_type}, 强度:{rel.strength})")


if __name__ == "__main__":
    create_course_relationships()

    # 演示查询
    db = SessionLocal()

    print("\n" + "=" * 70)
    print("📚 课程依赖关系查询示例")
    print("=" * 70)

    query_course_dependencies(db, '03010110a')  # 自动控制原理
    query_course_dependencies(db, '03031364a')  # 计算机控制系统
    query_course_dependencies(db, '03041310a')  # 电路

    db.close()
