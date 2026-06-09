import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
from openai import OpenAI
import uuid
import re
import json

# 页面配置
st.set_page_config(page_title="校园闲置物品智能交易助手", page_icon="📦", layout="wide")

# 自定义CSS样式
st.markdown("""
<style>
    /* 整体背景色 */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        min-height: 100vh;
    }
    
    /* 标题样式 */
    .stTitle {
        color: #2c3e50;
        font-weight: 700;
    }
    
    /* 标签页样式 */
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(255, 255, 255, 0.8);
        border-radius: 10px 10px 0 0;
        padding: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #3498db;
        font-weight: 500;
        background-color: transparent;
        border-radius: 8px;
        padding: 0.5rem 1rem;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(52, 152, 219, 0.1);
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #3498db;
        color: white;
    }
    
    /* 卡片样式 */
    .stMetric {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* 按钮样式 */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* 侧边栏样式 - 柔和浅蓝 */
    .css-1d391kg {
        background: #f0f6fc;
        border-radius: 0 12px 12px 0;
        box-shadow: 2px 0 10px rgba(0, 0, 0, 0.05);
    }
    
    /* 表单输入样式 */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        padding: 0.5rem;
    }
    
    /* 数据表格样式 */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# ==================== 初始化会话状态 + 预置模拟测试数据 ====================
if "selected_items" not in st.session_state:
    st.session_state.selected_items = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
# 管理页AI对话记录
if "manage_ai_chat" not in st.session_state:
    st.session_state.manage_ai_chat = []

# 预置【我发布的商品】模拟数据
if "published_goods" not in st.session_state:
    st.session_state.published_goods = [
        {
            "id": "test001",
            "name": "大学计算机基础教材",
            "category": "教材",
            "price": 45,
            "condition": "几乎全新",
            "college": "计算机学院",
            "grade": "大二",
            "contact": "微信: student01",
            "desc": "课本笔记完整，无破损，适合计算机专业同学使用",
            "status": "上架中"
        },
        {
            "id": "test002",
            "name": "蓝牙耳机",
            "category": "数码",
            "price": 129,
            "condition": "轻微使用痕迹",
            "college": "文学院",
            "grade": "大一",
            "contact": "QQ: 123456",
            "desc": "续航正常，音质良好，配件齐全",
            "status": "上架中"
        },
        {
            "id": "test003",
            "name": "实木书桌",
            "category": "家具",
            "price": 380,
            "condition": "明显使用痕迹",
            "college": "理学院",
            "grade": "大三",
            "contact": "微信: desk888",
            "desc": "宿舍自用书桌，结实耐用，自提",
            "status": "已下架"
        }
    ]

# 预置【交易记录/已购商品】模拟数据
if "trade_records" not in st.session_state:
    st.session_state.trade_records = [
        {
            "trade_id": "TRADE001",
            "goods_name": "高等数学上册",
            "category": "教材",
            "price": 32,
            "seller_grade": "大四",
            "contact": "微信: math99",
            "trade_time": "2026-06-08 14:20:15"
        },
        {
            "trade_id": "TRADE002",
            "goods_name": "运动篮球",
            "category": "运动",
            "price": 85,
            "seller_grade": "大二",
            "contact": "QQ: 654321",
            "trade_time": "2026-06-09 09:10:22"
        }
    ]

if "show_settings" not in st.session_state:
    st.session_state.show_settings = False
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# ==================== 加载数据 ====================
@st.cache_data
def load_data():
    """加载闲置物品数据"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, "data", "items.csv")
    df = pd.read_csv(data_path)
    df['post_date'] = pd.to_datetime(df['post_date'])
    df['month'] = df['post_date'].dt.month_name()
    return df

df = load_data()

# ==================== AI客户端 ====================
def get_ai_client():
    api_key = st.session_state.get("api_key", "")
    base_url = st.session_state.get("base_url", "https://api.deepseek.com/v1")
    if api_key:
        return OpenAI(api_key=api_key, base_url=base_url)
    return None

# 各类AI提示词
# 1. 通用货源匹配
MATCH_PROMPT = """
你是一个校园闲置物品智能匹配助手。
用户会提供他们的预算、年级、专业和所需物品类型（如教材、电器等）。
请根据以下商品列表，为用户推荐最合适的3-5件商品。

商品列表：
{items_info}

用户需求：
{user_query}

请以友好、简洁的方式列出匹配的商品，包括：商品名称、类别、价格、成色、卖家年级。
"""

# 2. 教材专项查询
BOOK_PROMPT = """
你是校园教材查询助手。
用户提供了【专业】和【年级】，请从下方商品列表中，精准筛选出对应专业、对应年级的所有教材类商品。
列出：商品名称、价格、成色、卖家信息。

商品列表：
{items_info}
用户专业&年级：{user_info}
"""

# 3. 商品文案&估价
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

# 4. 卖家描述润色
POLISH_PROMPT = """
你是校园闲置商品文案优化师，帮卖家润色商品描述。
原描述：{raw_text}
商品信息：名称-{name}，类别-{cate}，成色-{cond}

要求：语言通顺优美、突出商品亮点、字数适中，适合校园二手交易场景。
直接输出润色后的内容即可。
"""

# 5. 管理页问题解答
MANAGE_HELP_PROMPT = """
你是本校园闲置交易平台的智能客服，专门解答用户在【我的管理】板块遇到的问题，
包括商品发布、价格修改、商品下架、交易订单、购买流程、功能使用等相关问题。
语言通俗易懂，简洁实用。
用户问题：{question}
"""

# 6. AI智能筛选解析
FILTER_AI_PROMPT = """
你是筛选指令解析助手，从用户自然语言中提取：学院、最低价格、最高价格、物品品类。
可选学院：{college_list}
可选品类：{cate_list}
价格范围0-2000元。

用户输入：{user_text}
严格按照以下JSON格式输出，无匹配则填空字符串：
{{"college":"","min_price":"","max_price":"","category":""}}
"""

# 管理员密码
ADMIN_PASSWORD = "qimodazuoye123"

# 右上角设置按钮
col1, col2 = st.columns([1, 0.1])
with col2:
    if st.button("⚙️", key="settings_btn", help="设置"):
        st.session_state.show_settings = not st.session_state.show_settings

# 设置弹窗
if st.session_state.show_settings:
    with st.expander("⚙️ 系统设置", expanded=True):
        st.subheader("🔐 管理员登录")
        admin_pwd = st.text_input("管理员密码", type="password", help="输入密码以访问数据分析和API配置")
        if st.button("登录"):
            if admin_pwd == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.success("管理员登录成功！")
            else:
                st.error("密码错误")
        if st.session_state.is_admin:
            st.info("当前为管理员模式")
            st.markdown("---")
            st.subheader("🤖 API配置")
            st.session_state.api_key = st.text_input("API Key", value=st.session_state.get("api_key", ""), type="password")
            st.session_state.base_url = st.text_input("Base URL", value=st.session_state.get("base_url", "https://api.deepseek.com/v1"))
            st.session_state.model = st.text_input("Model", value=st.session_state.get("model", "deepseek-chat"))

# ==================== 侧边栏（价格优化 + AI智能筛选 + 表情品类） ====================
with st.sidebar:
    st.header("📊 数据筛选")
    selected_college = st.selectbox("选择学院", ["全部"] + sorted(df['college'].unique()))

    # 价格区域：上限2000 + 手动输入
    st.subheader("💰 价格范围")
    price_slider = st.slider("滑动选择价格", 0, 2000, (0, 2000))
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        min_price_input = st.number_input("最低价格", min_value=0, max_value=2000, value=price_slider[0])
    with col_p2:
        max_price_input = st.number_input("最高价格", min_value=0, max_value=2000, value=price_slider[1])

    final_min_price = min_price_input
    final_max_price = max_price_input

    # 品类（带表情）
    st.subheader("📦 物品品类")
    category_options = [
        "全部 📋",
        "教材 📚",
        "电器 🔌",
        "数码 📱",
        "家具 🪑",
        "服装 👕",
        "运动 🏃",
        "美妆 💄",
        "其他 📦",
        "数码配件 🎧",
        "日用品 🧴",
        "运动器材 ⚽",
        "乐器 🎸",
        "鞋靴 👟",
        "箱包 🎒"
    ]
    selected_category = st.selectbox("筛选品类", category_options)
    clean_category = selected_category.split(" ")[0]

    # ========== 新增：AI智能语义筛选 ==========
    st.markdown("---")
    st.subheader("🤖 AI智能筛选")
    ai_filter_text = st.text_input("输入需求(例：计算机学院 100元以内 教材)")
    if st.button("🔍 智能匹配筛选") and ai_filter_text.strip():
        client = get_ai_client()
        if client:
            college_list = ",".join(sorted(df['college'].unique()))
            cate_list = "教材,电器,数码,家具,服装,运动,美妆,其他,数码配件,日用品,运动器材,乐器,鞋靴,箱包"
            prompt = FILTER_AI_PROMPT.format(
                college_list=college_list,
                cate_list=cate_list,
                user_text=ai_filter_text
            )
            try:
                res = client.chat.completions.create(
                    model=st.session_state.model,
                    messages=[{"role":"user","content":prompt}],
                    temperature=0
                )
                res_json = json.loads(res.choices[0].message.content)
                # 赋值到筛选组件
                if res_json["college"]:
                    selected_college = res_json["college"]
                if res_json["min_price"] and res_json["min_price"].isdigit():
                    final_min_price = int(res_json["min_price"])
                if res_json["max_price"] and res_json["max_price"].isdigit():
                    final_max_price = int(res_json["max_price"])
                if res_json["category"]:
                    for item in category_options:
                        if item.startswith(res_json["category"]):
                            selected_category = item
                            break
                st.success("AI筛选规则已生效！")
            except Exception as e:
                st.error(f"解析失败：{str(e)}")
        else:
            st.warning("请先配置API Key")

    # 全局数据过滤
    filtered_df = df.copy()
    if selected_college != "全部":
        filtered_df = filtered_df[filtered_df['college'] == selected_college]
    filtered_df = filtered_df[(filtered_df['price'] >= final_min_price) & (filtered_df['price'] <= final_max_price)]
    if clean_category != "全部":
        filtered_df = filtered_df[filtered_df['category'] == clean_category]

# ==================== 主页面 ====================
st.title("📦 校园闲置物品智能交易助手")
st.subheader("让闲置物品找到新主人")

tabs_list = ["🤖 AI智能助手", "💰 发布商品", "📋 我的管理"]
if st.session_state.is_admin:
    tabs_list.append("📊 数据看板")

tab_objects = st.tabs(tabs_list)
tab_ai = tab_objects[0]
tab_sell = tab_objects[1]
tab_my = tab_objects[2]
tab_data = tab_objects[3] if st.session_state.is_admin else None

# 管理员-数据看板
if st.session_state.is_admin and tab_data:
    with tab_data:
        st.markdown("### 📊 数据概览")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📦 商品总数", len(filtered_df))
        with col2:
            st.metric("💰 总销售额", f"{(filtered_df['price'] * filtered_df['sales_count']).sum():.2f}元")
        with col3:
            st.metric("📈 平均价格", f"{filtered_df['price'].mean():.2f}元")
        with col4:
            st.metric("🔥 热销商品数", len(filtered_df[filtered_df['sales_count'] > 10]))

        morandi_colors = ['#28A745', '#17A2B8', '#FFC107', '#FD7E14', '#DC3545', '#B5A0A9', '#A0A9B5', '#A9B5A0', '#B5A0A0', '#A0B5B5']
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 📈 商品类别分布")
            category_counts = filtered_df['category'].value_counts()
            fig1, ax1 = plt.subplots(figsize=(6, 5))
            wedges, texts, autotexts = ax1.pie(category_counts, labels=category_counts.index, autopct='%1.1f%%',
                                               startangle=90, colors=morandi_colors[:len(category_counts)],
                                               wedgeprops={'edgecolor': 'white', 'linewidth': 2},
                                               textprops={'fontsize': 10, 'family': 'SimHei'})
            ax1.axis('equal')
            st.pyplot(fig1)
        with col2:
            st.markdown("### 💰 价格区间分布")
            bins = [0, 50, 100, 200, 500, 2000]
            labels = ['0-50', '50-100', '100-200', '200-500', '500+']
            filtered_df['price_range'] = pd.cut(filtered_df['price'], bins=bins, labels=labels)
            price_dist = filtered_df['price_range'].value_counts().sort_index()
            fig2, ax2 = plt.subplots(figsize=(6, 5))
            bars = ax2.bar(price_dist.index, price_dist.values, color=morandi_colors[:5])
            ax2.set_xlabel('价格区间(元)', fontsize=11, family='SimHei')
            ax2.set_ylabel('商品数量', fontsize=11, family='SimHei')
            ax2.grid(axis='y', alpha=0.3)
            for bar in bars:
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width() / 2., height, f'{int(height)}',
                         ha='center', va='bottom', fontsize=10)
            st.pyplot(fig2)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 📅 月度发布趋势")
            month_order = ['March', 'April']
            monthly_data = filtered_df['month'].value_counts().reindex(month_order, fill_value=0)
            fig3, ax3 = plt.subplots(figsize=(6, 5))
            ax3.plot(monthly_data.index, monthly_data.values, marker='o', color='#EF232A', linewidth=3, markersize=8)
            ax3.fill_between(monthly_data.index, monthly_data.values, alpha=0.3, color='#FFB6C1')
            ax3.set_xlabel('月份', fontsize=11, family='SimHei')
            ax3.set_ylabel('发布数量', fontsize=11, family='SimHei')
            ax3.grid(axis='y', alpha=0.3)
            st.pyplot(fig3)
        with col2:
            st.markdown("### 🔥 热门商品TOP10")
            top_sales = filtered_df.sort_values('sales_count', ascending=False).head(10)
            st.dataframe(top_sales[['name', 'category', 'price', 'sales_count', 'college']],
                         hide_index=True, use_container_width=True)

