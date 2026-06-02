import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
from openai import OpenAI

# 页面配置
st.set_page_config(page_title="校园闲置物品智能交易助手", page_icon="📦", layout="wide")

# 初始化会话状态
if "selected_items" not in st.session_state:
    st.session_state.selected_items = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 加载数据
@st.cache_data
def load_data():
    """加载闲置物品数据"""
    data_path = os.path.join("data", "items.csv")
    df = pd.read_csv(data_path)
    df['post_date'] = pd.to_datetime(df['post_date'])
    df['month'] = df['post_date'].dt.month_name()
    return df

df = load_data()

# 连接AI客户端
def get_ai_client():
    api_key = st.session_state.get("api_key", "")
    base_url = st.session_state.get("base_url", "https://api.deepseek.com/v1")
    if api_key:
        return OpenAI(api_key=api_key, base_url=base_url)
    return None

# 闲置货源匹配提示词
MATCH_PROMPT = """
你是一个校园闲置物品智能匹配助手。
用户会提供他们的预算、年级和所需物品类型（如教材、电器等）。
请根据以下商品列表，为用户推荐最合适的3-5件商品。

商品列表：
{items_info}

用户需求：
{user_query}

请以友好、简洁的方式列出匹配的商品，包括：商品名称、类别、价格、成色、卖家年级。
"""

# 商品文案&估价提示词
DESC_PROMPT = """
你是一个校园闲置物品文案撰写和估价专家。
请根据以下商品信息：
- 商品名称：{item_name}
- 类别：{category}
- 成色：{condition}
- 当前价格：{price}元
- 描述：{description}

请完成以下任务：
1. 撰写一段吸引人的商品介绍文案（30-50字）
2. 给出一个合理的估价范围

输出格式：
【商品文案】：xxx
【估价范围】：xxx元 - xxx元
"""

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 配置")
    st.session_state.api_key = st.text_input("API Key", value="", type="password", help="你的大模型API密钥")
    st.session_state.base_url = st.text_input("Base URL", value="https://api.deepseek.com/v1", help="API端点地址")
    st.session_state.model = st.text_input("Model", value="deepseek-chat", help="模型名称")
    
    st.markdown("---")
    st.header("📊 数据筛选")
    selected_college = st.selectbox("选择学院", ["全部"] + sorted(df['college'].unique()))
    price_range = st.slider("价格范围", 0, 3000, (0, 3000))
    
    # 过滤数据
    filtered_df = df.copy()
    if selected_college != "全部":
        filtered_df = filtered_df[filtered_df['college'] == selected_college]
    filtered_df = filtered_df[(filtered_df['price'] >= price_range[0]) & (filtered_df['price'] <= price_range[1])]

# 主页面
st.title("📦 校园闲置物品智能交易助手")
st.subheader("让闲置物品找到新主人")

# 标签页
tab1, tab2 = st.tabs(["📊 数据看板", "🤖 AI智能助手"])

