import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from deep_translator import GoogleTranslator
from streamlit_sortables import sort_items

# --- 1. 初始化 Google Sheets ---
def init_gspread():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        info = dict(st.secrets["gcp_service_account"])
        if "private_key" in info:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(info, scopes=scope)
        client = gspread.authorize(creds)
        sh = client.open("InnHelperDB")
        return sh.get_worksheet(0)
    except Exception as e:
        st.error(f"❌ 連接失敗: {e}")
        st.stop()

worksheet = init_gspread()

def get_gs_data():
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    return df

def save_to_gs(df):
    try:
        df_clean = df.fillna("")
        data_to_save = [df_clean.columns.values.tolist()] + df_clean.values.tolist()
        worksheet.clear()
        worksheet.update(data_to_save)
        st.toast("🚀 雲端同步成功")
        return True
    except Exception as e:
        st.error(f"❌ 同步失敗: {e}")
        return False

# --- 2. 網頁配置 ---
st.set_page_config(page_title="旅館客服系統", layout="wide")

# CSS 修正：讓 code 區塊如果有捲軸時不要太醜，並限制 textarea 高度
st.markdown("""
    <style>
    code { white-space: pre-wrap !important; }
    /* 限制 code 區塊的最大高度，超過會出捲軸 */
    div[data-testid="stMarkdownContainer"] pre {
        max-height: 200px !important;
        overflow-y: auto !important;
    }
    </style>
""", unsafe_allow_html=True)

if 'df' not in st.session_state:
    st.session_state.df = get_gs_data()

# --- 3. 側邊欄 ---
branch = st.sidebar.selectbox("分館", ["喜園館", "中華館", "長沙館"])
user_mode = st.sidebar.radio("類別", ["公版回覆", "個人常用"])
is_admin = (st.sidebar.text_input("管理密碼", type="password") == "000000") if user_mode == "公版回覆" else True

# --- 4. 主畫面 ---
st.title(f"💬 {branch} 客服中心")
st.divider()

current_cat = "公版回覆" if user_mode == "公版回覆" else "Kuma"
view_df = st.session_state.df[(st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat)].copy()

if not view_df.empty:
    view_df['priority'] = pd.to_numeric(view_df['priority'], errors='coerce').fillna(999)
    view_df = view_df.sort_values("priority")

    for idx, row in view_df.iterrows():
        # 標題與備註
        note_display = f" ｜ 🏷️ {row['note']}" if row['note'] else ""
        header_text = f"📌 **{row['title']}** {note_display}"
        
        with st.expander(header_text):
            # 建立兩個小按鈕來切換顯示內容
            btn_col1, btn_col2 = st.columns(2)
            
            # 使用 session_state 來記錄目前這一個項目要顯示什麼
            show_key = f"show_{idx}"
            if show_key not in st.session_state:
                st.session_state[show_key] = None

            if btn_col1.button("👁️ 檢視英文", key=f"v_en_{idx}"):
                st.session_state[show_key] = "en"
            if btn_col2.button("👁️ 檢視中文", key=f"v_tw_{idx}"):
                st.session_state[show_key] = "tw"

            # 根據點擊顯示對應的內容框
            if st.session_state[show_key] == "en":
                st.caption("🇺🇸 English Content (可點擊右側複製)")
                st.code(row['content_en'], language="text")
            elif st.session_state[show_key] == "tw":
                st.caption("🇹🇼 中文內容 (可點擊右側複製)")
                st.code(row['content_tw'], language="text")
            
            # 管理按鈕（刪除）
            if is_admin:
                st.divider()
                if st.button("🗑️ 刪除此模板", key=f"del_{idx}"):
                    st.session_state.df = st.session_state.df.drop(idx)
                    save_to_gs(st.session_state.df)
                    st.rerun()