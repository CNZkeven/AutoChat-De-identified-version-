#!/usr/bin/env python3
"""
API调用示例 - 展示如何使用各个端点

需要先启动服务器:
    python run.py
"""

import requests
import json

BASE_URL = "http://localhost:8000"


class AgentAPIClient:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.token = None

    def register(self, username: str, email: str, password: str):
        """注册用户"""
        url = f"{self.base_url}/api/v1/auth/register"
        data = {
            "username": username,
            "email": email,
            "password": password
        }
        response = requests.post(url, json=data)
        print(f"[注册用户] {response.status_code}")
        return response.json()

    def login(self, username: str, password: str):
        """登录用户"""
        url = f"{self.base_url}/api/v1/auth/login"
        data = {
            "username": username,
            "password": password
        }
        response = requests.post(url, json=data)
        result = response.json()
        if "access_token" in result:
            self.token = result["access_token"]
        print(f"[登录用户] {response.status_code}")
        return result

    def create_chat_session(self, title: str = None):
        """创建聊天会话"""
        url = f"{self.base_url}/api/v1/chat/sessions?token={self.token}"
        data = {"title": title}
        response = requests.post(url, json=data)
        print(f"[创建会话] {response.status_code}")
        return response.json()

    def add_message(self, session_id: int, role: str, content: str):
        """添加聊天消息"""
        url = f"{self.base_url}/api/v1/chat/sessions/{session_id}/messages?token={self.token}"
        data = {
            "role": role,
            "content": content
        }
        response = requests.post(url, json=data)
        print(f"[添加消息] {response.status_code}")
        return response.json()

    def create_knowledge(self, title: str, content: str, category: str = None):
        """创建知识条目"""
        url = f"{self.base_url}/api/v1/knowledge/?token={self.token}"
        data = {
            "title": title,
            "content": content,
            "category": category
        }
        response = requests.post(url, json=data)
        print(f"[创建知识] {response.status_code}")
        return response.json()

    def search_rag(self, query: str, top_k: int = 5):
        """搜索相关知识"""
        url = f"{self.base_url}/api/v1/rag/search?token={self.token}"
        data = {
            "query": query,
            "top_k": top_k,
            "similarity_threshold": 0.5
        }
        response = requests.post(url, json=data)
        print(f"[RAG搜索] {response.status_code}")
        return response.json()

    def get_rag_context(self, query: str):
        """获取RAG上下文"""
        url = f"{self.base_url}/api/v1/rag/context?token={self.token}&query={query}"
        response = requests.post(url)
        print(f"[获取上下文] {response.status_code}")
        return response.json()


def example_workflow():
    """演示工作流"""
    print("=" * 60)
    print("Agent AI Backend API 使用示例")
    print("=" * 60)

    client = AgentAPIClient()

    # 1. 注册用户
    print("\n1. 注册新用户...")
    user_data = client.register("testuser", "test@example.com", "<your-password>")
    print(json.dumps(user_data, indent=2, ensure_ascii=False))

    # 2. 登录
    print("\n2. 用户登录...")
    login_result = client.login("testuser", "<your-password>")
    print(f"Token: {client.token[:50]}...")

    # 3. 创建知识条目
    print("\n3. 创建知识条目...")
    knowledge_data = client.create_knowledge(
        title="Python基础教程",
        content="Python是一种高级编程语言。它具有简单易学的语法，强大的功能库，以及广泛的应用领域。" + \
                "Python可用于Web开发、数据分析、人工智能、自动化脚本等多个领域。" * 10,
        category="教程"
    )
    knowledge_id = knowledge_data.get("id")
    print(f"创建知识ID: {knowledge_id}")

    # 4. 创建聊天会话
    print("\n4. 创建聊天会话...")
    session_data = client.create_chat_session("Python讨论")
    session_id = session_data.get("id")
    print(f"创建会话ID: {session_id}")

    # 5. 添加聊天消息
    print("\n5. 添加聊天消息...")
    client.add_message(session_id, "user", "Python有什么特点?")
    client.add_message(session_id, "assistant", "Python是一种简单易学的编程语言...")

    # 6. 搜索相关知识 (RAG)
    print("\n6. 搜索相关知识...")
    rag_results = client.search_rag("Python编程特点", top_k=3)
    print(json.dumps(rag_results, indent=2, ensure_ascii=False))

    # 7. 获取增强上下文
    print("\n7. 获取RAG上下文...")
    context = client.get_rag_context("Python是什么")
    print(json.dumps(context, indent=2, ensure_ascii=False))

    print("\n" + "=" * 60)
    print("示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    try:
        example_workflow()
    except requests.exceptions.ConnectionError:
        print("错误: 无法连接到服务器")
        print("请确保服务器正在运行: python run.py")
    except Exception as e:
        print(f"错误: {e}")
