#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Dec 12 14:30:48 2025

@author: emmahu
"""

import streamlit as st
import pandas as pd
import random
import os
import matplotlib.pyplot as plt
from datetime import datetime
import hashlib
import time

st.set_page_config(
    page_title="英语语法能力测试",
    layout="wide"
)

# ========== 第1步：加载题库（只执行一次） ==========
@st.cache_data
def load_question_bank():
    """加载题库 - 使用缓存，只执行一次"""
    print("📚 加载题库")
    
    excel_file = "语言测试/语言测试题库.xlsx"
    if not os.path.exists(excel_file):
        st.error(f"未找到题库文件：{excel_file}")
        return []
    
    try:
        easy_df = pd.read_excel(excel_file, sheet_name='Sheet1')
        medium_df = pd.read_excel(excel_file, sheet_name='Sheet2')
        hard_df = pd.read_excel(excel_file, sheet_name='Sheet3')
        
        question_bank = []
        
        def add_questions(df, difficulty):
            for _, row in df.iterrows():
                if pd.isna(row.get('question')) or pd.isna(row.get('correct_option')):
                    continue
                
                try:
                    qid = int(row['id'])
                except:
                    continue
                
                # 转换正确答案
                correct_option = str(row['correct_option']).strip().upper()
                correct_index = 0
                if correct_option == 'A': correct_index = 0
                elif correct_option == 'B': correct_index = 1
                elif correct_option == 'C': correct_index = 2
                elif correct_option == 'D': correct_index = 3
                
                question = {
                    'id': f"{difficulty}_{qid}",
                    'question': str(row['question']).strip(),
                    'options': [
                        str(row['option_a']).strip() if not pd.isna(row.get('option_a')) else "",
                        str(row['option_b']).strip() if not pd.isna(row.get('option_b')) else "",
                        str(row['option_c']).strip() if not pd.isna(row.get('option_c')) else "",
                        str(row['option_d']).strip() if not pd.isna(row.get('option_d')) else ""
                    ],
                    'correct': correct_index,
                    'difficulty': difficulty
                }
                question_bank.append(question)
        
        add_questions(easy_df, 'easy')
        add_questions(medium_df, 'medium')
        add_questions(hard_df, 'hard')
        
        print(f"✅ 题库加载完成: {len(question_bank)} 题")
        return question_bank
        
    except Exception as e:
        st.error(f"加载题库失败: {str(e)}")
        return []

# ========== 第2步：初始化session state ==========
def init_session_state():
    """初始化所有状态"""
    
    # 核心状态
    if 'test_started' not in st.session_state:
        st.session_state.test_started = False
    
    if 'test_finished' not in st.session_state:
        st.session_state.test_finished = False
    
    if 'user_name' not in st.session_state:
        st.session_state.user_name = ""
    
    # 题目和答案管理
    if 'current_question' not in st.session_state:
        st.session_state.current_question = None
    
    if 'current_question_id' not in st.session_state:
        st.session_state.current_question_id = None
    
    if 'used_question_ids' not in st.session_state:
        st.session_state.used_question_ids = set()
    
    if 'user_answers' not in st.session_state:
        st.session_state.user_answers = []
    
    # 自适应逻辑
    if 'current_difficulty' not in st.session_state:
        st.session_state.current_difficulty = 'medium'
    
    if 'question_number' not in st.session_state:
        st.session_state.question_number = 1
    
    if 'first_two_answers' not in st.session_state:
        st.session_state.first_two_answers = []
    
    if 'test_id' not in st.session_state:
        st.session_state.test_id = ""
    
    # 历史记录
    if 'test_history' not in st.session_state:
        st.session_state.test_history = []

# ========== 第3步：题目选择逻辑 ==========
def select_question(question_bank, target_difficulty):
    """选择一道题目 - 确保不重复"""
    
    # 获取所有题目
    all_questions = question_bank
    used_ids = st.session_state.used_question_ids
    
    current_q = st.session_state.question_number
    print(f"\n🎯 选择第 {current_q} 题")
    print(f"目标难度: {target_difficulty}")
    print(f"已用题目数: {len(used_ids)}")
    
    # 如果已经有当前题目，直接返回
    if st.session_state.current_question_id:
        for q in all_questions:
            if q['id'] == st.session_state.current_question_id:
                print(f"📄 使用现有题目: {q['id']}")
                return q
    
    # 选择新题目
    # 1. 优先选择目标难度的未用题目
    target_questions = [q for q in all_questions if q['difficulty'] == target_difficulty]
    available = [q for q in target_questions if q['id'] not in used_ids]
    
    if available:
        selected = random.choice(available)
        print(f"✅ 从目标难度选择: {selected['id']}")
    else:
        # 2. 从所有未用题目中选择
        all_unused = [q for q in all_questions if q['id'] not in used_ids]
        if not all_unused:
            print("❌ 所有题目都已用完！")
            return None
        
        selected = random.choice(all_unused)
        print(f"🔄 随机选择: {selected['id']} (难度: {selected['difficulty']})")
    
    # 保存题目状态
    st.session_state.current_question = selected
    st.session_state.current_question_id = selected['id']
    
    return selected

# ========== 第4步：修复的第3题自适应逻辑 ==========
def get_next_difficulty(is_correct):
    """根据当前答题情况确定下一题难度"""
    
    current_q = st.session_state.question_number
    current_diff = st.session_state.current_difficulty
    
    print(f"📊 自适应计算: 第{current_q}题，当前难度{current_diff}，答对:{is_correct}")
    
    # 前两题固定中等
    if current_q <= 2:
        return 'medium'
    
    # ========== 修复：第3题根据前两题结果 ==========
    elif current_q == 3:
        if len(st.session_state.first_two_answers) == 2:
            correct_count = sum(st.session_state.first_two_answers)
            print(f"  前两题结果: {st.session_state.first_two_answers}，正确数: {correct_count}")
            
            if correct_count == 2:
                print(f"  → 两题全对，第3题为hard")
                return 'hard'
            elif correct_count == 1:
                print(f"  → 一对一错，第3题为medium")
                return 'medium'
            else:  # correct_count == 0
                print(f"  → 两题全错，第3题为easy")
                return 'easy'
        else:
            print(f"  ⚠️ 前两题结果不足，使用默认medium")
            return 'medium'
    
    # 第四题及以后
    difficulty_levels = ['easy', 'medium', 'hard']
    current_index = difficulty_levels.index(current_diff)
    
    if is_correct:
        next_index = min(current_index + 1, 2)  # 上升
    else:
        next_index = max(current_index - 1, 0)  # 下降
    
    next_diff = difficulty_levels[next_index]
    print(f"  下一题难度: {next_diff}")
    
    return next_diff

# ========== 第5步：报告生成函数 ==========
def calculate_score():
    """计算分数"""
    weights = {'easy': 1, 'medium': 2, 'hard': 3}
    user_answers = st.session_state.user_answers
    
    score = sum(weights[ans['difficulty']] for ans in user_answers if ans['is_correct'])
    max_score = sum(weights[ans['difficulty']] for ans in user_answers)
    percentage = (score / max_score * 100) if max_score > 0 else 0
    
    return score, max_score, percentage

def generate_test_report():
    """生成详细的测试报告"""
    score, max_score, percentage = calculate_score()
    correct_count = sum(1 for ans in st.session_state.user_answers if ans['is_correct'])
    total_questions = len(st.session_state.user_answers)
    
    report = f"""英语语法能力测试报告
{'=' * 50}

