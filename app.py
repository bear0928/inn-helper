import streamlit as st
import pandas as pd
import os
from deep_translator import GoogleTranslator
from streamlit_sortables import sort_items  # 需安裝：pip install streamlit-sortables

# 網頁基礎設定
st.set_page_config(page_title="旅館客服系統", layout="wide")

# 強制讓 st.code 自動換行的 CSS
st.markdown("""
    <style>
    code { white-space: pre-wrap !important; word-break: break-word !important; }
    </style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "000000" 
CSV_FILE = 'templates.csv'

def load_data():
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            required_cols = ["branch", "category", "title", "content_en", "content_tw", "note", "priority"]
            for col in required_cols:
                if col not in df.columns:
                    df[col] = 999 if col == "priority" else ""
            return df
        except:
            return pd.DataFrame(columns=["branch", "category", "title", "content_en", "content_tw", "note", "priority"])
    else:
        return pd.DataFrame(columns=["branch", "category", "title", "content_en", "content_tw", "note", "priority"])

def save_data(df):
    # 儲存前確保 priority 是數字型態
    df['priority'] = pd.to_numeric(df['priority'], errors='coerce').fillna(999)
    df = df.sort_values(by="priority")
    df.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 側邊欄 ---
st.sidebar.title("🏨 管理系統")
branch = st.sidebar.selectbox("切換分館", ["喜園館", "中華館", "長沙館"])
user_mode = st.sidebar.radio("類別選擇", ["公版回覆", "個人常用"])

is_admin = False
if user_mode == "公版回覆":
    pwd = st.sidebar.text_input("輸入管理密碼以修改內容", type="password")
    if pwd == ADMIN_PASSWORD:
        is_admin = True
else:
    is_admin = True

# 排序模式開關 (任何人皆可使用)
sort_mode = st.sidebar.toggle("🔄 開啟拖動排序模式", value=False)

staff_name = ""
if user_mode == "個人常用":
    existing_staff = st.session_state.df[st.session_state.df['category'] != "公版回覆"]['category'].unique().tolist()
    staff_options = sorted(existing_staff) + ["+ 新增員工"] if existing_staff else ["+ 新增員工"]
    selected_staff = st.sidebar.selectbox("選擇員工", staff_options)
    if selected_staff == "+ 新增員工":
        new_in = st.sidebar.text_input("輸入新名字")
        staff_name = new_in if new_in else "New Staff"
    else:
        staff_name = selected_staff

# --- 主畫面 ---
st.title(f"💬 {branch} 客服中心")
src_text = st.text_input("🌐 翻譯中心 (輸入後按 Enter)：")
if src_text:
    res = GoogleTranslator(source='auto', target='zh-TW').translate(src_text)
    st.info(f"**翻譯：** {res}")

st.divider()

# --- 模板列表與排序邏輯 ---
curr_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
mask = (st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == curr_cat)
view_df = st.session_state.df[mask].copy()
view_df['priority'] = pd.to_numeric(view_df['priority'], errors='coerce').fillna(999)
view_df = view_df.sort_values(by="priority")

if view_df.empty:
    st.info("目前沒有資料。")
else:
    if sort_mode:
        st.subheader("🖱️ 拖動標題來調整順序")
        # 建立一個標題與原始索引的對照表
        items_to_sort = view_df['title'].tolist()
        sorted_items = sort_items(items_to_sort)
        
        if st.button("💾 儲存新順序"):
            # 根據拖動後的結果，更新原始 df 的 priority
            for i, title in enumerate(sorted_items):
                # 找到該標題在原始資料中的索引 (需同時匹配分館與類別)
                idx = st.session_state.df[(st.session_state.df['branch'] == branch) & 
                                          (st.session_state.df['category'] == curr_cat) & 
                                          (st.session_state.df['title'] == title)].index
                if not idx.empty:
                    st.session_state.df.at[idx[0], 'priority'] = i
            
            save_data(st.session_state.df)
            st.success("順序已更新！")
            st.rerun()
    else:
        # 正常顯示模式
        for idx, row in view_df.iterrows():
            m_cols = st.columns([0.85, 0.15]) if is_admin else st.columns([1.0])
            with m_cols[0]:
                label = f"🏷️ {row['note']}" if row['note'] else ""
                with st.expander(f"📌 {row['title']} {label}"):
                    st.write("**🇺🇸 English**")
                    st.code(row['content_en'], language="text")
                    st.write("**🇹🇼 中文**")
                    st.code(row['content_tw'], language="text")

            if is_admin:
                with m_cols[1]:
                    c1, c2 = st.columns(2)
                    if c1.button("✏️", key=f"e_{idx}"): st.session_state[f"edit_{idx}"] = True
                    if c2.button("🗑️", key=f"d_{idx}"):
                        st.session_state.df = st.session_state.df.drop(idx)
                        save_data(st.session_state.df)
                        st.rerun()
                
                if st.session_state.get(f"edit_{idx}", False):
                    with st.container(border=True):
                        et = st.text_input("標題", row['title'], key=f"t_{idx}")
                        en = st.text_input("備註", row['note'], key=f"n_{idx}")
                        ee = st.text_area("英文", row['content_en'], key=f"en_{idx}")
                        etw = st.text_area("中文", row['content_tw'], key=f"tw_{idx}")
                        if st.button("💾 儲存修改", key=f"s_{idx}"):
                            st.session_state.df.at[idx, 'title'], st.session_state.df.at[idx, 'note'] = et, en
                            st.session_state.df.at[idx, 'content_en'], st.session_state.df.at[idx, 'content_tw'] = ee, etw
                            save_data(st.session_state.df)
                            st.session_state[f"edit_{idx}"] = False
                            st.rerun()