with tab1:
    # 统计卡片
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("商品总数", len(filtered_df))
    with col2:
        st.metric("总销售额", f"{(filtered_df['price'] * filtered_df['sales_count']).sum():.2f}元")
    with col3:
        st.metric("平均价格", f"{filtered_df['price'].mean():.2f}元")
    with col4:
        st.metric("热销商品数", len(filtered_df[filtered_df['sales_count'] > 10]))

    # 类别分布饼图
    st.subheader("📈 商品类别分布")
    category_counts = filtered_df['category'].value_counts()
    fig1, ax1 = plt.subplots()
    ax1.pie(category_counts, labels=category_counts.index, autopct='%1.1f%%', startangle=90)
    ax1.axis('equal')
    st.pyplot(fig1)

    # 价格区间柱状图
    st.subheader("💰 价格区间分布")
    bins = [0, 50, 100, 200, 500, 3000]
    labels = ['0-50', '50-100', '100-200', '200-500', '500+']
    filtered_df['price_range'] = pd.cut(filtered_df['price'], bins=bins, labels=labels)
    price_dist = filtered_df['price_range'].value_counts().sort_index()
    fig2, ax2 = plt.subplots()
    ax2.bar(price_dist.index, price_dist.values, color='skyblue')
    ax2.set_xlabel('价格区间(元)')
    ax2.set_ylabel('商品数量')
    st.pyplot(fig2)

    # 月度发布趋势
    st.subheader("📅 月度发布趋势")
    month_order = ['March']  # 数据中只有3月
    monthly_data = filtered_df['month'].value_counts().reindex(month_order, fill_value=0)
    fig3, ax3 = plt.subplots()
    ax3.plot(monthly_data.index, monthly_data.values, marker='o', color='green')
    ax3.set_xlabel('月份')
    ax3.set_ylabel('发布数量')
    st.pyplot(fig3)

    # 热门商品排行
    st.subheader("🔥 热门商品TOP10")
    top_sales = filtered_df.sort_values('sales_count', ascending=False).head(10)
    st.dataframe(top_sales[['name', 'category', 'price', 'sales_count', 'college']], hide_index=True)

with tab2:
    # AI对话区域
    st.subheader("🤖 智能客服")
    
    # 显示聊天历史
    for msg in st.session_state.chat_history:
        if msg['role'] == 'user':
            st.chat_message("user").write(msg['content'])
        else:
            st.chat_message("assistant").write(msg['content'])
    
    # 用户输入
    user_input = st.text_input("请输入您的需求（如：预算200元，大一，需要教材）", key="user_input")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        match_btn = st.button("🎯 货源匹配")
    with col2:
        desc_btn = st.button("✍️ 生成文案")
    with col3:
        reset_btn = st.button("🔄 清空对话")
    
    if reset_btn:
        st.session_state.chat_history = []
    
    if match_btn and user_input:
        # 准备商品信息
        items_info = "\n".join([f"- {row['name']} | {row['category']} | {row['price']}元 | {row['condition']} | {row['college']} | {row['seller_grade']}" 
                                for _, row in filtered_df.iterrows()])
        
        prompt = MATCH_PROMPT.format(items_info=items_info, user_query=user_input)
        
        client = get_ai_client()
        if client:
            with st.spinner("正在匹配货源..."):
                try:
                    response = client.chat.completions.create(
                        model=st.session_state.model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7
                    )
                    result = response.choices[0].message.content
                    st.session_state.chat_history.append({"role": "user", "content": user_input})
                    st.session_state.chat_history.append({"role": "assistant", "content": result})
                    st.rerun()
                except Exception as e:
                    st.error(f"AI调用失败: {str(e)}")
        else:
            st.warning("请先配置API Key")
    
    if desc_btn and user_input:
        # 选择一个商品生成文案
        item_names = filtered_df['name'].tolist()
        selected_item = st.selectbox("选择商品", item_names, key="item_select")
        
        item = filtered_df[filtered_df['name'] == selected_item].iloc[0]
        prompt = DESC_PROMPT.format(
            item_name=item['name'],
            category=item['category'],
            condition=item['condition'],
            price=item['price'],
            description=item['description']
        )
        
        client = get_ai_client()
        if client:
            with st.spinner("正在生成文案..."):
                try:
                    response = client.chat.completions.create(
                        model=st.session_state.model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7
                    )
                    result = response.choices[0].message.content
                    st.session_state.chat_history.append({"role": "user", "content": f"为「{selected_item}」生成文案"})
                    st.session_state.chat_history.append({"role": "assistant", "content": result})
                    st.rerun()
                except Exception as e:
                    st.error(f"AI调用失败: {str(e)}")
        else:
            st.warning("请先配置API Key")

# 页脚
st.markdown("---")
st.caption("💡 提示：在侧边栏配置API Key后即可使用AI功能")