"""
初始化全局工具数据到数据库
该脚本将把核心工具定义插入数据库，支持幂等性操作（Upsert）
"""

from datetime import datetime

from sqlalchemy import func, select

from app.db import Base, SessionLocal, engine
from app.models import Tool


def build_json_schema(description: str, parameters: dict) -> dict:
    """
    将参数定义转换为标准的 JSON Schema 格式

    Args:
        description: 工具描述
        parameters: 参数定义字典，格式为 {param_name: {type, required, ...}}

    Returns:
        符合 JSON Schema 标准的完整定义
    """
    properties = {}
    required = []

    for param_name, param_info in parameters.items():
        param_type = param_info.get('type', 'string')
        param_desc = param_info.get('description', '')

        # 构建基本属性定义
        prop_def = {
            'type': param_type,
            'description': param_desc
        }

        # 添加 enum（如果存在）
        if 'enum' in param_info:
            prop_def['enum'] = param_info['enum']

        properties[param_name] = prop_def

        # 记录必填字段
        if param_info.get('required', False):
            required.append(param_name)

    return {
        'type': 'object',
        'description': description,
        'properties': properties,
        'required': required,
        'additionalProperties': False
    }


def upsert_tool(session, name: str, description: str, parameters_schema: dict) -> Tool:
    """
    幂等性插入或更新工具定义

    Args:
        session: 数据库会话
        name: 工具名称
        description: 工具描述
        parameters_schema: JSON Schema 参数定义

    Returns:
        Tool 对象
    """
    # 查询现有工具
    stmt = select(Tool).where(Tool.name == name)
    existing_tool = session.execute(stmt).scalars().first()

    if existing_tool:
        # 更新现有工具
        existing_tool.description = description
        existing_tool.parameters_schema = parameters_schema
        session.flush()
        return existing_tool
    else:
        # 创建新工具
        new_tool = Tool(
            name=name,
            description=description,
            parameters_schema=parameters_schema,
            created_at=datetime.utcnow()
        )
        session.add(new_tool)
        session.flush()
        return new_tool


def init_tools_data():
    """初始化所有工具数据"""

    # 创建所有表（如果不存在）
    Base.metadata.create_all(bind=engine)

    # 获取数据库会话
    session = SessionLocal()

    try:
        # 工具 1: get_user_comprehensive_profile
        tool1_params = {
            'user_id': {
                'type': 'string',
                'description': '用户唯一标识',
                'required': True
            },
            'scope': {
                'type': 'string',
                'description': '查询维度。basic=基础信息, academic=成绩/图谱, execution=习惯, history=任务/项目',
                'enum': ['basic', 'academic', 'execution', 'history'],
                'required': True
            }
        }
        tool1_schema = build_json_schema(
            '获取用户的静态身份与动态状态，用于个性化分析。',
            tool1_params
        )
        upsert_tool(
            session,
            'get_user_comprehensive_profile',
            '获取用户的静态身份与动态状态，用于个性化分析。',
            tool1_schema
        )

        # 工具 2: query_institutional_database
        tool2_params = {
            'user_id': {
                'type': 'string',
                'description': '用户唯一标识（可选，用于按专业过滤培养方案）',
                'required': False
            },
            'category': {
                'type': 'string',
                'description': '数据类别',
                'enum': ['competition_history', 'curriculum', 'research_strength'],
                'required': True
            },
            'keywords': {
                'type': 'string',
                'description': '检索关键词（如赛事名、课程名）',
                'required': True
            }
        }
        tool2_schema = build_json_schema(
            '检索学校内部的教务、历史战绩及培养方案数据。',
            tool2_params
        )
        upsert_tool(
            session,
            'query_institutional_database',
            '检索学校内部的教务、历史战绩及培养方案数据。',
            tool2_schema
        )

        # 工具 3: search_knowledge_repository
        tool3_params = {
            'source': {
                'type': 'string',
                'description': '数据源',
                'enum': ['internet', 'internal_kb', 'academic_db'],
                'required': True
            },
            'query_type': {
                'type': 'string',
                'description': '查询意图（如 competition_info, skill_inference, spirit_genealogy）',
                'required': True
            },
            'keywords': {
                'type': 'string',
                'description': '核心检索词',
                'required': True
            }
        }
        tool3_schema = build_json_schema(
            '检索外部互联网数据、垂类专业知识库及学术资源。',
            tool3_params
        )
        upsert_tool(
            session,
            'search_knowledge_repository',
            '检索外部互联网数据、垂类专业知识库及学术资源。',
            tool3_schema
        )

        # 工具 4: execute_strategy_engine
        tool4_params = {
            'action': {
                'type': 'string',
                'description': '执行的具体动作',
                'enum': ['recommend_advisor', 'analyze_team_model', 'generate_plan', 'check_error_book', 'log_milestone'],
                'required': True
            },
            'context_data': {
                'type': 'object',
                'description': '动作所需的上下文参数字典（如目标赛事名、学生专业）',
                'required': True
            }
        }
        tool4_schema = build_json_schema(
            '执行具体的分析算法、策略生成及任务管理操作。',
            tool4_params
        )
        upsert_tool(
            session,
            'execute_strategy_engine',
            '执行具体的分析算法、策略生成及任务管理操作。',
            tool4_schema
        )

        # 工具 5: fetch_dm_student_academic_data
        tool5_params = {
            'action': {
                'type': 'string',
                'description': '本地读库学业数据操作类型',
                'enum': [
                    'list_course_offerings',
                    'course_offering',
                    'course_objectives',
                    'course_grades',
                    'course_achievements',
                    'grade_distribution',
                    'summary',
                ],
                'required': True
            },
            'offering_id': {
                'type': 'integer',
                'description': '课程开设ID（除list/summary外必填）',
                'required': False
            },
            'term': {
                'type': 'string',
                'description': '学期名称（可选，过滤课程清单）',
                'required': False
            },
            'min_sample': {
                'type': 'integer',
                'description': '班级分布最小样本数（grade_distribution/summary可用）',
                'required': False
            },
            'max_offerings': {
                'type': 'integer',
                'description': 'summary 模式下最多返回的课程数量',
                'required': False
            },
            'include_grades': {
                'type': 'boolean',
                'description': 'summary 模式下是否包含成绩明细',
                'required': False
            },
            'include_distribution': {
                'type': 'boolean',
                'description': 'summary 模式下是否包含班级分布',
                'required': False
            }
        }
        tool5_schema = build_json_schema(
            '访问本地读库的课程目标/成绩/达成度数据（仅限本人）。',
            tool5_params
        )
        upsert_tool(
            session,
            'fetch_dm_student_academic_data',
            '访问本地读库的课程目标/成绩/达成度数据（仅限本人）。',
            tool5_schema
        )

        # 提交事务
        session.query(Tool).filter(Tool.name == "fetch_external_student_academic_data").delete()
        session.commit()
        print("✓ 工具数据初始化成功！已插入/更新 5 个工具定义。")

        # 验证数据
        stmt = select(func.count(Tool.id))
        count = session.execute(stmt).scalar()
        print(f"✓ 数据库中现有工具总数: {count}")

        # 列出所有工具
        stmt = select(Tool).order_by(Tool.created_at)
        tools = session.execute(stmt).scalars().all()
        print("\n已初始化的工具列表:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description[:50]}...")

    except Exception as e:
        session.rollback()
        print(f"✗ 初始化失败: {str(e)}")
        raise
    finally:
        session.close()


if __name__ == '__main__':
    init_tools_data()
