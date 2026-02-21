import streamlit as st
import pandas as pd
import os
from deep_translator import GoogleTranslator

st.set_page_config(page_title="旅館客服系統", layout="wide")

# --- 1. 資料處理函數 ---
CSV_FILE = 'templates.csv'

def load_data():
    if os.path.exists(CSV_FILE):
        try:
            return pd.read_csv(CSV_FILE)
        except:
            return pd.DataFrame(columns=["branch", "category", "title", "content_en", "content_tw", "note"])
    else:
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

# --- 3. 新增回覆模板功能 ---
with st.sidebar.expander("➕ 新增模板"):
    new_title = st.text_input("模板標題")
    new_note = st.text_input("小備註 (例：過年專用)")
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
            st.success("✅ 已新增")
            st.rerun()

# --- 4. 主畫面 ---
st.title(f"💬 {branch} 客服小幫手")

# --- 區塊 A：即時翻譯窗口 (按 Enter 觸發) ---
st.subheader("🌐 即時翻譯中心 (外語 → 繁中)")
# 改用 text_input，使用者貼上文字後按 Enter 即可翻譯
source_text = st.text_input("在此貼上顧客訊息並按下 Enter：", placeholder="Paste guest message and press Enter...")

if source_text:
    try:
        with st.spinner('Translating...'):
            translated_res = GoogleTranslator(source='auto', target='zh-TW').translate(source_text)
            st.info(f"**中文翻譯結果：**\n\n{translated_res}")
            # 提供一個小按鈕清空輸入內容
            if st.button("清空翻譯"):
                st.rerun()
    except Exception as e:
        st.error(f"翻譯發生錯誤，請檢查網路連線。")
else:
    st.caption("等待輸入中... (支援多國語言自動偵測)")

st.divider()

# --- 5. 模板顯示庫 ---
st.subheader(f"📄 {user_mode} 模板庫")
current_cat = "公版回覆" if user_mode == "公版回覆" else staff_name

mask = (st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat)
view_df = st.session_state.df[mask]

if view_df.empty:
    st.info("此分類目前尚無模板。")
else:
    for index, row in view_df.iterrows():
        col_main, col_del = st.columns([0.92, 0.08])
        
        with col_main:
            note_tag = f" 💡 {row['note']}" if pd.notna(row['note']) and row['note'] != "" else ""
            with st.expander(f"📌 {row['title']} {note_tag}", expanded=False):
                if note_tag:
                    st.warning(f"**操作備註：** {row['note']}")
                
                c_en, c_tw = st.columns(2)
                with c_en:
                    st.write("**🇺🇸 English**")
                    st.code(row['content_en'], language="text")
                with c_tw:
                    st.write("**🇹🇼 中文**")
                    st.code(row['content_tw'], language="text")
        
        with col_del:
            if st.button("🗑️", key=f"del_{index}"):
                st.session_state.df = st.session_state.df.drop(index)
                save_data(st.session_state.df)
                st.rerun()