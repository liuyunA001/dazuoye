import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
from openai import OpenAI

# -------------------- 字体配置（解决中文显示方块问题） --------------------
def setup_chinese_font():
    """设置 matplotlib 中文字体，避免方框乱码"""
    font_candidates = [
        'Microsoft YaHei', 'SimHei', 'WenQuanYi Micro Hei',
        'Noto Sans CJK SC', 'PingFang SC', 'Heiti SC', 'sans-serif'
    ]
    for font_name in font_candidates:
        try:
            plt.rcParams['font.sans-serif'] = [font_name]
            plt.rcParams['axes.unicode_minus'] = False
            fig, ax = plt.subplots(figsize=(0.1, 0.1))
            ax.set_title('测试', fontsize=1)
            plt.close(fig)
            return True
        except:
            continue
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    return False

setup_chinese_font()

# -------------------- 页面配置 --------------------
st.set_page_config(page_title="校园闲置物品智能交易助手", page_icon="📦", layout="wide")

# -------------------- 自定义 CSS（校园治愈风格） --------------------
st.markdown("""
<style>
    .stApp {
        background-color: #faf8f5;
    }
    .main {
        background: linear-gradient(135deg, #faf8f5 0%, #f2f0eb 100%);
    }
    section[data-testid="stSidebar"] {
        background: rgba(200, 230, 201, 0.35);
        backdrop-filter: blur(12px);
        border-right: 1px solid rgba(255,255,255,0.5);
    }
    h1, h2, h3, h4, h5, h6 {
        color: #4a6b4a;
        font-family: 'Segoe UI', 'Roboto', sans-serif;
    }
    div.stMetric, div.stDataFrame, div[data-testid="stExpander"], div.stButton > button,
    .stTextInput input, .stSelectbox select, .stNumberInput input, .stTextArea textarea {
        border-radius: 20px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06) !important;
        transition: all 0.3s ease;
    }
    .stTextInput input:hover, .stSelectbox select:hover, .stNumberInput input:hover,
    .stTextArea textarea:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.1) !important;
        border-color: #f3b391 !important;
    }
    .stButton > button {
        background: linear-gradient(135deg, #fdd9b5 0%, #f9b482 100%) !important;
        color: #5a4a3a !important;
        font-weight: 600;
        border: none !important;
        padding: 0.6rem 2rem;
    }
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(249, 180, 130, 0.4) !important;
        background: linear-gradient(135deg, #f9b482 0%, #f58b5a 100%) !important;
    }
    .stDownloadButton > button, .st-key-settings_btn button {
        background: linear-gradient(135deg, #c8e6c9 0%, #a5d6a7 100%) !important;
        color: #4a6b4a !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #c8e6c9 !important;
        color: #4a6b4a !important;
    }
    .stDataFrame table {
        border-radius: 20px;
    }
    .glass-card {
        background: rgba(255,255,255,0.5);
        backdrop-filter: blur(8px);
        border-radius: 24px;
        padding: 1.2rem;
        margin: 0.8rem 0;
        box-shadow: 0 4px 16px rgba(0,0,0,0.05);
        border: 1px solid rgba(255,255,255,0.8);
    }
    .category-tag {
        display: inline-block;
        padding: 4px 16px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: 500;
        margin: 3px 6px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        transition: all 0.2s;
        cursor: pointer;
    }
    .category-tag:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    }
    .corner-decor {
        position: fixed;
        font-size: 60px;
        opacity: 0.15;
        z-index: 0;
        pointer-events: none;
        filter: grayscale(0.3);
    }
    .decor-bike { top: 20px; right: 30px; }
    .decor-book { bottom: 20px; left: 30px; }
    .decor-dorm { top: 50%; left: 10px; font-size: 70px; }
    .decor-cup { bottom: 80px; right: 20px; font-size: 50px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="corner-decor decor-bike">🚲</div>', unsafe_allow_html=True)
st.markdown('<div class="corner-decor decor-book">📚</div>', unsafe_allow_html=True)
st.markdown('<div class="corner-decor decor-dorm">🏠</div>', unsafe_allow_html=True)
st.markdown('<div class="corner-decor decor-cup">🥤</div>', unsafe_allow_html=True)

# -------------------- 初始化会话状态 --------------------
if "selected_items" not in st.session_state:
    st.session_state.selected_items = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "show_quick_sell" not in st.session_state:
    st.session_state.show_quick_sell = False
if "quick_filter_category" not in st.session_state:
    st.session_state.quick_filter_category = None

# -------------------- 数据加载 --------------------
@st.cache_data
def load_data():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, "data", "items.csv")
    df = pd.read_csv(data_path)
    df['post_date'] = pd.to_datetime(df['post_date'])
    df['month'] = df['post_date'].dt.month_name()
    return df

df = load_data()

# -------------------- AI 客户端 --------------------
def get_ai_client():
    api_key = st.session_state.get("api_key", "")
    base_url = st.session_state.get("base_url", "https://api.deepseek.com/v1")
    if api_key:
        return OpenAI(api_key=api_key, base_url=base_url)
    return None

# -------------------- 提示词 --------------------
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

# -------------------- 管理员设置 --------------------
if "show_settings" not in st.session_state:
    st.session_state.show_settings = False
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

ADMIN_PASSWORD = "qimodazuoye123"

col1, col2 = st.columns([1, 0.1])
with col2:
    if st.button("⚙️", key="settings_btn", help="设置"):
        st.session_state.show_settings = not st.session_state.show_settings

if st.session_state.show_settings:
    with st.expander("⚙️ 系统设置", expanded=True):
        st.subheader("🔐 管理员登录")
        admin_pwd = st.text_input("管理员密码", type="password")
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

# -------------------- 侧边栏 --------------------
with st.sidebar:
    st.markdown("""
    <div class="glass-card">
        <div style="text-align: center;">
            <span style="font-size: 48px;">🧑‍🎓</span>
            <h4 style="margin: 0.5rem 0 0.2rem; color: #4a6b4a;">校园小闲</h4>
            <p style="color: #888; font-size: 14px;">游客模式 · 未登录</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🪄 快速发布闲置")
    if st.button("打开快速发布", key="toggle_quick_sell"):
        st.session_state.show_quick_sell = not st.session_state.show_quick_sell
    
    if st.session_state.show_quick_sell:
        with st.form("quick_sell_form"):
            q_name = st.text_input("物品名称", placeholder="例：高等数学教材")
            q_cat = st.selectbox("类别", ["教材", "电器", "数码", "家具", "服装", "运动", "美妆", "其他"])
            q_price = st.number_input("价格", min_value=0, step=1)
            q_contact = st.text_input("联系方式", placeholder="QQ/微信")
            if st.form_submit_button("🚀 立即发布"):
                if q_name and q_price > 0 and q_contact:
                    new_item = pd.DataFrame({
                        'id': [len(df) + 1],
                        'name': [q_name],
                        'category': [q_cat],
                        'price': [q_price],
                        'condition': ["几乎全新"],
                        'college': ["未知"],
                        'seller_grade': ["未知"],
                        'sales_count': [0],
                        'post_date': [pd.Timestamp.now()],
                        'description': [""],
                        'contact': [q_contact]
                    })
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    data_path = os.path.join(script_dir, "data", "items.csv")
                    new_item.to_csv(data_path, mode='a', header=False, index=False)
                    st.success("🎉 发布成功！")
                    st.session_state.show_quick_sell = False
                    st.rerun()
                else:
                    st.error("请填写名称、价格和联系方式")
    
    st.markdown("---")
    st.header("📊 数据筛选")
    
    selected_college = st.selectbox("选择学院", ["全部"] + sorted(df['college'].unique()))
    price_range = st.slider("价格范围", 0, 3000, (0, 3000))
    
    st.caption("🎨 分类快捷筛选")
    categories = ["全部", "教材", "电器", "数码", "家具", "服装", "运动", "美妆", "食品", "书籍"]
    color_map = {
        "教材": "#E8F5E9", "电器": "#FFF3E0", "数码": "#E3F2FD", "家具": "#F3E5F5",
        "服装": "#FCE4EC", "运动": "#E0F7FA", "美妆": "#F1F8E9", "食品": "#FFF9C4", "书籍": "#EDE7F6"
    }
    cols = st.columns(5)
    for i, cat in enumerate(categories):
        with cols[i % 5]:
            if st.button(cat, key=f"cat_{cat}", use_container_width=True):
                if cat == "全部":
                    st.session_state.quick_filter_category = None
                else:
                    st.session_state.quick_filter_category = cat
    
    quick_cat = st.session_state.get("quick_filter_category")
    if quick_cat:
        st.info(f"当前快速筛选：{quick_cat}")
    
    filtered_df = df.copy()
    if selected_college != "全部":
        filtered_df = filtered_df[filtered_df['college'] == selected_college]
    filtered_df = filtered_df[(filtered_df['price'] >= price_range[0]) & (filtered_df['price'] <= price_range[1])]
    if quick_cat:
        filtered_df = filtered_df[filtered_df['category'] == quick_cat]

# -------------------- 主页面 --------------------
st.title("📦 校园闲置物品智能交易助手")
st.subheader("让闲置物品找到新主人")

tabs_list = ["🤖 AI智能助手", "💰 发布商品"]
if st.session_state.is_admin:
    tabs_list.append("📊 数据看板")

tab_objects = st.tabs(tabs_list)
tab_ai = tab_objects[0]
tab_sell = tab_objects[1]
tab_data = tab_objects[2] if st.session_state.is_admin else None

# -------------------- 数据看板（治愈系配色） --------------------
if st.session_state.is_admin and tab_data:
    # 治愈系马卡龙配色（低饱和，清新不刺眼）
    healing_colors = [
        '#A8DADC',  # 浅蓝绿
        '#F4A261',  # 暖杏橘
        '#E9C46A',  # 奶油黄
        '#A5D6A7',  # 青草绿
        '#FFCDB2',  # 浅蜜瓜
        '#B0C4DE',  # 淡钢蓝
        '#D4A5A5',  # 淡豆沙粉
        '#C3E8B0',  # 薄荷绿
        '#FBC4AB',  # 蜜桃杏
        '#B8E0D2'   # 浅薄荷蓝
    ]

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

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 📈 商品类别分布")
            category_counts = filtered_df['category'].value_counts()
            fig1, ax1 = plt.subplots(figsize=(6,5))
            wedges, texts, autotexts = ax1.pie(
                category_counts,
                labels=category_counts.index,
                autopct='%1.1f%%',
                startangle=90,
                colors=healing_colors[:len(category_counts)],   # 治愈色系
                wedgeprops={'edgecolor':'white','linewidth':2},
                textprops={'fontsize': 10}
            )
            ax1.axis('equal')
            plt.setp(autotexts, size=9, weight='bold', color='#333333')
            plt.setp(texts, fontsize=10)
            st.pyplot(fig1)

        with col2:
            st.markdown("### 💰 价格区间分布")
            bins = [0,50,100,200,500,3000]
            labels = ['0-50', '50-100', '100-200', '200-500', '500+']
            filtered_df['price_range'] = pd.cut(filtered_df['price'], bins=bins, labels=labels)
            price_dist = filtered_df['price_range'].value_counts().sort_index()
            fig2, ax2 = plt.subplots(figsize=(6,5))
            bars = ax2.bar(price_dist.index, price_dist.values, color=healing_colors[:5])  # 治愈色系
            ax2.set_xlabel('价格区间(元)', fontsize=11)
            ax2.set_ylabel('商品数量', fontsize=11)
            ax2.grid(axis='y', alpha=0.3)
            for bar in bars:
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}',
                        ha='center', va='bottom', fontsize=10)
            st.pyplot(fig2)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 📅 月度发布趋势")
            month_order = ['March','April']
            monthly_data = filtered_df['month'].value_counts().reindex(month_order, fill_value=0)
            fig3, ax3 = plt.subplots(figsize=(6,5))
            ax3.plot(monthly_data.index, monthly_data.values, marker='o', color='#F4A261', linewidth=3)  # 暖杏橘
            ax3.fill_between(monthly_data.index, monthly_data.values, alpha=0.3, color='#FFCDB2')       # 浅蜜瓜填充
            ax3.set_xlabel('月份', fontsize=11)
            ax3.set_ylabel('发布数量', fontsize=11)
            ax3.grid(axis='y', alpha=0.3)
            st.pyplot(fig3)

        with col2:
            st.markdown("### 🔥 热门商品TOP10")
            top_sales = filtered_df.sort_values('sales_count', ascending=False).head(10)
            st.dataframe(top_sales[['name','category','price','sales_count','college']],
                         hide_index=True,
                         column_config={
                             "name":"商品名称","category":"类别",
                             "price":st.column_config.NumberColumn("价格(元)", format="%.2f"),
                             "sales_count":"销量","college":"学院"
                         })

