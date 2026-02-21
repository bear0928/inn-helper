import streamlit as st
import pandas as pd
import os
import subprocess
from datetime import datetime
from deep_translator import GoogleTranslator
from streamlit_sortables import sort_items

# --- 網頁基礎設定 ---
st.set_page_config(page_title="旅館客服系統", layout="wide")

# 強制讓 st.code 自動換行，並調整輸入框字體
st.markdown("""
    <style>
    code { white-space: pre-wrap !important; word-break: break-word !important; }
    textarea { font-family: sans-serif !important; }
    </style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "000000" 
CSV_FILE = 'templates.csv'

# --- 1. 資料處理與自動 Git 功能 ---
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
    df['priority'] = pd.to_numeric(df['priority'], errors='coerce').fillna(999)
    df = df.sort_values(by="priority")
    df.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')
    
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message = f"Update CSV: {current_time}"
        subprocess.run(["git", "add", CSV_FILE], check=True)
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        st.toast(f"🚀 已同步至 GitHub: {commit_message}")
    except Exception as e:
        st.warning(f"本地檔案已儲存，但 Git 同步失敗")

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 2. 側邊欄設定 ---
st.sidebar.title("🏨 管理系統")
branch = st.sidebar.selectbox("切換分館", ["喜園館", "中華館", "長沙館"])
user_mode = st.sidebar.radio("類別選擇", ["公版回覆", "個人常用"])

is_admin = False
staff_name = "Kuma"

if user_mode == "公版回覆":
    pwd = st.sidebar.text_input("輸入管理密碼以修改內容", type="password")
    if pwd == ADMIN_PASSWORD:
        is_admin = True
        st.sidebar.success("管理權限已開啟")
else:
    is_admin = True
    existing_staff = [c for c in st.session_state.df['category'].unique() if c != "公版回覆"]
    if existing_staff:
        staff_name = st.sidebar.selectbox("切換員工帳號", sorted(existing_staff))
    else:
        staff_name = st.sidebar.text_input("輸入新員工姓名", value="Kuma")

# --- 3. 新增模板區塊 (加大輸入框) ---
if is_admin:
    st.sidebar.divider()
    with st.sidebar.expander("➕ 新增回覆模板", expanded=False):
        n_title = st.text_input("模板標題 (必填)")
        n_note = st.text_input("備註標籤")
        # 加大新增時的內容框
        n_en = st.text_area("英文內容", height=250)
        n_tw = st.text_area("中文內容", height=250)
        
        target_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
        
        if st.button("💾 確認儲存模板"):
            if n_title:
                new_data = {
                    "branch": branch, "category": target_cat, "title": n_title, 
                    "content_en": n_en, "content_tw": n_tw, "note": n_note, 
                    "priority": len(st.session_state.df) + 1
                }
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_data])], ignore_index=True)
                save_data(st.session_state.df)
                st.rerun()

st.sidebar.divider()
sort_mode = st.sidebar.toggle("🔄 開啟拖動排序模式", value=False)

# --- 4. 主畫面：翻譯功能 ---
st.title(f"💬 {branch} 客服中心")
src_text = st.text_input("🌐 翻譯中心：")
if src_text:
    res = GoogleTranslator(source='auto', target='zh-TW').translate(src_text)
    st.info(f"**翻譯結果：** {res}")

st.divider()

# --- 5. 顯示與排序邏輯 ---
current_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
view_df = st.session_state.df[(st.session_state.df['branch'] == branch) & 
                              (st.session_state.df['category'] == current_cat)].copy()

if view_df.empty:
    st.info(f"目前【{current_cat}】尚無內容。")
else:
    view_df['priority'] = pd.to_numeric(view_df['priority'], errors='coerce').fillna(999)
    view_df = view_df.sort_values(by="priority")

    if sort_mode:
        st.subheader("🖱️ 拖動標題調整順序")
        items_to_sort = view_df['title'].tolist()
        sorted_items = sort_items(items_to_sort)
        if st.button("🚀 儲存新順序並更新 GitHub"):
            for i, title in enumerate(sorted_items):
                target_mask = (st.session_state.df['branch'] == branch) & \
                              (st.session_state.df['category'] == current_cat) & \
                              (st.session_state.df['title'] == title)
                st.session_state.df.loc[target_mask, 'priority'] = i
            save_data(st.session_state.df)
            st.rerun()
    else:
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
                    if st.button("✏️", key=f"e_{idx}"): st.session_state[f"edit_{idx}"] = True
                    if st.button("🗑️", key=f"d_{idx}"):
                        st.session_state.df = st.session_state.df.drop(idx)
                        save_data(st.session_state.df)
                        st.rerun()
                
                # --- 修改區塊 (加大輸入框至 300px) ---
                if st.session_state.get(f"edit_{idx}", False):
                    with st.container(border=True):
                        st.subheader(f"🛠️ 正在修改：{row['title']}")
                        et = st.text_input("修改標題", row['title'], key=f"t_{idx}")
                        en = st.text_input("修改備註", row['note'], key=f"n_{idx}")
                        # 這裡使用 height=300 讓框框變大
                        ee = st.text_area("修改英文內容", row['content_en'], key=f"en_{idx}", height=300)
                        etw = st.text_area("修改中文內容", row['content_tw'], key=f"tw_{idx}", height=300)
                        
                        c1, c2 = st.columns(2)
                        if c1.button("💾 儲存並同步 GitHub", key=f"s_{idx}"):
                            st.session_state.df.at[idx, 'title'] = et
                            st.session_state.df.at[idx, 'note'] = en
                            st.session_state.df.at[idx, 'content_en'] = ee
                            st.session_state.df.at[idx, 'content_tw'] = etw
                            save_data(st.session_state.df)
                            st.session_state[f"edit_{idx}"] = False
                            st.rerun()
                        if c2.button("✖️ 取消修改", key=f"c_{idx}"):
                            st.session_state[f"edit_{idx}"] = False
                            st.rerun()