基本信息
--------
测试者: {st.session_state.user_name}
测试ID: {st.session_state.test_id}
测试时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
总题数: {total_questions}

测试结果
--------
总分: {score}/{max_score}
正确率: {percentage:.1f}%
答对题数: {correct_count}/{total_questions}

难度分析
--------
"""
    # 难度分布
    difficulty_stats = {'easy': 0, 'medium': 0, 'hard': 0}
    difficulty_correct = {'easy': 0, 'medium': 0, 'hard': 0}
    
    for ans in st.session_state.user_answers:
        difficulty_stats[ans['difficulty']] += 1
        if ans['is_correct']:
            difficulty_correct[ans['difficulty']] += 1
    
    for diff in ['easy', 'medium', 'hard']:
        count = difficulty_stats[diff]
        correct = difficulty_correct[diff]
        correct_rate = (correct / count * 100) if count > 0 else 0
        report += f"{diff}: {count}题，答对{correct}题 ({correct_rate:.1f}%)\n"
    
    # 详细答题记录
    report += f"\n详细答题记录\n{'-' * 30}\n"
    for i, ans in enumerate(st.session_state.user_answers, 1):
        status = "✓ 正确" if ans['is_correct'] else "✗ 错误"
        report += f"第{i:2d}题 [{ans['difficulty']}] {status}\n"
        report += f"    题目ID: {ans['question_id']}\n"
        report += f"    你的答案: {ans['user_answer']}\n"
        report += f"    正确答案: {ans['correct_answer']}\n\n"
    
    # 测试分析
    report += f"\n测试分析\n{'-' * 30}\n"
    if percentage >= 80:
        report += "表现优秀！您的英语语法掌握得很好。\n"
    elif percentage >= 60:
        report += "表现良好！部分知识点需要加强练习。\n"
    else:
        report += "需要更多练习，建议重点复习语法知识点。\n"
    
    # 难度变化趋势
    report += f"\n难度变化趋势: "
    difficulties = [ans['difficulty'][0].upper() for ans in st.session_state.user_answers]
    report += " → ".join(difficulties)
    
    return report

def save_test_result():
    """保存测试结果到CSV文件"""
    score, max_score, percentage = calculate_score()
    correct_count = sum(1 for ans in st.session_state.user_answers if ans['is_correct'])
    total_questions = len(st.session_state.user_answers)
    
    # 难度统计
    difficulty_counts = {
        'easy': len([ans for ans in st.session_state.user_answers if ans['difficulty'] == 'easy']),
        'medium': len([ans for ans in st.session_state.user_answers if ans['difficulty'] == 'medium']),
        'hard': len([ans for ans in st.session_state.user_answers if ans['difficulty'] == 'hard'])
    }
    
    result_data = {
        'test_id': st.session_state.test_id,
        'user_name': st.session_state.user_name,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'score': f"{score}/{max_score}",
        'percentage': f"{percentage:.1f}%",
        'correct_count': correct_count,
        'total_questions': total_questions,
        'easy_count': difficulty_counts['easy'],
        'medium_count': difficulty_counts['medium'],
        'hard_count': difficulty_counts['hard']
    }
    
    csv_file = 'test_results.csv'
    file_exists = os.path.exists(csv_file)
    
    df_result = pd.DataFrame([result_data])
    
    if file_exists:
        df_existing = pd.read_csv(csv_file)
        df_combined = pd.concat([df_existing, df_result], ignore_index=True)
        df_combined.to_csv(csv_file, index=False, encoding='utf-8-sig')
    else:
        df_result.to_csv(csv_file, index=False, encoding='utf-8-sig')
    
    return csv_file

def show_results_with_charts():
    """显示完整的结果页面"""
    st.markdown("## 测试结果")
    
    score, max_score, percentage = calculate_score()
    correct_count = sum(1 for ans in st.session_state.user_answers if ans['is_correct'])
    total_questions = len(st.session_state.user_answers)
    
    # 基本信息
    st.info(f"测试者: {st.session_state.user_name} | 测试ID: {st.session_state.test_id}")
    
    # 分数统计
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总分", f"{score}/{max_score}")
    with col2:
        st.metric("正确率", f"{percentage:.1f}%")
    with col3:
        st.metric("答对题数", f"{correct_count}/{total_questions}")
    
    # 难度变化趋势图
    st.subheader("难度变化趋势")
    difficulty_history = [ans['difficulty'] for ans in st.session_state.user_answers]
    difficulty_numeric = []
    for d in difficulty_history:
        if d == 'easy':
            difficulty_numeric.append(1)
        elif d == 'medium':
            difficulty_numeric.append(2)
        else:
            difficulty_numeric.append(3)
    
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(range(1, len(difficulty_numeric) + 1), difficulty_numeric, marker='o', linewidth=2, color='#1f77b4')
    ax.set_xlabel("id_number")
    ax.set_ylabel("difficulty")
    ax.set_yticks([1, 2, 3])
    ax.set_yticklabels(['easy', 'medium', 'hard'])
    ax.set_ylim(0.5, 3.5)
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)
    
    # 详细答题记录
    st.subheader("详细答题记录")
    results_data = []
    for i, ans in enumerate(st.session_state.user_answers, 1):
        results_data.append({
            "题号": i,
            "题目ID": ans['question_id'],
            "难度": ans['difficulty'],
            "是否正确": "正确" if ans['is_correct'] else "错误",
            "你的答案": ans['user_answer'][:30] + "..." if len(ans['user_answer']) > 30 else ans['user_answer'],
            "正确答案": ans['correct_answer'][:30] + "..." if len(ans['correct_answer']) > 30 else ans['correct_answer']
        })
    
    df_results = pd.DataFrame(results_data)
    st.dataframe(df_results, use_container_width=True)
    
    # 难度分布饼图
    st.subheader("难度分布")
    difficulty_counts = {
        'easy': len([ans for ans in st.session_state.user_answers if ans['difficulty'] == 'easy']),
        'medium': len([ans for ans in st.session_state.user_answers if ans['difficulty'] == 'medium']),
        'hard': len([ans for ans in st.session_state.user_answers if ans['difficulty'] == 'hard'])
    }
    
    col1, col2 = st.columns([1, 2])
    with col1:
        for diff, count in difficulty_counts.items():
            st.metric(diff, count)
    
    with col2:
        fig2, ax2 = plt.subplots()
        colors = ['#87CEEB', '#6495ED', '#4169E1']
        ax2.pie(list(difficulty_counts.values()), labels=list(difficulty_counts.keys()), 
                autopct='%1.1f%%', colors=colors)
        st.pyplot(fig2)
    
    # 保存测试历史
    st.session_state.test_history.append({
        "user_name": st.session_state.user_name,
        "test_id": st.session_state.test_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "score": f"{score}/{max_score}",
        "percentage": percentage,
        "total_questions": total_questions,
        "correct_count": correct_count
    })
    
    # 保存到CSV
    csv_file = save_test_result()
    
    # 下载报告
    st.markdown("---")
    st.subheader("下载测试报告")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 下载详细报告 (TXT)
        report_text = generate_test_report()
        st.download_button(
            label="下载详细报告 (TXT)",
            data=report_text,
            file_name=f"英语测试报告_{st.session_state.user_name}_{st.session_state.test_id}.txt",
            mime="text/plain",
            type="primary"
        )
    
    with col2:
        # 下载所有成绩汇总 (CSV)
        if os.path.exists(csv_file):
            with open(csv_file, 'rb') as f:
                csv_data = f.read()
            st.download_button(
                label="下载所有成绩汇总 (CSV)",
                data=csv_data,
                file_name="所有测试成绩汇总.csv",
                mime="text/csv",
                type="primary"
            )
    
    st.success(f"测试结果已保存到: {csv_file}")

# ========== 第6步：主程序 ==========
def main():
    st.title("英语语法能力测试")
    
    # 初始化状态
    init_session_state()
    
    # 加载题库
    question_bank = load_question_bank()
    if not question_bank:
        st.stop()
    
    # ===== 侧边栏 =====
    with st.sidebar:
        st.header("个人信息")
        
        if st.session_state.user_name:
            st.info(f"**姓名:** {st.session_state.user_name}")
            st.info(f"**测试ID:** {st.session_state.test_id}")
        
        st.header("系统设置")
        
        if not st.session_state.test_started:
            st.info("每次测试包含20道题目")
        elif st.session_state.test_started and not st.session_state.test_finished:
            progress = (st.session_state.question_number - 1) / 20
            st.progress(progress)
            st.write(f"**进度:** {st.session_state.question_number-1}/20")
        
        # 历史记录
        if st.session_state.test_history:
            st.header("历史记录")
            for i, history in enumerate(reversed(st.session_state.test_history[-3:]), 1):
                st.markdown(f"**测试{i}**")
                st.markdown(f"分数: {history['score']}")
                st.markdown(f"正确率: {history['percentage']:.1f}%")
                st.markdown("---")
    
    # ===== 主界面 =====
    
    # 1. 姓名输入
    if not st.session_state.user_name:
        st.markdown("### 欢迎参加英语语法能力测试")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            user_name = st.text_input("请输入您的姓名", placeholder="请输入姓名")
            
            if st.button("开始测试", type="primary"):
                if user_name.strip():
                    st.session_state.user_name = user_name.strip()
                    st.session_state.test_id = f"{user_name}_{datetime.now().strftime('%Y%m%d')}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:6]}"
                    st.session_state.test_started = True
                    st.session_state.test_finished = False
                    st.session_state.question_number = 1
                    st.session_state.current_difficulty = 'medium'
                    st.session_state.first_two_answers = []
                    st.session_state.user_answers = []
                    st.session_state.used_question_ids = set()
                    st.session_state.current_question = None
                    st.session_state.current_question_id = None
                    
                    print(f"\n🚀 测试开始: {user_name}")
                    st.rerun()
                else:
                    st.warning("请输入您的姓名")
        
        with col2:
            st.markdown("""
            **测试说明：**
            - 共20道选择题
            - 根据答题表现动态调整难度
            - 测试完成后可下载详细报告
            - 所有成绩将保存在本地CSV文件中
            
            **测试规则：**
            1. 前两题中等难度
            2. 第三题根据前两题结果决定
            3. 从第四题起答对升难度，答错降难度
            """)
    
    # 2. 测试结束
    elif st.session_state.test_finished:
        show_results_with_charts()
        
        if st.button("重新测试", type="primary"):
            # 生成新的测试ID
            new_test_id = f"{st.session_state.user_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            st.session_state.test_id = new_test_id
            
            # 重置测试状态
            st.session_state.test_started = True
            st.session_state.test_finished = False
            st.session_state.question_number = 1
            st.session_state.current_difficulty = 'medium'
            st.session_state.first_two_answers = []
            st.session_state.user_answers = []
            st.session_state.used_question_ids = set()
            st.session_state.current_question = None
            st.session_state.current_question_id = None
            
            st.rerun()
    
    # 3. 测试进行中
    elif st.session_state.test_started:
        current_q = st.session_state.question_number
        
        # 确定目标难度
        if current_q <= 2:
            target_difficulty = 'medium'
        else:
            target_difficulty = st.session_state.current_difficulty
        
        # 选择题目
        current_question = select_question(question_bank, target_difficulty)
        
        if not current_question:
            st.error("题目不足，测试结束")
            st.session_state.test_finished = True
            st.rerun()
        
        # 显示题目
        st.markdown(f"### 第 {current_q} 题 / 共 20 题")
        st.markdown(f"**{current_question['question']}**")
        
        # 使用表单防止意外刷新
        with st.form(key=f"question_form_{current_q}"):
            selected = st.radio(
                "请选择答案:",
                current_question['options'],
                key=f"options_{current_q}",
                index=None
            )
            
            submitted = st.form_submit_button("提交答案", type="primary")
            
            if submitted:
                if selected is None:
                    st.warning("请选择一个答案")
                else:
                    # 检查答案
                    is_correct = (selected == current_question['options'][current_question['correct']])
                    
                    print(f"\n📝 提交答案:")
                    print(f"  题目ID: {current_question['id']}")
                    print(f"  用户答案: {selected}")
                    print(f"  正确答案: {current_question['options'][current_question['correct']]}")
                    print(f"  是否正确: {is_correct}")
                    
                    # 记录答案
                    answer_record = {
                        'question_id': current_question['id'],
                        'user_answer': selected,
                        'correct_answer': current_question['options'][current_question['correct']],
                        'is_correct': is_correct,
                        'difficulty': current_question['difficulty']
                    }
                    
                    st.session_state.user_answers.append(answer_record)
                    
                    # 标记题目已用
                    st.session_state.used_question_ids.add(current_question['id'])
                    
                    # 记录前两题结果
                    if current_q <= 2:
                        st.session_state.first_two_answers.append(is_correct)
                    
                    # 计算下一题难度（修复了第3题逻辑）
                    st.session_state.current_difficulty = get_next_difficulty(is_correct)
                    
                    # 清理当前题目状态
                    st.session_state.current_question = None
                    st.session_state.current_question_id = None
                    
                    # 更新题号
                    st.session_state.question_number += 1
                    
                    # 检查是否完成
                    if st.session_state.question_number > 20:
                        st.session_state.test_finished = True
                    
                    # 显示反馈
                    if is_correct:
                        st.success("✅ 回答正确！")
                    else:
                        st.error(f"❌ 回答错误。正确答案是: {current_question['options'][current_question['correct']]}")
                    
                    # 短暂延迟后刷新
                    st.rerun()

if __name__ == "__main__":
    main()