# -------------------- AI 智能助手 --------------------
with tab_ai:
    st.subheader("🤖 智能客服")
    for msg in st.session_state.chat_history:
        if msg['role'] == 'user':
            st.chat_message("user").write(msg['content'])
        else:
            st.chat_message("assistant").write(msg['content'])
    
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
        matched_items = filtered_df.copy()
        import re
        price_match = re.search(r'预算(\d+)元|价格(\d+)元|(\d+)元', user_input)
        if price_match:
            target_price = int(price_match.group(1) or price_match.group(2) or price_match.group(3))
            matched_items = matched_items[(matched_items['price'] >= target_price - 100) & 
                                          (matched_items['price'] <= target_price + 100)]
        category_keywords = ['教材','电器','数码','家具','服装','运动','美妆','食品','书籍']
        matched_categories = [k for k in category_keywords if k in user_input]
        if matched_categories:
            matched_items = matched_items[matched_items['category'].str.contains('|'.join(matched_categories))]
        
        if len(matched_items) == 0:
            result = "😔 没有找到匹配的商品，试试其他关键词吧！"
        else:
            items_info = "\n".join([f"- {row['name']} | {row['category']} | {row['price']}元 | {row['condition']} | {row['college']} | {row['seller_grade']} | 联系方式:{row['contact']}" 
                                    for _, row in matched_items.iterrows()])
            prompt = MATCH_PROMPT.format(items_info=items_info, user_query=user_input)
            client = get_ai_client()
            if client:
                with st.spinner("正在匹配货源..."):
                    try:
                        response = client.chat.completions.create(
                            model=st.session_state.model,
                            messages=[{"role":"user","content":prompt}],
                            temperature=0.7
                        )
                        result = response.choices[0].message.content
                    except Exception as e:
                        result = f"AI调用失败，显示原始匹配结果：\n{items_info}"
            else:
                result = f"API Key未配置，显示原始匹配结果：\n{items_info}"
        st.session_state.chat_history.append({"role":"user","content":user_input})
        st.session_state.chat_history.append({"role":"assistant","content":result})
        st.rerun()
    
    if desc_btn and user_input:
        item_names = filtered_df['name'].tolist()
        selected_item = st.selectbox("选择商品", item_names, key="item_select")
        item = filtered_df[filtered_df['name'] == selected_item].iloc[0]
        prompt = DESC_PROMPT.format(item_name=item['name'], category=item['category'],
                                    condition=item['condition'], price=item['price'],
                                    description=item['description'])
        client = get_ai_client()
        if client:
            with st.spinner("正在生成文案..."):
                try:
                    response = client.chat.completions.create(
                        model=st.session_state.model,
                        messages=[{"role":"user","content":prompt}],
                        temperature=0.7
                    )
                    result = response.choices[0].message.content
                    st.session_state.chat_history.append({"role":"user","content":f"为「{selected_item}」生成文案"})
                    st.session_state.chat_history.append({"role":"assistant","content":result})
                    st.rerun()
                except Exception as e:
                    st.error(f"AI调用失败: {str(e)}")
        else:
            st.warning("请先配置API Key")

