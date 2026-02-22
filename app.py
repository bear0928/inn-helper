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
        st.error(f"❌ 無法連接至 Google Sheets: {e}")
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
        st.toast("🚀 雲端資料同步成功！")
        return True
    except Exception as e:
        st.error(f"❌ 同步失敗: {e}")
        return False

# --- 2. 網頁配置與 CSS ---
st.set_page_config(page_title="旅館客服雲端系統", layout="wide")

st.markdown("""
    <style>
    /* 強制縮小中英按鈕的欄位寬度 */
    [data-testid="column"]:nth-of-type(1), 
    [data-testid="column"]:nth-of-type(2) {
        flex: 0 0 45px !important;
        min-width: 45px !important;
    }
    /* 讓按鈕高度一致 */
    div.stButton > button {
        width: 100% !important;
        height: 38px !important;
        padding: 0px !important;
        font-weight: bold;
    }
    /* 讓 code 複製區塊更緊湊 */
    .stCodeBlock { margin-top: -10px; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. 資料讀取 ---
if 'df' not in st.session_state:
    st.session_state.df = get_gs_data()

# --- 4. 側邊欄 ---
st.sidebar.title("🏨 旅館管理")
branch = st.sidebar.selectbox("分館", ["喜園館", "中華館", "長沙館"])
user_mode = st.sidebar.radio("類別", ["公版回覆", "個人常用"])

# 簡化密碼與身分判定
ADMIN_PASSWORD = "000000"
is_admin = False
staff_name = "Kuma"
if user_mode == "公版回覆":
    if st.sidebar.text_input("管理密碼", type="password") == ADMIN_PASSWORD:
        is_admin = True
else:
    is_admin = True
    staff_name = st.sidebar.text_input("員工帳號", value="Kuma")

# --- 5. 主畫面 ---
st.title(f"💬 {branch} 客服中心")
st.divider()

# --- 6. 內容顯示核心邏輯 ---
current_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
view_df = st.session_state.df[(st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat)].copy()

if view_df.empty:
    st.info("尚無資料")
else:
    # 確保優先級排序
    view_df['priority'] = pd.to_numeric(view_df['priority'], errors='coerce').fillna(0)
    view_df = view_df.sort_values("priority")

    for idx, row in view_df.iterrows():
        # 版面配置：中 | 英 | 標題展開 | 管理
        c_zh, c_en, c_main, c_admin = st.columns([0.05, 0.05, 0.8, 0.1])
        
        # 點擊「中」或「英」按鈕
        with c_zh:
            if st.button("中", key=f"z_{idx}"):
                st.session_state[f"copy_box_{idx}"] = ("🇹🇼 中文內容", row['content_tw'])
        with c_en:
            if st.button("英", key=f"e_{idx}"):
                st.session_state[f"copy_box_{idx}"] = ("🇺🇸 英文內容", row['content_en'])

        with c_main:
            note_txt = f" ｜ 🏷️ {row['note']}" if row['note'] else ""
            with st.expander(f"📌 **{row['title']}** {note_txt}"):
                st.write("**Full English:**")
                st.code(row['content_en'], language="text")
                st.write("**完整中文：**")
                st.code(row['content_tw'], language="text")
        
        if is_admin:
            with c_admin:
                if st.button("🗑️", key=f"del_{idx}"):
                    st.session_state.df = st.session_state.df.drop(idx)
                    save_to_gs(st.session_state.df)
                    st.rerun()

        # --- 關鍵修正：點擊按鈕後，在該列下方顯現複製區塊 ---
        if f"copy_box_{idx}" in st.session_state:
            label, content = st.session_state[f"copy_box_{idx}"]
            # 建立一個醒目的複製區域
            with st.container(border=True):
                col_txt, col_close = st.columns([0.9, 0.1])
                col_txt.caption(f"{label} (點擊右側圖示複製)")
                if col_close.button("✖️", key=f"close_{idx}"):
                    del st.session_state[f"copy_box_{idx}"]
                    st.rerun()
                st.code(content, language="text") # 這裡的 st.code 帶有 100% 成功的複製按鈕