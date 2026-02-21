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
        # 若檔案不存在，建立預設欄位
        return pd.DataFrame(columns=["branch", "category", "title", "content_en", "content_tw"])

def save_data(df):
    # 儲存回 CSV，使用 utf-8-sig 確保中文不亂碼
    df.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')

# 使用 session_state 儲存資料，避免每次操作都重新讀取導致速度變慢
if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 2. 側邊欄設定 ---
st.sidebar.title("🏨 客服系統")
branch = st.sidebar.selectbox("切換分館", ["喜園館", "中華館", "長沙館"])
user_mode = st.sidebar.radio("類別", ["公版回覆", "個人常用"])

staff_name = ""
if user_mode == "個人常用":
    staff_name = st.sidebar.text_input("輸入員工姓名", "Kuma")

st.sidebar.divider()

# --- 3. 新增回覆模板功能 (側邊欄) ---
with st.sidebar.expander("➕ 新增模板"):
    new_title = st.text_input("模板標題 (例：接機資訊)")
    new_en = st.text_area("英文內容")
    new_tw = st.text_area("中文內容")
    
    # 判斷要存入公版還是個人常用
    target_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
    
    if st.button("確認新增"):
        if new_title and (new_en or new_tw):
            new_data = {
                "branch": branch,
                "category": target_cat,
                "title": new_title,
                "content_en": new_en,
                "content_tw": new_tw
            }
            # 更新數據庫
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_data])], ignore_index=True)
            save_data(st.session_state.df)
            st.success(f"✅ 已新增至 {target_cat}")
            st.rerun()
        else:
            st.error("請至少填寫標題與一項內容")

# --- 4. 主畫面 ---
st.title(f"💬 {branch} 客服小幫手")

# 區塊 A：Google 翻譯窗口
st.subheader("🌐 即時翻譯窗口")
source_text = st.text_area("請輸入顧客訊息 (自動偵測語言)：", height=100)
if st.button("翻譯成繁體中文"):
    if source_text:
        res = GoogleTranslator(source='auto', target='zh-TW').translate(source_text)
        st.success(f"翻譯結果：\n\n{res}")

st.divider()

# 區塊 B：回覆模板庫
st.subheader(f"📄 {user_mode} 模板庫")
current_cat = "公版回覆" if user_mode == "公版回覆" else staff_name

# 篩選目前分館與分類的資料
mask = (st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat)
view_df = st.session_state.df[mask]

if view_df.empty:
    st.info(f"目前 {branch} 的 {current_cat} 分類下沒有模板，請從側邊欄新增。")
else:
    # 遍歷顯示模板
    for index, row in view_df.iterrows():
        # 使用 columns 讓標題與刪除按鈕並排
        col_main, col_del = st.columns([0.9, 0.1])
        
        with col_main:
            with st.expander(f"📌 {row['title']}", expanded=False):
                col_en, col_tw = st.columns(2)
                with col_en:
                    st.write("**🇺🇸 English**")
                    st.code(row['content_en'], language="text")
                with col_tw:
                    st.write("**🇹🇼 中文回覆**")
                    st.code(row['content_tw'], language="text")
        
        with col_del:
            # 刪除功能
            if st.button("🗑️", key=f"del_{index}"):
                # 從 DataFrame 移除該列並存檔
                st.session_state.df = st.session_state.df.drop(index)
                save_data(st.session_state.df)
                st.toast(f"已刪除：{row['title']}")
                st.rerun()

st.sidebar.caption(f"目前共有 {len(st.session_state.df)} 筆模板數據")