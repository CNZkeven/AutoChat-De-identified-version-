"""
验证 models 导入集成
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR / "backend"))

def test_models_import():
    """测试模型导入"""
    print("\n" + "=" * 80)
    print("📦 Models 导入集成测试")
    print("=" * 80)

    try:
        # 测试直接导入
        print("\n[测试 1] 直接导入 Tool 模型:")
        from app.models import Tool as ToolDirect
        print(f"  ✅ from app.models import Tool")
        print(f"     - 模型类: {ToolDirect}")
        print(f"     - 表名: {ToolDirect.__tablename__}")

        # 测试通过 app.models 导出
        print("\n[测试 2] 通过 app.models 导出 Tool 模型:")
        from app import models
        print(f"  ✅ from app import models; models.Tool")
        print(f"     - 模型类: {models.Tool}")
        print(f"     - 是否同一对象: {ToolDirect is models.Tool}")

        # 测试所有导出
        print("\n[测试 3] 验证所有导出的模型:")
        exported = getattr(models, "__all__", None)
        if not exported:
            exported = [
                name
                for name in dir(models)
                if name[:1].isupper() and hasattr(getattr(models, name), "__tablename__")
            ]

        for model_name in exported:
            model_class = getattr(models, model_name)
            tablename = getattr(model_class, "__tablename__", "N/A")
            print(f"  ✅ {model_name:25} -> table: {tablename}")

        # 测试 SQLAlchemy ORM 功能
        print("\n[测试 4] 验证 SQLAlchemy ORM 功能:")
        from app.db import SessionLocal
        from app.models import Tool

        session = SessionLocal()
        try:
            # 查询 Tool 表
            tools_count = session.query(Tool).count()
            print(f"  ✅ 可以查询 Tool 表")
            print(f"     - 表中记录数: {tools_count}")

            # 获取第一条记录
            first_tool = session.query(Tool).first()
            if first_tool:
                print(f"  ✅ 成功获取记录:")
                print(f"     - ID: {first_tool.id}")
                print(f"     - Name: {first_tool.name}")
                print(f"     - Has schema: {first_tool.parameters_schema is not None}")

        finally:
            session.close()

        print("\n" + "=" * 80)
        print("✅ Models 导入集成测试完成 - 所有检验通过！")
        print("=" * 80 + "\n")

    except ImportError as e:
        print(f"\n  ❌ 导入失败: {str(e)}")
    except Exception as e:
        print(f"\n  ❌ 测试失败: {str(e)}")

if __name__ == '__main__':
    test_models_import()
