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
        SHEET_NAME = "InnHelperDB"
        sh = client.open(SHEET_NAME)
        return sh.get_worksheet(0)
    except Exception as e:
        st.error(f"❌ 無法連接至 Google Sheets: {e}")
        st.stop()

worksheet = init_gspread()

def get_gs_data():
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    cols = ["id", "branch", "category", "title", "content_en", "content_tw", "note", "priority"]
    for col in cols:
        if col not in df.columns:
            df[col] = ""
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

# --- 2. 網頁基礎配置 ---
st.set_page_config(page_title="旅館客服雲端系統", layout="wide")

# ✨ 重點 CSS：強制縮短 st.code 複製框的高度並加上滾動條
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; max-width: 100% !important; }
    .stExpander { width: 100% !important; }
    
    /* 針對 st.code 的容器進行限高 */
    div[data-testid="stMarkdownContainer"] pre {
        max-height: 180px !important; /* 固定高度，超過就滾動 */
        overflow-y: auto !important;
        border: 1px solid #ddd !important;
    }
    
    /* 確保複製按鈕位置正確 */
    div[data-testid="stCodeBlock"] button {
        background-color: rgba(255, 255, 255, 0.8) !important;
    }

    code { white-space: pre-wrap !important; word-break: break-word !important; }
    </style>
""", unsafe_allow_html=True)

if 'df' not in st.session_state:
    st.session_state.df = get_gs_data()

# --- 4. 側邊欄與翻譯中心 (自動偵測) ---
branch = st.sidebar.selectbox("切換分館", ["喜園館", "中華館", "長沙館"])
user_mode = st.sidebar.radio("類別選擇", ["公版回覆", "個人常用"])
is_admin = (st.sidebar.text_input("管理密碼", type="password") == "000000") if user_mode == "公版回覆" else True

st.title(f"💬 {branch} 客服中心")
src_text = st.text_input("🌐 各國語言翻譯 (自動偵測 -> 繁中)：", placeholder="請貼上客人的訊息...")
if src_text:
    translated = GoogleTranslator(source='auto', target='zh-TW').translate(src_text)
    st.info(f"**翻譯結果：**")
    st.code(translated, language="text") # 翻譯結果也使用帶有一鍵複製的框

st.divider()

# --- 5. 內容顯示 ---
current_cat = "公版回覆" if user_mode == "公版回覆" else "Kuma"
view_df = st.session_state.df[(st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat)].copy()

if not view_df.empty:
    view_df['priority'] = pd.to_numeric(view_df['priority'], errors='coerce').fillna(999)
    view_df = view_df.sort_values("priority")

    for idx, row in view_df.iterrows():
        col1, col2 = st.columns([0.95, 0.05])
        with col1:
            note_display = f" ｜ 🏷️ {row['note']}" if row['note'] else ""
            header_text = f"📌 **{row['title']}** {note_display}"
            
            with st.expander(header_text):
                # 直接使用原生的 st.code，它自帶一鍵複製按鈕
                # 搭配上方的 CSS，它會自動變成「固定高度 + 可滾動」
                st.write("**🇺🇸 English**")
                st.code(row['content_en'], language="text")
                
                st.write("**🇹🇼 中文**")
                st.code(row['content_tw'], language="text")
        
        if is_admin:
            with col2:
                if st.button("🗑️", key=f"del_{idx}"):
                    st.session_state.df = st.session_state.df.drop(idx)
                    save_to_gs(st.session_state.df)
                    st.rerun()