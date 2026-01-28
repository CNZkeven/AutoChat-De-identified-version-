#!/usr/bin/env python3
"""
初始化数据库

使用示例:
    python setup_db.py
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR / "backend"))

from app.config import DATABASE_URL  # noqa: E402
from app.db import Base, engine  # noqa: E402
import app.models  # noqa: E402


def init_database():
    """初始化数据库"""
    print("正在初始化数据库...")
    print(f"数据库URL: {DATABASE_URL}")

    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)

        print("✓ 数据库初始化成功！")
        print("\n创建的表:")
        print("  - users (用户表)")
        print("  - conversations (聊天会话表)")
        print("  - messages (聊天消息表)")
        print("  - knowledge / knowledge_embeddings (知识库表)")
        print("  - tools / courses / course_relationships / course_logs (业务表)")

    except Exception as e:
        print(f"✗ 数据库初始化失败: {e}")
        exit(1)


if __name__ == "__main__":
    init_database()
