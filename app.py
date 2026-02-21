import streamlit as st
import pandas as pd
import os
from deep_translator import GoogleTranslator

# 網頁基礎設定
st.set_page_config(page_title="旅館客服系統", layout="wide")

# 強制讓 st.code 自動換行的 CSS
st.markdown("""
    <style>
    code {
        white-space: pre-wrap !important;
        word-break: break-word !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 設定管理密碼 ---
ADMIN_PASSWORD = "ximen888" 

# --- 1. 資料處理函數 ---
CSV_FILE = 'templates.csv'

def load_data():
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            required_cols = ["branch", "category", "title", "content_en", "content_tw", "note"]
            for col in required_cols:
                if col not in df.columns:
                    df[col] = ""
            return df
        except:
            return pd.DataFrame(columns=["branch", "category", "title", "content_en", "content_tw", "note"])
    else:
        return pd.DataFrame(columns=["branch", "category", "title", "content_en", "content_tw", "note"])

def save_data(df):
    df.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 2. 側邊欄設定 ---
st.sidebar.title("🏨 管理系統")
branch = st.sidebar.selectbox("切換分館", ["喜園館", "中華館", "長沙館"])
user_mode = st.sidebar.radio("類別選擇", ["公版回覆", "個人常用"])

is_admin = False
if user_mode == "公版回覆":
    pwd = st.sidebar.text_input("輸入管理密碼以修改", type="password")
    if pwd == ADMIN_PASSWORD:
        is_admin = True
        st.sidebar.success("管理權限已開啟")
    elif pwd:
        st.sidebar.error("密碼不正確")
else:
    is_admin = True

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

st.sidebar.divider()

# --- 3. 新增模板 ---
if is_admin:
    with st.sidebar.expander("➕ 新增模板"):
        n_title = st.text_input("標題")
        n_note = st.text_input("備註標籤")
        n_en = st.text_area("英文內容")
        n_tw = st.text_area("中文內容")
        t_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
        if st.button("確認儲存"):
            if n_title:
                new_data = {"branch": branch, "category": t_cat, "title": n_title, "content_en": n_en, "content_tw": n_tw, "note": n_note}
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_data])], ignore_index=True)
                save_data(st.session_state.df)
                st.rerun()

# --- 4. 翻譯功能 ---
st.title(f"💬 {branch} 客服中心")
src_text = st.text_input("🌐 輸入外文訊息並按 Enter：")
if src_text:
    res = GoogleTranslator(source='auto', target='zh-TW').translate(src_text)
    st.info(f"**翻譯：** {res}")

st.divider()

# --- 5. 模板列表 ---
st.subheader(f"📄 {user_mode}清單")
curr_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
mask = (st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == curr_cat)
view_df = st.session_state.df[mask]

if view_df.empty:
    st.info("目前沒有資料。")
else:
    for idx, row in view_df.iterrows():
        # 修正欄位比例，避免出現 0.00 導致報錯
        m_cols = st.columns([0.85, 0.15]) if is_admin else st.columns([1.0])
        
        with m_cols[0]:
            label = f"🏷️ {row['note']}" if row['note'] else ""
            with st.expander(f"📌 {row['title']} {label}"):
                if label: st.warning(f"💡 {row['note']}")
                # 改為單欄上下排列，並應用自動換行 CSS
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
            
            # 編輯區域
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