# ==================== AI智能助手（原有功能保留） ====================
with tab_ai:
    st.subheader("🤖 智能客服 & 教材查询")
    st.info("💡 输入「专业+年级」查询教材；输入需求自动匹配商品")

    for msg in st.session_state.chat_history:
        if msg['role'] == 'user':
            st.chat_message("user").write(msg['content'])
        else:
            st.chat_message("assistant").write(msg['content'])

    user_input = st.text_input("请输入需求（例：计算机专业 大二 / 预算150元 大一教材）", key="user_input")
    col1, col2, col3 = st.columns(3)
    with col1:
        match_btn = st.button("🎯 货源匹配")
    with col2:
        book_btn = st.button("📚 查询教材")
    with col3:
        reset_btn = st.button("🔄 清空对话")

    if reset_btn:
        st.session_state.chat_history = []

    # 通用匹配
    if match_btn and user_input:
        matched_items = filtered_df.copy()
        price_match = re.search(r'预算(\d+)元|价格(\d+)元|(\d+)元', user_input)
        if price_match:
            target_price = int(price_match.group(1) or price_match.group(2) or price_match.group(3))
            matched_items = matched_items[(matched_items['price'] >= target_price - 100) & (matched_items['price'] <= target_price + 100)]
        category_keywords = ['教材', '电器', '数码', '家具', '服装', '运动', '美妆', '食品', '书籍']
        matched_categories = [k for k in category_keywords if k in user_input]
        if matched_categories:
            matched_items = matched_items[matched_items['category'].str.contains('|'.join(matched_categories))]

        if len(matched_items) == 0:
            result = "😔 没有找到匹配的商品，请调整筛选条件或关键词！"
        else:
            items_info = "\n".join([
                f"- {row['name']} | {row['category']} | {row['price']}元 | {row['condition']} | {row['seller_grade']} | 联系方式:{row['contact']}"
                for _, row in matched_items.iterrows()])
            prompt = MATCH_PROMPT.format(items_info=items_info, user_query=user_input)
            client = get_ai_client()
            if client:
                with st.spinner("智能匹配中..."):
                    try:
                        res = client.chat.completions.create(model=st.session_state.model,
                                                            messages=[{"role": "user", "content": prompt}], temperature=0.7)
                        result = res.choices[0].message.content
                    except:
                        result = f"AI调用失败，以下是筛选结果：\n{items_info}"
            else:
                result = f"请先配置API Key，以下是筛选结果：\n{items_info}"

        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.session_state.chat_history.append({"role": "assistant", "content": result})
        st.rerun()

    # 教材查询
    if book_btn and user_input:
        book_df = filtered_df[filtered_df["category"] == "教材"]
        if len(book_df) == 0:
            res_text = "当前筛选条件下暂无教材类商品！"
        else:
            items_info = "\n".join([
                f"- {row['name']} | {row['price']}元 | {row['condition']} | {row['seller_grade']}"
                for _, row in book_df.iterrows()])
            prompt = BOOK_PROMPT.format(items_info=items_info, user_info=user_input)
            client = get_ai_client()
            if client:
                with st.spinner("查询教材中..."):
                    try:
                        res = client.chat.completions.create(model=st.session_state.model,
                                                            messages=[{"role": "user", "content": prompt}], temperature=0.7)
                        res_text = res.choices[0].message.content
                    except:
                        res_text = f"AI调用失败，当前教材列表：\n{items_info}"
            else:
                res_text = f"当前筛选条件下教材列表：\n{items_info}"

        st.session_state.chat_history.append({"role": "user", "content": f"查询教材：{user_input}"})
        st.session_state.chat_history.append({"role": "assistant", "content": res_text})
        st.rerun()

    # 文案生成
    if user_input and not match_btn and not book_btn:
        item_names = filtered_df['name'].tolist()
        if item_names:
            selected_item = st.selectbox("选择商品生成文案", item_names, key="item_select")
            item = filtered_df[filtered_df['name'] == selected_item].iloc[0]
            if st.button("✍️ 生成商品文案"):
                prompt = DESC_PROMPT.format(item_name=item['name'], category=item['category'],
                                           condition=item['condition'], price=item['price'],
                                           description=item['description'])
                client = get_ai_client()
                if client:
                    with st.spinner("生成文案中..."):
                        try:
                            res = client.chat.completions.create(model=st.session_state.model,
                                                                messages=[{"role": "user", "content": prompt}], temperature=0.7)
                            result = res.choices[0].message.content
                            st.session_state.chat_history.append({"role": "user", "content": f"为【{selected_item}】生成文案"})
                            st.session_state.chat_history.append({"role": "assistant", "content": result})
                            st.rerun()
                        except Exception as e:
                            st.error(f"AI调用失败：{str(e)}")
                else:
                    st.warning("请先配置API Key")

