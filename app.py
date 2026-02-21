import streamlit as st
import pandas as pd
import os
import subprocess
import time
from datetime import datetime
from deep_translator import GoogleTranslator
from streamlit_sortables import sort_items

# --- 基礎設定 ---
st.set_page_config(page_title="旅館客服系統", layout="wide")

st.markdown("""
    <style>
    code { white-space: pre-wrap !important; }
    textarea { font-family: sans-serif !important; }
    </style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "000000" 
CSV_FILE = 'templates.csv'

# --- 1. 資料處理與強制同步 ---
def load_data():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        # 確保必要欄位都存在
        for col in ["branch", "category", "title", "content_en", "content_tw", "note", "priority"]:
            if col not in df.columns:
                df[col] = 999 if col == "priority" else ""
        return df
    return pd.DataFrame(columns=["branch", "category", "title", "content_en", "content_tw", "note", "priority"])

def save_data(df):
    """強力儲存：確保寫入磁碟並執行推送"""
    try:
        # 格式化
        df['priority'] = pd.to_numeric(df['priority'], errors='coerce').fillna(999)
        df = df.sort_values(by="priority")
        
        # 核心：強制存檔，不留緩存
        df.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')
        
        # Git 同步
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"Update CSV: {current_time}"
        
        # 使用串接指令確保順序執行
        cmd = f'git add {CSV_FILE} && git commit -m "{msg}" && git push origin main'
        process = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if process.returncode == 0:
            st.toast(f"🚀 已存檔並推送 GitHub: {current_time}")
        else:
            st.warning("本地已存檔，但 Git 推送遇到問題。")
        
        return True
    except Exception as e:
        st.error(f"儲存失敗：{e}")
        return False

# 確保 session_state 始終有最新資料
if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 2. 側邊欄與管理邏輯 ---
st.sidebar.title("🏨 管理系統")
branch = st.sidebar.selectbox("切換分館", ["喜園館", "中華館", "長沙館"])
user_mode = st.sidebar.radio("類別選擇", ["公版回覆", "個人常用"])

is_admin = False
staff_name = "Kuma"
if user_mode == "公版回覆":
    if st.sidebar.text_input("管理密碼", type="password") == ADMIN_PASSWORD:
        is_admin = True
else:
    is_admin = True
    staff_list = sorted([c for c in st.session_state.df['category'].unique() if c != "公版回覆"])
    if staff_list:
        staff_name = st.sidebar.selectbox("員工帳號", staff_list)
    else:
        staff_name = st.sidebar.text_input("新員工姓名", value="Kuma")

# --- 3. 新增模板 (使用 Form 確保清空與執行) ---
if is_admin:
    st.sidebar.divider()
    with st.sidebar.expander("➕ 新增回覆模板", expanded=False):
        with st.form("add_new_template", clear_on_submit=True):
            n_t = st.text_input("模板標題")
            n_n = st.text_input("備註標籤")
            n_e = st.text_area("英文內容", height=250)
            n_w = st.text_area("中文內容", height=250)
            submit = st.form_submit_button("💾 確認儲存模板")
            
            if submit and n_t:
                target_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
                new_data = {
                    "branch": branch, "category": target_cat, "title": n_t, 
                    "content_en": n_e, "content_tw": n_w, "note": n_n, 
                    "priority": len(st.session_state.df) + 1
                }
                # 直接更新 session_state 並立刻存檔
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_data])], ignore_index=True)
                if save_data(st.session_state.df):
                    time.sleep(0.5) # 給系統一點緩衝時間
                    st.rerun()

# --- 4. 翻譯功能 ---
st.title(f"💬 {branch} 客服中心")
src_text = st.text_input("🌐 翻譯中心：")
if src_text:
    st.info(f"**翻譯結果：** {GoogleTranslator(source='auto', target='zh-TW').translate(src_text)}")

st.divider()

# --- 5. 顯示與排序模式 ---
sort_mode = st.sidebar.toggle("🔄 拖動排序模式")
current_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
view_df = st.session_state.df[(st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat)].copy()

if not view_df.empty:
    view_df['priority'] = pd.to_numeric(view_df['priority']).fillna(999)
    view_df = view_df.sort_values("priority")

    if sort_mode:
        titles = view_df['title'].tolist()
        sorted_titles = sort_items(titles)
        if st.button("🚀 儲存順序"):
            for i, t in enumerate(sorted_titles):
                mask = (st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat) & (st.session_state.df['title'] == t)
                st.session_state.df.loc[mask, 'priority'] = i
            save_data(st.session_state.df)
            st.rerun()
    else:
        for idx, row in view_df.iterrows():
            col1, col2 = st.columns([0.9, 0.1])
            with col1:
                with st.expander(f"📌 {row['title']} {row['note']}"):
                    st.write("**🇺🇸 English**")
                    st.code(row['content_en'])
                    st.write("**🇹🇼 中文**")
                    st.code(row['content_tw'])
            with col2:
                if st.button("🗑️", key=f"del_{idx}"):
                    st.session_state.df = st.session_state.df.drop(idx)
                    save_data(st.session_state.df)
                    st.rerun()