# -------------------- 发布商品 --------------------
with tab_sell:
    st.subheader("💰 发布闲置商品")
    st.markdown("填写以下信息发布您的闲置物品")
    with st.form("sell_form"):
        col1, col2 = st.columns(2)
        with col1:
            item_name = st.text_input("商品名称", placeholder="例如：iPhone 13")
            category = st.selectbox("商品类别",
                ["教材","电器","数码","家具","服装","运动","美妆","其他","数码配件","日用品","运动器材","乐器","鞋靴","箱包"])
            price = st.number_input("价格（元）", min_value=0, step=1)
            condition = st.selectbox("商品成色", ["全新","几乎全新","轻微使用痕迹","明显使用痕迹"])
        with col2:
            college = st.selectbox("学院", sorted(df['college'].unique()))
            seller_grade = st.selectbox("卖家年级", ["大一","大二","大三","大四","研究生"])
            contact = st.text_input("联系方式", placeholder="例如：QQ:123456789 或 微信:xxx")
            description = st.text_area("商品描述", placeholder="描述商品的具体情况...", height=100)
        
        submit_btn = st.form_submit_button("发布商品")
        if submit_btn:
            if item_name and category and price > 0 and contact:
                new_item = pd.DataFrame({
                    'id': [len(df) + 1],
                    'name': [item_name],
                    'category': [category],
                    'price': [price],
                    'condition': [condition],
                    'college': [college],
                    'seller_grade': [seller_grade],
                    'sales_count': [0],
                    'post_date': [pd.Timestamp.now()],
                    'description': [description],
                    'contact': [contact]
                })
                script_dir = os.path.dirname(os.path.abspath(__file__))
                data_path = os.path.join(script_dir, "data", "items.csv")
                new_item.to_csv(data_path, mode='a', header=False, index=False)
                st.success("🎉 商品发布成功！")
                st.rerun()
            else:
                st.error("请填写完整的商品信息（名称、类别、价格、联系方式为必填项）")

st.markdown("---")
st.caption("💡 提示：点击右上角 ⚙️ 配置API Key后即可使用AI功能")
