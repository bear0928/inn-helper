import streamlit as st
import pandas as pd
import sqlite3
import os
import subprocess
from datetime import datetime
from deep_translator import GoogleTranslator
from streamlit_sortables import sort_items

# --- 1. 資料庫基礎功能 ---
DB_FILE = 'data.db'

def init_db():
    """初始化資料庫：如果不存在就建立 data.db 與 templates 表"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch TEXT,
            category TEXT,
            title TEXT,
            content_en TEXT,
            content_tw TEXT,
            note TEXT,
            priority INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def get_db_data():
    """讀取資料庫回傳 DataFrame"""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM templates ORDER BY priority ASC", conn)
    conn.close()
    return df

def save_and_sync(query, params):
    """執行 SQL 指令並嘗試同步到 GitHub"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        conn.close()
        
        # 自動 Git 同步 (備份 db 檔案)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        subprocess.run(["git", "add", DB_FILE], capture_output=True)
        subprocess.run(["git", "commit", "-m", f"DB Update: {current_time}"], capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], capture_output=True)
        return True
    except Exception as e:
        st.error(f"資料庫操作失敗: {e}")
        return False

# --- 2. 網頁配置 ---
st.set_page_config(page_title="旅館客服系統 (SQL)", layout="wide")
init_db()

st.markdown("""
    <style>
    code { white-space: pre-wrap !important; word-break: break-word !important; }
    textarea { font-family: sans-serif !important; }
    </style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "000000"

# --- 3. 側邊欄邏輯 ---
st.sidebar.title("🏨 旅館管理 (SQL)")
branch = st.sidebar.selectbox("切換分館", ["喜園館", "中華館", "長沙館"])
user_mode = st.sidebar.radio("類別選擇", ["公版回覆", "個人常用"])

df = get_db_data()

is_admin = False
staff_name = "Kuma"
if user_mode == "公版回覆":
    if st.sidebar.text_input("管理密碼", type="password") == ADMIN_PASSWORD:
        is_admin = True
else:
    is_admin = True
    staff_list = sorted(df[df['category'] != "公版回覆"]['category'].unique())
    if staff_list:
        staff_name = st.sidebar.selectbox("員工帳號", staff_list)
    else:
        staff_name = st.sidebar.text_input("輸入員工姓名", value="Kuma")

# --- 4. 新增模板 (使用 Form 並清空) ---
if is_admin:
    st.sidebar.divider()
    with st.sidebar.expander("➕ 新增回覆模板", expanded=False):
        with st.form("add_template_form", clear_on_submit=True):
            n_t = st.text_input("模板標題 (必填)")
            n_n = st.text_input("備註標籤 (如: ⚠️)")
            n_e = st.text_area("英文內容", height=250)
            n_w = st.text_area("中文內容", height=250)
            
            if st.form_submit_button("💾 確認儲存模板"):
                if n_t:
                    target_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
                    query = "INSERT INTO templates (branch, category, title, content_en, content_tw, note, priority) VALUES (?,?,?,?,?,?,?)"
                    params = (branch, target_cat, n_t, n_e, n_w, n_n, len(df))
                    if save_and_sync(query, params):
                        st.success("✅ 已存入資料庫並同步 GitHub")
                        st.rerun()
                else:
                    st.error("標題必填！")

# --- 5. 主畫面 ---
st.title(f"💬 {branch} 客服中心")
src_text = st.text_input("🌐 翻譯中心 (自動轉繁中)：")
if src_text:
    res = GoogleTranslator(source='auto', target='zh-TW').translate(src_text)
    st.info(f"**翻譯：** {res}")

st.divider()

# --- 6. 內容顯示與編輯 ---
sort_mode = st.sidebar.toggle("🔄 拖動排序模式")
current_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
view_df = df[(df['branch'] == branch) & (df['category'] == current_cat)]

if view_df.empty:
    st.info("目前尚無模板。")
else:
    if sort_mode:
        st.subheader("🖱️ 拖動標題調整順序")
        titles = view_df['title'].tolist()
        sorted_titles = sort_items(titles)
        if st.button("🚀 儲存新順序"):
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            for i, t in enumerate(sorted_titles):
                c.execute("UPDATE templates SET priority=? WHERE title=? AND category=? AND branch=?", (i, t, current_cat, branch))
            conn.commit()
            conn.close()
            st.rerun()
    else:
        for _, row in view_df.iterrows():
            col1, col2 = st.columns([0.85, 0.15])
            with col1:
                with st.expander(f"📌 {row['title']} {row['note']}"):
                    st.write("**🇺🇸 English**")
                    st.code(row['content_en'], language="text")
                    st.write("**🇹🇼 中文**")
                    st.code(row['content_tw'], language="text")
            
            if is_admin:
                with col2:
                    if st.button("✏️", key=f"edit_btn_{row['id']}"):
                        st.session_state[f"edit_mode_{row['id']}"] = True
                    if st.button("🗑️", key=f"del_btn_{row['id']}"):
                        save_and_sync("DELETE FROM templates WHERE id=?", (row['id'],))
                        st.rerun()
                
                # --- 修改大框框 UI ---
                if st.session_state.get(f"edit_mode_{row['id']}", False):
                    with st.container(border=True):
                        st.subheader(f"🛠️ 修改：{row['title']}")
                        et = st.text_input("修改標題", row['title'], key=f"t_{row['id']}")
                        en = st.text_input("修改備註", row['note'], key=f"n_{row['id']}")
                        ee = st.text_area("修改英文", row['content_en'], key=f"en_{row['id']}", height=300)
                        ew = st.text_area("修改中文", row['content_tw'], key=f"tw_{row['id']}", height=300)
                        
                        c1, c2 = st.columns(2)
                        if c1.button("💾 儲存修改", key=f"save_edit_{row['id']}"):
                            q = "UPDATE templates SET title=?, note=?, content_en=?, content_tw=? WHERE id=?"
                            p = (et, en, ee, ew, row['id'])
                            if save_and_sync(q, p):
                                st.session_state[f"edit_mode_{row['id']}"] = False
                                st.rerun()
                        if c2.button("✖️ 取消", key=f"cancel_{row['id']}"):
                            st.session_state[f"edit_mode_{row['id']}"] = False
                            st.rerun()