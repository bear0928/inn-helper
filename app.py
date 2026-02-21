import streamlit as st
import pandas as pd
import os
from deep_translator import GoogleTranslator

st.set_page_config(page_title="旅館客服系統", layout="wide")

# --- 資料讀取 ---
CSV_FILE = 'templates.csv'
if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
else:
    df = pd.DataFrame(columns=["branch", "category", "title", "content_en", "content_tw"])

# --- 側邊欄設定 ---
st.sidebar.title("🏨 客服系統")
branch = st.sidebar.selectbox("切換分館", ["喜園館", "西門館", "花園館"])
user_mode = st.sidebar.radio("類別", ["公版回覆", "個人常用"])
staff_name = ""
if user_mode == "個人常用":
    staff_name = st.sidebar.text_input("輸入員工姓名", "Kuma")

# --- 主畫面 ---
st.title(f"💬 {branch} 客服小幫手")

# 區塊 A：Google 翻譯窗口 (外語轉繁中)
st.subheader("🌐 即時翻譯窗口")
source_text = st.text_area("請輸入顧客訊息 (自動偵測語言)：", height=100)
if st.button("翻譯成繁體中文"):
    if source_text:
        res = GoogleTranslator(source='auto', target='zh-TW').translate(source_text)
        st.success(f"翻譯結果：\n\n{res}")

st.divider()

# 區塊 B：回覆模板庫
st.subheader("📄 常用模板 (中英雙窗口)")
cat = "公用回覆" if user_mode == "公用回覆" else staff_name
view_df = df[(df['branch'] == branch) & (df['category'] == cat)]

if view_df.empty:
    st.info("目前此分類下無模板。")
else:
    for _, row in view_df.iterrows():
        with st.expander(f"📌 {row['title']}", expanded=False):
            col_en, col_tw = st.columns(2)
            with col_en:
                st.write("**🇺🇸 English**")
                st.code(row['content_en'], language="text")
            with col_tw:
                st.write("**🇹🇼 中文回覆**")
                st.code(row['content_tw'], language="text")