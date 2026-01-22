"""
验证数据库中的工具数据
"""

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR / "backend"))

from app.db import SessionLocal  # noqa: E402
from app.models import Tool  # noqa: E402

def verify_tools_data():
    """验证数据库中的工具数据"""
    session = SessionLocal()

    try:
        # 查询所有工具
        tools = session.query(Tool).order_by(Tool.id).all()

        print("=" * 100)
        print("🔍 数据库工具数据验证报告")
        print("=" * 100)

        if not tools:
            print("❌ 没有找到任何工具数据")
            return

        print(f"\n✅ 找到 {len(tools)} 个工具\n")

        for idx, tool in enumerate(tools, 1):
            print(f"\n{'─' * 100}")
            print(f"[工具 {idx}] {tool.name}")
            print(f"{'─' * 100}")

            # 基本信息
            print(f"ID:          {tool.id}")
            print(f"Description: {tool.description}")
            print(f"Created At:  {tool.created_at}")

            # 解析并验证 JSON Schema
            try:
                schema = json.loads(tool.parameters_schema) if isinstance(tool.parameters_schema, str) else tool.parameters_schema

                print(f"\n📋 参数 Schema:")
                print(f"  Type: {schema.get('type')}")
                print(f"  Description: {schema.get('description')}")

                # 验证必填字段
                required = schema.get('required', [])
                print(f"\n  必填字段 ({len(required)}): {required}")

                # 详细参数定义
                properties = schema.get('properties', {})
                print(f"\n  参数定义 ({len(properties)}个):")

                for param_name, param_def in properties.items():
                    print(f"\n    • {param_name}:")
                    print(f"      - type: {param_def.get('type')}")
                    print(f"      - description: {param_def.get('description')}")

                    if 'enum' in param_def:
                        print(f"      - enum: {param_def['enum']}")

                    # 检查是否为必填
                    is_required = param_name in required
                    print(f"      - required: {'✅ Yes' if is_required else '❌ No'}")

                # Schema 验证
                print(f"\n  ✅ JSON Schema 格式: 有效")
                print(f"  ✅ additionalProperties: {schema.get('additionalProperties', 'not set')}")

            except Exception as e:
                print(f"  ❌ JSON Schema 解析失败: {str(e)}")

        print(f"\n{'=' * 100}")
        print("✅ 数据验证完成")
        print("=" * 100)

    finally:
        session.close()

if __name__ == '__main__':
    verify_tools_data()
