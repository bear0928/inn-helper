import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from deep_translator import GoogleTranslator

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

# --- 2. 網頁配置與 CSS 優化 ---
st.set_page_config(page_title="旅館客服系統", layout="wide")

st.markdown("""
    <style>
    /* 讓 code 顯示框變得很短且有捲軸 */
    div[data-testid="stMarkdownContainer"] pre {
        max-height: 120px !important; /* 限制高度在約三行字左右 */
        overflow-y: auto !important;
        background-color: #f8f9fa;
        border: 1px solid #ddd;
    }
    code { white-space: pre-wrap !important; }
    
    /* 讓檢視按鈕更醒目 */
    div.stButton > button {
        border-radius: 20px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

if 'df' not in st.session_state:
    st.session_state.df = get_gs_data()

# --- 3. 側邊欄 ---
st.sidebar.title("🏨 旅館管理")
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
        note_display = f" ｜ 🏷️ {row['note']}" if row['note'] else ""
        header_text = f"📌 **{row['title']}** {note_display}"
        
        with st.expander(header_text):
            # 檢視按鈕：點擊後會顯示內容框
            btn_col1, btn_col2 = st.columns(2)
            
            show_key = f"view_content_{idx}"
            if show_key not in st.session_state:
                st.session_state[show_key] = None

            if btn_col1.button("👁️ 檢視英文內容", key=f"v_en_{idx}"):
                st.session_state[show_key] = ("🇺🇸 英文已就緒", row['content_en'])
                st.toast("請點擊下方框框右上角圖示進行複製")

            if btn_col2.button("👁️ 檢視中文內容", key=f"v_tw_{idx}"):
                st.session_state[show_key] = ("🇹🇼 中文已就緒", row['content_tw'])
                st.toast("請點擊下方框框右上角圖示進行複製")

            # 顯示短小的檢視複製框
            if st.session_state[show_key] is not None:
                label, content = st.session_state[show_key]
                st.info(f"**{label}**")
                # 此 code 區塊受 CSS 限制，高度僅 120px，且內建複製按鈕
                st.code(content, language="text")
                
                if st.button("✖️ 關閉內容", key=f"close_{idx}"):
                    st.session_state[show_key] = None
                    st.rerun()
            
            # 管理按鈕
            if is_admin:
                st.divider()
                if st.button("🗑️ 刪除", key=f"del_{idx}"):
                    st.session_state.df = st.session_state.df.drop(idx)
                    save_to_gs(st.session_state.df)
                    st.rerun()