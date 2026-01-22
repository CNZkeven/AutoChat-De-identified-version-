"""
课程数据补充脚本
补充缺失的课程性质、开课时间等字段
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from app.config import PROJECT_ROOT
from app.db import SessionLocal
from app.models import Course

# 课程性质推断规则
COURSE_NATURE_RULES = {
    # 电气工程及其自动化 - 必修课
    '03010110a': '专业必修',  # 自动控制原理
    '03010074a': '专业必修',  # 检测与仪表
    '03021843a': '专业必修',  # 电机与拖动基础
    '03021844a': '专业必修',  # 电力电子技术
    '03031363a': '专业必修',  # 微机原理与接口技术
    '03031364a': '专业必修',  # 计算机控制系统
    '03041310a': '专业必修',  # 电路
    '03041311a': '专业必修',  # 数字电子技术
    '03050085a': '专业必修',  # 模拟电子技术
    '05010039a': '学科必修',  # 高等数学A1
    '05010040a': '学科必修',  # 高等数学A2
    '05020063a': '学科必修',  # 大学物理1
    '05020064a': '学科必修',  # 大学物理2
    '05030034a': '学科必修',  # 线性代数
    '05030010a': '学科必修',  # 概率论与数理统计
    '07010016a': '通识必修',  # 体育1
    '07010017a': '通识必修',  # 体育2
    '07010018a': '通识必修',  # 体育3
    '07010019a': '通识必修',  # 体育4
    '08010134a': '通识必修',  # 大学英语1
    '08010135a': '通识必修',  # 大学英语2
    '08020002a': '通识必修',  # 大学英语3
    '08020006a': '通识必修',  # 大学英语4
    '09020021a': '通识必修',  # 马克思主义基本原理
    '09030043a': '通识必修',  # 毛泽东思想概论
    '09030044a': '通识必修',  # 习近平新时代思想概论
    '09050063a': '通识必修',  # 中国近现代史纲要
    '14000013b': '通识必修',  # 军事技能训练
    '14000016b': '通识必修',  # 军事理论与安全教育

    # 选修课
    '03010024b': '专业选修',  # 智能控制
    '03010062b': '专业选修',  # 船舶自动化系统
    '03010063b': '学科选修',  # 控制网络基础
    '03010065b': '专业选修',  # 人工智能导论
    '03010066b': '专业选修',  # 工程伦理
    '03030089b': '专业选修',  # 物联网技术
    '03040087b': '专业选修',  # 嵌入式系统
    '03040095b': '专业选修',  # 图像处理基础
    '03040096b': '专业选修',  # 机器视觉及应用
    '03040097b': '专业选修',  # 云计算与大数据分析
    '03021375b': '专业选修',  # 控制软件基础
    '03021842b': '专业选修',  # PLC原理及应用
    '04060003b': '专业选修',  # 创业基础
    '05030005b': '学科选修',  # 复变函数与积分变换

    # 测控技术与仪器
    '03030031a': '专业必修',  # 误差理论与数据处理
    '03030092a': '专业必修',  # 传感器与检测技术
    '03031370a': '专业必修',  # 信号分析与处理
    '03031374a': '专业必修',  # 导航系统原理

    # 智能感知工程
    '03030702a': '专业必修',  # 数据结构与算法
    '03030703b': '专业必修',  # 智能感知工程专业导论
    '03030714a': '专业必修',  # 机器学习与数据挖掘

    # 实验课
    '03101408b': '实践课程',  # 电路实验
    '03101409b': '实践课程',  # 模拟电子技术实验
    '03101410b': '实践课程',  # 数字电子技术实验
    '03031381b': '实践课程',  # 传感器与检测技术实验
    '03021845b': '实践课程',  # 电机与拖动实验
    '03031365b': '实践课程',  # 微机原理与接口技术实验

    # 课程设计
    '03010068b': '课程设计',  # 运动控制系统课程设计
    '03010073b': '课程设计',  # 计算机控制系统课程设计
    '03010080b': '课程设计',  # 自动控制理论课程设计
    '03101411b': '课程设计',  # 电子技术课程设计
    '03031309b': '课程设计',  # 虚拟仪器课程设计
    '03031366b': '课程设计',  # 微机原理与接口技术课程设计
    '03031382b': '课程设计',  # 智能测控系统课程设计

    # 实习
    '03010069b': '实习',  # 专业实习
    '03031383b': '实习',  # 专业实习

    # 综合实训
    '03015216b': '综合实训',  # 自动化专业综合实训
    '03031384b': '综合实训',  # 测控技术与仪器综合实训
    '03030714b': '综合实训',  # 智能感知工程专业综合实训

    # 毕业设计
    '03015217b': '毕业设计',  # 毕业设计
    '03031385b': '毕业设计',  # 毕业设计

    # 通识选修
    '09010011b': '通识选修',  # 形势与政策1
    '09010012b': '通识选修',  # 形势与政策实践1
    '09010013b': '通识选修',  # 形势与政策2
    '09010014b': '通识选修',  # 形势与政策实践2
    '09010015b': '通识选修',  # 形势与政策3
    '09010016b': '通识选修',  # 形势与政策实践3
    '09010017b': '通识选修',  # 形势与政策4
    '09010018b': '通识选修',  # 形势与政策实践4
    '09040032b': '通识选修',  # 思想道德与法治
    '09130106b': '通识选修',  # 职业生涯规划
    '09130107b': '通识选修',  # 国学通论
    '13040002b': '通识选修',  # 心理健康教育
    '75010006b': '通识选修',  # 工程基础训练
    '99010002b': '通识选修',  # 劳动教育
}

# 开课时间规则（基于课程代码和课程类型）
OFFERING_SEMESTER_RULES = {
    # 第一学年秋季（第1学期）
    '05010039a': '2024-2025_1',  # 高等数学A1
    '08010134a': '2024-2025_1',  # 大学英语1
    '05020063a': '2024-2025_1',  # 大学物理1
    '19010130a': '2024-2025_1',  # C++程序设计

    # 第一学年春季（第2学期）
    '05010040a': '2024-2025_2',  # 高等数学A2
    '08010135a': '2024-2025_2',  # 大学英语2
    '05020064a': '2024-2025_2',  # 大学物理2
    '05030034a': '2024-2025_2',  # 线性代数
    '05060069b': '2024-2025_2',  # 物理实验2

    # 第二学年秋季（第3学期）
    '03041310a': '2024-2025_1',  # 电路
    '03050085a': '2024-2025_2',  # 模拟电子技术
    '08020002a': '2024-2025_1',  # 大学英语3
    '05030010a': '2024-2025_2',  # 概率论与数理统计

    # 第三学年秋季（第5学期）
    '03010110a': '2024-2025_2',  # 自动控制原理
    '03031363a': '2024-2025_2',  # 微机原理与接口技术

    # 第三学年春季（第6学期）
    '03031364a': '2025-2026_1',  # 计算机控制系统
    '03041311a': '2024-2025_1',  # 数字电子技术

    # 实践课程
    '03101408b': '2024-2025_1',  # 电路实验
}

# JSON数据文件默认路径（可通过 --json 或 COURSES_JSON_PATH 覆盖）
DEFAULT_JSON_PATH = PROJECT_ROOT / "data" / "extracted_courses_data.json"


def resolve_courses_json_path(cli_value: str | None = None) -> Path:
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


def infer_course_nature(course_code, course_name):
    """推断课程性质"""
    if course_code in COURSE_NATURE_RULES:
        return COURSE_NATURE_RULES[course_code]

    # 基于课程名称的规则推断
    keywords_map = {
        '实验': '实践课程',
        '设计': '课程设计',
        '实习': '实习',
        '综合实训': '综合实训',
        '毕业设计': '毕业设计',
        '形势与政策': '通识选修',
        '体育': '通识必修',
        '英语': '通识必修',
        '思想': '通识必修',
        '高等数学': '学科必修',
        '物理': '学科必修',
        '线性代数': '学科必修',
    }

    for keyword, nature in keywords_map.items():
        if keyword in course_name:
            return nature

    # 默认值
    return '未明确'


def infer_offering_semester(course_code, course_name, course_type):
    """推断开课时间"""
    if course_code in OFFERING_SEMESTER_RULES:
        return OFFERING_SEMESTER_RULES[course_code]

    # 基于课程类型的推断
    if course_type == '实践课程' or '实验' in course_name:
        return '每学期'
    elif course_type == '通识必修':
        return '指定学期'
    else:
        return '未明确'


def import_courses_to_course_table(json_path: str | None = None):
    """从Knowledge表导入课程到Course表"""
    print("=" * 70)
    print("📚 开始补充课程数据")
    print("=" * 70)

    try:
        # 加载JSON数据
        print("\n📖 正在加载JSON数据...")
        resolved_path = resolve_courses_json_path(json_path)
        with resolved_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        courses_data = data.get('courses', [])
        print(f"✅ 加载成功！共 {len(courses_data)} 门课程")

        db = SessionLocal()

        print("\n📥 正在导入课程到Course表...")
        success_count = 0
        updated_count = 0

        for idx, course_data in enumerate(courses_data, 1):
            try:
                course_code = course_data.get('课程代码', '').strip()
                if not course_code:
                    continue

                major = course_data.get('所属专业', '')

                # 检查是否已存在（按课程代码和专业）
                existing = db.query(Course).filter(
                    (Course.course_code == course_code) &
                    (Course.major == major)
                ).first()

                # 推断课程性质
                course_nature = course_data.get('课程性质', '未明确')
                if course_nature == '未明确':
                    course_nature = infer_course_nature(course_code, course_data.get('课程名称', ''))

                # 推断开课时间
                offering_semester = course_data.get('开课时间', '未明确')
                if offering_semester == '未明确':
                    offering_semester = infer_offering_semester(
                        course_code,
                        course_data.get('课程名称', ''),
                        course_nature
                    )

                # 清理课程代码中的空格
                clean_code = course_code.replace(' ', '')

                course_obj = Course(
                    course_code=clean_code,
                    course_name=course_data.get('课程名称', '').strip(),
                    credits=course_data.get('学分', ''),
                    course_nature=course_nature,
                    major=major,
                    is_exam_course=course_data.get('是否为考试课', '否') == '是',
                    is_investigation_course=course_data.get('是否为考查课', '否') == '是',
                    instructor=course_data.get('任课教师', ''),
                    offering_semester=offering_semester,
                    total_hours=course_data.get('总学时', ''),
                    lecture_hours=course_data.get('授课学时', ''),
                    experiment_hours=course_data.get('实验时数', ''),
                    syllabus_status=course_data.get('课程大纲', ''),
                    is_active=True,
                    data_source=resolved_path.name,
                    data_quality_score=calculate_quality_score(course_data)
                )

                if existing:
                    # 更新现有记录
                    existing.course_nature = course_nature
                    existing.offering_semester = offering_semester
                    existing.instructor = course_obj.instructor
                    existing.data_quality_score = calculate_quality_score(course_data)
                    existing.updated_at = datetime.utcnow()
                    updated_count += 1
                else:
                    db.add(course_obj)
                    success_count += 1

                if (idx % 50) == 0:
                    try:
                        db.commit()
                        print(f"   已处理 {idx}/{len(courses_data)} 条...")
                    except Exception:
                        db.rollback()

            except Exception as e:
                print(f"⚠️  第{idx}条课程处理失败：{str(e)[:100]}")
                db.rollback()
                continue

        db.commit()

        print("\n✅ 导入完成！")
        print(f"   - 新增课程：{success_count}条")
        print(f"   - 更新课程：{updated_count}条")

        # 统计字段填充情况
        print("\n📊 字段填充统计：")
        print_field_statistics(db)

        db.close()

    except Exception as e:
        print(f"\n❌ 导入失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def calculate_quality_score(course_data):
    """计算课程数据质量评分"""
    score = 0
    max_score = 0

    # 检查每个字段的完整性
    fields = [
        '课程代码',
        '课程名称',
        '学分',
        '课程性质',
        '所属专业',
        '是否为考试课',
        '是否为考查课',
        '任课教师',
        '课程大纲',
        '开课时间',
        '总学时',
        '授课学时',
        '实验时数'
    ]

    for field in fields:
        max_score += 1
        value = course_data.get(field, '')
        if value and str(value).strip() and str(value).strip() != '未明确' and str(value).strip() != '未排课/无数据':
            score += 1

    return int(score / max_score * 100) if max_score > 0 else 0


def print_field_statistics(db):
    """打印字段填充统计"""
    courses = db.query(Course).all()
    total = len(courses)

    if total == 0:
        return

    stats = {
        '课程性质': sum(1 for c in courses if c.course_nature and c.course_nature != '未明确'),
        '开课时间': sum(1 for c in courses if c.offering_semester and c.offering_semester != '未明确'),
        '任课教师': sum(1 for c in courses if c.instructor and c.instructor != '未排课/无数据'),
        '总学时': sum(1 for c in courses if c.total_hours and c.total_hours != '未明确'),
        '授课学时': sum(1 for c in courses if c.lecture_hours and c.lecture_hours != '未明确'),
        '实验时数': sum(1 for c in courses if c.experiment_hours and c.experiment_hours != '未明确'),
    }

    for field, count in stats.items():
        percentage = count / total * 100
        print(f"  {field:15s}: {count:3d}/{total} ({percentage:5.1f}%)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="补充课程数据到 Course 表")
    parser.add_argument("--json", dest="json_path", help="课程 JSON 文件路径")
    args = parser.parse_args()
    import_courses_to_course_table(args.json_path)