# ==================== 发布商品（修复：AI描述润色移到表单外） ====================
with tab_sell:
    st.subheader("💰 发布闲置商品")
    st.markdown("填写以下信息发布您的闲置物品，支持AI一键润色商品描述")

    # 先定义变量，方便AI润色读取
    if "polished_desc" not in st.session_state:
        st.session_state.polished_desc = ""

    with st.form("sell_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            item_name = st.text_input("商品名称", placeholder="例如：iPhone 13")
            category = st.selectbox("商品类别", [i.split(" ")[0] for i in category_options[1:]])
            price = st.number_input("价格（元）", min_value=0, step=1)
            condition = st.selectbox("商品成色", ["全新", "几乎全新", "轻微使用痕迹", "明显使用痕迹"])
        with col2:
            college = st.selectbox("学院", sorted(df['college'].unique()))
            seller_grade = st.selectbox("卖家年级", ["大一", "大二", "大三", "大四", "研究生"])
            contact = st.text_input("联系方式", placeholder="QQ/微信")
            # 描述文本框，绑定session_state中的润色结果
            description = st.text_area("商品描述", height=100, 
                                       value=st.session_state.polished_desc,
                                       placeholder="简单描述商品情况，可使用下方AI润色")

        submit_btn = st.form_submit_button("发布商品")
        if submit_btn:
            if item_name and price > 0 and contact:
                goods_id = str(uuid.uuid4())[:8]
                new_good = {
                    "id": goods_id,
                    "name": item_name,
                    "category": category,
                    "price": price,
                    "condition": condition,
                    "college": college,
                    "grade": seller_grade,
                    "contact": contact,
                    "desc": description,
                    "status": "上架中"
                }
                st.session_state.published_goods.append(new_good)
                st.success(f"✅ 发布成功！商品ID：{goods_id}")
            else:
                st.error("请填写完整信息（名称、价格、联系方式为必填）")

    # ========== 修复：AI润色按钮放在表单外面 ==========
    st.markdown("---")
    st.subheader("✨ AI商品描述润色")
    raw_desc_input = st.text_input("原始描述（复制上面的描述或直接输入）", value=description)
    if st.button("✨ AI润色描述"):
        client = get_ai_client()
        if client and raw_desc_input.strip() and item_name:
            with st.spinner("润色中..."):
                prompt = POLISH_PROMPT.format(
                    raw_text=raw_desc_input,
                    name=item_name,
                    cate=category,
                    cond=condition
                )
                try:
                    res = client.chat.completions.create(
                        model=st.session_state.model,
                        messages=[{"role":"user","content":prompt}],
                        temperature=0.7
                    )
                    polished_text = res.choices[0].message.content
                    st.session_state.polished_desc = polished_text
                    st.success("润色完成！已自动同步到上方描述框：")
                    st.text_area("润色后内容", value=polished_text, height=80)
                    st.rerun()  # 刷新表单，同步内容
                except Exception as e:
                    st.error(f"AI调用失败：{str(e)}")
        elif not client:
            st.warning("请先配置API Key")
        else:
            st.warning("请先填写商品名称和原始描述")

# ==================== 我的管理（新增：AI问题咨询） ====================
with tab_my:
    st.subheader("📋 我的管理中心")
    main_tab, ai_tab = st.tabs(["📦 商品&交易管理", "🤖 管理问题AI咨询"])

    # 原有商品+交易管理
    with main_tab:
        sub1, sub2 = st.tabs(["📤 我发布的商品", "🛒 我的交易&已购商品"])
        # 我发布的商品
        with sub1:
            st.markdown("### 已发布商品（支持改价 / 下架）")
            my_goods = st.session_state.published_goods
            if clean_category != "全部":
                my_goods = [g for g in my_goods if g["category"] == clean_category]

            if not my_goods:
                st.info("暂无您发布的商品")
            else:
                for idx, goods in enumerate(my_goods):
                    with st.expander(f"【{goods['status']}】{goods['name']}"):
                        col1, col2, col3 = st.columns([2, 1, 1])
                        with col1:
                            st.write(f"品类：{goods['category']}")
                            st.write(f"售价：¥{goods['price']}")
                            st.write(f"成色：{goods['condition']}")
                            st.write(f"描述：{goods['desc']}")
                        with col2:
                            new_price = st.number_input("修改价格", min_value=1, value=int(goods["price"]), key=f"p_{idx}")
                            if st.button("✅ 确认改价", key=f"up_{idx}"):
                                my_goods[idx]["price"] = new_price
                                st.success("价格更新成功！")
                                st.rerun()
                        with col3:
                            if goods["status"] == "上架中":
                                if st.button("🟥 下架商品", key=f"off_{idx}"):
                                    my_goods[idx]["status"] = "已下架"
                                    st.warning("商品已下架")
                                    st.rerun()
                            else:
                                st.info("该商品已下架")
        # 交易记录
        with sub2:
            st.markdown("### 交易记录 & 已购买商品")
            st.info("💡 模拟交易：选择商品可加入购买清单，生成交易明细")
            buy_list = filtered_df.head(5)
            if len(buy_list) > 0:
                buy_item_name = st.selectbox("选择商品模拟购买", buy_list["name"].tolist())
                buy_item = buy_list[buy_list["name"] == buy_item_name].iloc[0]
                if st.button("🛒 确认购买"):
                    trade_id = str(uuid.uuid4())[:8]
                    trade_info = {
                        "trade_id": trade_id,
                        "goods_name": buy_item["name"],
                        "category": buy_item["category"],
                        "price": buy_item["price"],
                        "seller_grade": buy_item["seller_grade"],
                        "contact": buy_item["contact"],
                        "trade_time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    st.session_state.trade_records.append(trade_info)
                    st.success(f"交易成功！交易单号：{trade_id}")
                    st.rerun()
            st.markdown("---")
            st.subheader("📄 交易明细列表")
            if not st.session_state.trade_records:
                st.info("暂无交易记录")
            else:
                trade_df = pd.DataFrame(st.session_state.trade_records)
                st.dataframe(trade_df, use_container_width=True, hide_index=True)

    # ========== 新增：管理问题AI咨询专区 ==========
    with ai_tab:
        st.markdown("### 💬 功能问题咨询")
        st.info("针对商品发布、改价、下架、交易、筛选等问题，向AI提问")
        # 历史对话
        for msg in st.session_state.manage_ai_chat:
            if msg["role"] == "user":
                st.chat_message("user").write(msg["content"])
            else:
                st.chat_message("assistant").write(msg["content"])

        manage_question = st.text_input("输入你的问题（例：怎么下架商品？/ 交易记录怎么查看？）", key="manage_q")
        col_q1, col_q2 = st.columns([1,1])
        with col_q1:
            send_q = st.button("📤 提问")
        with col_q2:
            clear_q = st.button("🗑️ 清空对话")

        if clear_q:
            st.session_state.manage_ai_chat = []
            st.rerun()

        if send_q and manage_question.strip():
            client = get_ai_client()
            if client:
                prompt = MANAGE_HELP_PROMPT.format(question=manage_question)
                with st.spinner("AI解答中..."):
                    try:
                        res = client.chat.completions.create(
                            model=st.session_state.model,
                            messages=[{"role":"user","content":prompt}],
                            temperature=0.7
                        )
                        ans = res.choices[0].message.content
                        st.session_state.manage_ai_chat.append({"role":"user","content":manage_question})
                        st.session_state.manage_ai_chat.append({"role":"assistant","content":ans})
                        st.rerun()
                    except:
                        st.error("AI调用失败，请检查API配置")
            else:
                st.warning("请先在右上角⚙️配置API Key")

st.markdown("---")
st.caption("💡 提示：点击右上角 ⚙️ 配置API Key后可使用全部AI拓展功能")