# app.py 教培学员数据分析交互式看板
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ====================== 全局配置 ======================
st.set_page_config(page_title="教培学员数据分析看板", layout="wide")
plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# ====================== 1. 数据加载与预处理（和原代码逻辑完全一致） ======================
@st.cache_data  # 缓存数据，提升加载速度
def get_data():
    # 读取Excel（和原代码同目录）
    df = pd.read_excel("学生基本信息.xlsx", sheet_name="全学员总表")

    # 缺失值填充
    fill_rules = {
        "cpa考级等级": "无",
        "电子学会考级结果": "无",
        "CCF-GESP考级结果": "无",
        "累计续费总金额": 0,
        "报名到首续费间隔天数": 0,
        "信息素养大赛": "未参赛",
        "人工智能挑战赛": "未参赛"
    }
    df = df.fillna(fill_rules)

    # 日期处理
    df["报名日期"] = pd.to_datetime(df["报名日期"])
    df["报名月份"] = df["报名日期"].dt.to_period("M")
    df["报名年份"] = df["报名日期"].dt.year

    # 衍生指标
    df["合计总收入"] = df["首次缴费"] + df["总续费金额"]
    df["学员生命周期价值(LTV)"] = df["合计总收入"]

    # 学员价值分层（沿用调试好的规则）
    def value_segmentation(row):
        if row["合计总收入"] >= 5000:
            return "高价值"
        elif row["合计总收入"] >= 3000:
            return "中价值"
        else:
            return "低价值"
    df["学员价值分层"] = df.apply(value_segmentation, axis=1)

    # 考级/参赛标记
    df["是否有考级"] = np.where(
        (df["cpa考级等级"] != "无") | (df["电子学会考级结果"] != "无") | (df["CCF-GESP考级结果"] != "无"),
        "是", "否"
    )
    df["是否有参赛"] = np.where(
        (df["信息素养大赛"] != "未参赛") | (df["人工智能挑战赛"] != "未参赛"),
        "是", "否"
    )
    return df

# 加载数据
df = get_data()

# ====================== 2. 页面标题 & 侧边栏筛选 ======================
st.title("📊 学员营收与留存数据分析看板")
st.sidebar.header("🔍 数据筛选")

# 课程筛选
course_list = df["课程科目"].unique()
select_course = st.sidebar.multiselect("选择课程", course_list, default=course_list)
df_filter = df[df["课程科目"].isin(select_course)]

# ====================== 3. 核心指标卡片 ======================
st.subheader("📈 核心经营指标")
total_stu = len(df_filter)
total_revenue = df_filter["合计总收入"].sum()
avg_ltv = round(df_filter["合计总收入"].mean(), 2)

col1, col2, col3 = st.columns(3)
col1.metric("总学员人数", total_stu)
col2.metric("总营收(元)", total_revenue)
col3.metric("平均学员LTV(元)", avg_ltv)

st.divider()

# ====================== 4. 课程维度分析 ======================
st.subheader("📚 各课程学员数 & 营收分布")
course_agg = df_filter.groupby("课程科目").agg(
    学员人数=("学员 ID", "count"),
    总营收=("合计总收入", "sum")
).reset_index()

st.bar_chart(course_agg, x="课程科目", y="学员人数", use_container_width=True)
st.bar_chart(course_agg, x="课程科目", y="总营收", use_container_width=True)

st.divider()

# ====================== 5. 学员价值分层饼图 ======================
st.subheader("🪙 学员价值分层营收占比")

# 1. 先按 Excel 规则重新生成分层（必须和 Excel 1:1 对应）
def value_segmentation(row):
    if row["合计总收入"] >= 5000:
        return "高价值"
    elif row["合计总收入"] >= 3000:
        return "中价值"
    else:
        return "低价值"

df_filter["学员价值分层"] = df_filter.apply(value_segmentation, axis=1)

# 2. 计算分层汇总
value_agg = df_filter.groupby("学员价值分层")["合计总收入"].sum().reset_index()

# 3. 绘制饼图（修正 autopct 的语法错误）
fig, ax = plt.subplots(figsize=(6, 6))
ax.pie(
    value_agg["合计总收入"], 
    labels=value_agg["学员价值分层"],
    autopct="%1.1f%%",  # 修正：去掉了多余的%符号
    startangle=90
)
ax.axis("equal")  # 确保饼图是圆形
st.pyplot(fig)

st.divider()

# ====================== 6. 考级/赛事对LTV影响 ======================
st.subheader("🏆 考级/赛事参与对学员LTV影响")
activity_agg = df_filter.groupby(["是否有考级", "是否有参赛"])["学员生命周期价值(LTV)"].mean().reset_index()
activity_agg["组合标签"] = activity_agg["是否有考级"] + " | " + activity_agg["是否有参赛"]

st.bar_chart(activity_agg, x="组合标签", y="学员生命周期价值(LTV)", use_container_width=True)

# ====================== 7. 原始数据查看 ======================
st.subheader("📄 原始学员数据")
st.dataframe(df_filter, use_container_width=True)