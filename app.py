import streamlit as st
import pandas as pd
import os
from deep_translator import GoogleTranslator

# 網頁基礎設定
st.set_page_config(page_title="旅館客服系統", layout="wide")

# --- 1. 資料處理函數 ---
CSV_FILE = 'templates.csv'

def load_data():
    if os.path.exists(CSV_FILE):
        try:
            # 讀取時確保編碼正確
            df = pd.read_csv(CSV_FILE)
            # 檢查並補足必要的欄位
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
    # 儲存為 UTF-8-SIG 以確保 Excel 開啟不亂碼
    df.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')

# 初始化 Session State
if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 2. 側邊欄設定 ---
st.sidebar.title("🏨 管理系統")
branch = st.sidebar.selectbox("切換分館", ["喜園館", "中華館", "長沙館"])
user_mode = st.sidebar.radio("類別", ["公版回覆", "個人常用"])

staff_name = ""
if user_mode == "個人常用":
    # 從資料庫提取已存在的員工姓名 (排除公版回覆)
    existing_staff = st.session_state.df[st.session_state.df['category'] != "公版回覆"]['category'].unique().tolist()
    
    # 預設至少有 Kuma
    if not existing_staff:
        existing_staff = ["Kuma"]
    
    # 下拉清單選項
    staff_options = sorted(existing_staff) + ["+ 新增員工"]
    selected_staff = st.sidebar.selectbox("選擇員工姓名", staff_options)
    
    if selected_staff == "+ 新增員工":
        new_staff_input = st.sidebar.text_input("請輸入新員工姓名", placeholder="例如: Amber")
        staff_name = new_staff_input if new_staff_input else "New Staff"
    else:
        staff_name = selected_staff

st.sidebar.divider()

# --- 3. 側邊欄：新增回覆模板功能 ---
with st.sidebar.expander("➕ 新增回覆模板"):
    new_title = st.text_input("模板標題", placeholder="例: 自助報到說明")
    new_note = st.text_input("小備註 (標籤)", placeholder="例: 2/11-2/22 過年加價")
    new_en = st.text_area("英文內容")
    new_tw = st.text_area("中文內容")
    
    target_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
    
    if st.button("確認儲存模板"):
        if new_title and (new_en or new_tw):
            new_row = {
                "branch": branch,
                "category": target_cat,
                "title": new_title,
                "content_en": new_en,
                "content_tw": new_tw,
                "note": new_note
            }
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(st.session_state.df)
            st.success(f"✅ 已存入 {target_cat}")
            st.rerun()
        else:
            st.error("標題與內容不能為空")

# --- 4. 主畫面：翻譯窗口 ---
st.title(f"💬 {branch} 客服小幫手")

st.subheader("🌐 即時翻譯中心 (外語 → 繁中)")
# 使用 text_input 達成按 Enter 即翻譯
source_text = st.text_input("貼上顧客訊息並按下 **Enter**：", placeholder="Type or paste text here...")

if source_text:
    try:
        with st.spinner('翻譯中...'):
            translated_res = GoogleTranslator(source='auto', target='zh-TW').translate(source_text)
            st.info(f"**【中文翻譯結果】**\n\n{translated_res}")
            if st.button("清除翻譯"):
                st.rerun()
    except Exception as e:
        st.error("翻譯連線失敗，請稍後再試。")
else:
    st.caption("等待輸入中... (支援自動語系偵測)")

st.divider()

# --- 5. 主畫面：模板庫 ---
st.subheader(f"📄 {user_mode}：{staff_name if user_mode=='個人常用' else ''}")
current_cat = "公版回覆" if user_mode == "公版回覆" else staff_name

# 篩選資料
mask = (st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat)
view_df = st.session_state.df[mask]

if view_df.empty:
    st.info(f"目前在「{branch} - {current_cat}」下沒有模板。")
else:
    for index, row in view_df.iterrows():
        # 佈局：標題區與刪除按鈕
        col_main, col_del = st.columns([0.93, 0.07])
        
        with col_main:
            # 標題加上備註標籤
            note_label = f" 🏷️ {row['note']}" if pd.notna(row['note']) and row['note'] != "" else ""
            with st.expander(f"📌 {row['title']} {note_label}"):
                if note_label:
                    st.warning(f"**💡 操作提示：** {row['note']}")
                
                # 中英對照窗口
                c_en, c_tw = st.columns(2)
                with c_en:
                    st.write("**🇺🇸 English**")
                    st.code(row['content_en'], language="text")
                with c_tw:
                    st.write("**🇹🇼 中文回覆**")
                    st.code(row['content_tw'], language="text")
        
        with col_del:
            # 刪除按鈕
            if st.button("🗑️", key=f"del_{index}", help="刪除此模板"):
                st.session_state.df = st.session_state.df.drop(index)
                save_data(st.session_state.df)
                st.rerun()

# 頁尾資訊
st.sidebar.divider()
st.sidebar.caption(f"數據庫總量: {len(st.session_state.df)} 筆")