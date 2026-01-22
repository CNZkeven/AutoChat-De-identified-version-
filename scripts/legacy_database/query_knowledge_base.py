"""
课程型智能体知识库查询与使用示例
演示如何从知识库中查询和使用信息
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR / "backend"))

from app.db import SessionLocal  # noqa: E402
from app.models import Knowledge  # noqa: E402


def search_by_category(category_name, limit=5):
    """按知识库类别查询"""
    print(f"\n📚 查询知识库类别：{category_name}")
    print("-" * 70)

    try:
        db = SessionLocal()

        docs = db.query(Knowledge).filter(
            Knowledge.category == category_name
        ).limit(limit).all()

        if not docs:
            print(f"未找到相关知识库")
            return

        print(f"找到 {len(docs)} 条记录（显示前{limit}条）：\n")

        for idx, doc in enumerate(docs, 1):
            print(f"{idx}. 📖 {doc.title}")
            # 显示前150字预览
            preview = doc.content[:200] if doc.content else "无内容"
            print(f"   预览：{preview}...")
            print()

        db.close()

    except Exception as e:
        print(f"❌ 查询失败：{e}")


def search_course_guidance(major_name):
    """查询专业选课指南"""
    print(f"\n📚 {major_name}专业选课指南")
    print("-" * 70)

    try:
        db = SessionLocal()

        doc = db.query(Knowledge).filter(
            Knowledge.category == 'course_guidance',
            Knowledge.source.ilike(f'%{major_name}%')
        ).first()

        if doc:
            print(f"✅ 找到指南：{doc.title}\n")
            print(doc.content[:1500])
            print("\n... [内容已截断，完整内容已保存在数据库]")
        else:
            print(f"未找到 {major_name} 的选课指南")

        db.close()

    except Exception as e:
        print(f"❌ 查询失败：{e}")


def search_faq(keyword):
    """搜索常见问题"""
    print(f"\n❓ 搜索常见问题：'{keyword}'")
    print("-" * 70)

    try:
        db = SessionLocal()

        # 在常见问题库中搜索
        doc = db.query(Knowledge).filter(
            Knowledge.category == 'course_content',
            Knowledge.source.ilike('%常见问答%'),
            Knowledge.content.ilike(f'%{keyword}%')
        ).first()

        if doc:
            print(f"✅ 找到相关问题！\n")
            # 查找包含关键词的行
            lines = doc.content.split('\n')
            context_lines = []
            for i, line in enumerate(lines):
                if keyword in line.lower():
                    # 显示问题及其后面的答案
                    start = max(0, i-1)
                    end = min(len(lines), i+6)
                    context_lines.extend(lines[start:end])
                    context_lines.append("---")

            if context_lines:
                print('\n'.join(context_lines[:20]))
        else:
            print(f"未找到包含 '{keyword}' 的问答")

        db.close()

    except Exception as e:
        print(f"❌ 查询失败：{e}")


def show_knowledge_stats():
    """显示知识库统计信息"""
    print(f"\n📊 知识库统计信息")
    print("-" * 70)

    try:
        db = SessionLocal()

        # 总计数
        total = db.query(Knowledge).count()
        print(f"总知识库记录数：{total}条\n")

        # 按类别统计
        categories = {
            'course_system': '课程体系知识库',
            'course_guidance': '选课指导知识库',
            'course_content': '课程内容知识库',
            'data_maintenance': '数据维护知识库'
        }

        print("📂 专属知识库统计：")
        for cat_code, cat_name in categories.items():
            count = db.query(Knowledge).filter(Knowledge.category == cat_code).count()
            percentage = (count / total * 100) if total > 0 else 0
            print(f"  {cat_name:20s}: {count:2d}条 ({percentage:.1f}%)")

        # 课程数据统计
        print(f"\n📚 课程数据统计：")
        majors = [
            ('智能感知工程', 'course_智能感知工程'),
            ('测控技术与仪器', 'course_测控技术与仪器'),
            ('电气工程及其自动化', 'course_电气工程及其自动化')
        ]

        for major_name, category in majors:
            count = db.query(Knowledge).filter(Knowledge.category == category).count()
            print(f"  {major_name:20s}: {count:2d}门课程")

        db.close()

    except Exception as e:
        print(f"❌ 查询失败：{e}")


def get_course_system_info():
    """获取课程体系完整信息"""
    print(f"\n📚 课程体系与培养方案")
    print("-" * 70)

    try:
        db = SessionLocal()

        docs = db.query(Knowledge).filter(
            Knowledge.category == 'course_system'
        ).all()

        print(f"找到 {len(docs)} 个课程体系文档：\n")

        for doc in docs:
            print(f"📖 {doc.title}")
            print(f"   来源：{doc.source}")
            print()

        db.close()

    except Exception as e:
        print(f"❌ 查询失败：{e}")


def intelligent_course_advisor(query):
    """智能课程咨询（示例）"""
    print(f"\n🤖 智能课程咨询：'{query}'")
    print("-" * 70)

    try:
        db = SessionLocal()

        # 多条件搜索
        results = db.query(Knowledge).filter(
            (Knowledge.title.ilike(f'%{query}%')) |
            (Knowledge.content.ilike(f'%{query}%'))
        ).limit(5).all()

        if results:
            print(f"找到 {len(results)} 条相关信息：\n")
            for idx, doc in enumerate(results, 1):
                print(f"{idx}. 📖 {doc.title} [{doc.category}]")
                # 显示匹配位置的预览
                if query in doc.content:
                    pos = doc.content.find(query)
                    preview_start = max(0, pos - 50)
                    preview_end = min(len(doc.content), pos + 150)
                    preview = doc.content[preview_start:preview_end]
                    print(f"   匹配内容：...{preview}...")
                print()
        else:
            print("未找到相关信息，请尝试其他查询方式")

        db.close()

    except Exception as e:
        print(f"❌ 查询失败：{e}")


def main():
    """主函数 - 演示各种知识库查询"""
    print("=" * 70)
    print("🎓 课程型智能体知识库查询演示")
    print("=" * 70)

    # 显示统计
    show_knowledge_stats()

    # 课程体系查询
    get_course_system_info()

    # 专业选课指南查询
    search_course_guidance('电气工程及其自动化')

    # 常见问题查询
    search_faq('自动控制原理')
    search_faq('实验报告')

    # 分类查询
    search_by_category('course_system', limit=5)
    search_by_category('course_guidance', limit=3)
    search_by_category('course_content', limit=2)
    search_by_category('data_maintenance', limit=2)

    # 智能咨询示例
    intelligent_course_advisor('课程难度')
    intelligent_course_advisor('学分规划')

    print("\n" + "=" * 70)
    print("✨ 查询演示完成！")
    print("=" * 70)
    print("\n💡 可用查询功能：")
    print("  1. search_by_category(category_name) - 按类别查询")
    print("  2. search_course_guidance(major_name) - 查询选课指南")
    print("  3. search_faq(keyword) - 搜索常见问题")
    print("  4. get_course_system_info() - 获取课程体系信息")
    print("  5. intelligent_course_advisor(query) - 智能咨询")
    print("=" * 70)


if __name__ == "__main__":
    main()
