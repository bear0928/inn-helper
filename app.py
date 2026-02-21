import streamlit as st
import pandas as pd
import os
from deep_translator import GoogleTranslator

st.set_page_config(page_title="旅館客服系統", layout="wide")

# --- 1. 資料處理函數 ---
CSV_FILE = 'templates.csv'

def load_data():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    else:
        # 新增 note 欄位
        return pd.DataFrame(columns=["branch", "category", "title", "content_en", "content_tw", "note"])

def save_data(df):
    df.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 2. 側邊欄設定 ---
st.sidebar.title("🏨 喜園管理系統")
branch = st.sidebar.selectbox("切換分館", ["喜園館", "中華館", "長沙館"])
user_mode = st.sidebar.radio("類別", ["公版回覆", "個人常用"])

staff_name = ""
if user_mode == "個人常用":
    staff_name = st.sidebar.text_input("輸入員工姓名", "Kuma")

st.sidebar.divider()

# --- 3. 新增回覆模板功能 (增加備註欄位) ---
with st.sidebar.expander("➕ 新增模板"):
    new_title = st.text_input("模板標題")
    new_note = st.text_input("小備註 (例：過年專用、需補資料)")
    new_en = st.text_area("英文內容")
    new_tw = st.text_area("中文內容")
    
    target_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
    
    if st.button("確認新增"):
        if new_title:
            new_data = {
                "branch": branch,
                "category": target_cat,
                "title": new_title,
                "content_en": new_en,
                "content_tw": new_tw,
                "note": new_note
            }
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_data])], ignore_index=True)
            save_data(st.session_state.df)
            st.success("✅ 已新增備註與內容")
            st.rerun()

# --- 4. 主畫面 ---
st.title(f"💬 {branch} 客服小幫手")

# 翻譯窗口
with st.expander("🌐 即時翻譯窗口", expanded=False):
    source_text = st.text_area("貼上顧客訊息：", height=100)
    if st.button("翻譯成繁體中文"):
        if source_text:
            res = GoogleTranslator(source='auto', target='zh-TW').translate(source_text)
            st.success(f"結果：{res}")

st.divider()

# --- 5. 模板顯示庫 (加入小備註標籤) ---
st.subheader(f"📄 {user_mode} 模板庫")
current_cat = "公版回覆" if user_mode == "公版回覆" else staff_name

mask = (st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat)
view_df = st.session_state.df[mask]

if view_df.empty:
    st.info("目前無資料。")
else:
    for index, row in view_df.iterrows():
        col_main, col_del = st.columns([0.9, 0.1])
        
        with col_main:
            # 標題旁邊顯示小備註
            note_text = f" | 💡 {row['note']}" if pd.notna(row['note']) and row['note'] != "" else ""
            with st.expander(f"📌 {row['title']} {note_text}", expanded=False):
                # 如果有備註，特別用警告框顯示在最上方
                if note_text:
                    st.warning(f"操作指南：{row['note']}")
                
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**🇺🇸 English**")
                    st.code(row['content_en'], language="text")
                with c2:
                    st.write("**🇹🇼 中文**")
                    st.code(row['content_tw'], language="text")
        
        with col_del:
            if st.button("🗑️", key=f"del_{index}"):
                st.session_state.df = st.session_state.df.drop(index)
                save_data(st.session_state.df)
                st.rerun()