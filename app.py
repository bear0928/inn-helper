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

# CSS 強化：優化按鈕寬度，解決手機版擠壓問題
st.markdown("""
    <style>
    code { white-space: pre-wrap !important; word-break: break-word !important; }
    
    /* 讓中英按鈕欄位縮到最小 */
    div[data-testid="column"]:nth-of-type(1), 
    div[data-testid="column"]:nth-of-type(2) {
        flex: 0 0 45px !important;
        min-width: 45px !important;
    }
    
    /* 按鈕樣式：高度與標題列齊平 */
    div.stButton > button {
        width: 100% !important;
        padding: 0px !important;
        height: 38px !important;
        border-radius: 4px;
        font-weight: bold;
        border: 1px solid #ddd;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. 複製功能函式 (純文字傳輸) ---
def copy_to_clipboard(text, label):
    # 使用 st.code 的內建點擊複製按鈕作為備案，或是直接顯示在文字框供長按
    st.session_state.clipboard = text
    st.toast(f"✅ 已準備好{label}內容，請長按下方文字框複製 (或部分設備已自動完成)")

# --- 4. 側邊欄邏輯 ---
ADMIN_PASSWORD = "000000"
if 'df' not in st.session_state:
    st.session_state.df = get_gs_data()

st.sidebar.title("🏨 旅館管理 (Cloud)")
branch = st.sidebar.selectbox("切換分館", ["喜園館", "中華館", "長沙館"])
user_mode = st.sidebar.radio("類別選擇", ["公版回覆", "個人常用"])

is_admin = False
staff_name = "Kuma"

if user_mode == "公版回覆":
    if st.sidebar.text_input("管理密碼", type="password") == ADMIN_PASSWORD:
        is_admin = True
else:
    is_admin = True
    staff_list = sorted(st.session_state.df[st.session_state.df['category'] != "公版回覆"]['category'].unique().tolist())
    staff_name = st.sidebar.selectbox("員工帳號", staff_list) if staff_list else st.sidebar.text_input("輸入新員工姓名", value="Kuma")

# --- 5. 主畫面 ---
st.title(f"💬 {branch} 客服中心")
src_text = st.text_input("🌐 快速翻譯：")
if src_text:
    res = GoogleTranslator(source='auto', target='zh-TW').translate(src_text)
    st.info(f"**翻譯：** {res}")

st.divider()

# --- 6. 內容顯示 ---
current_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
view_df = st.session_state.df[(st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat)].copy()

if view_df.empty:
    st.info("尚無模板資料。")
else:
    view_df['priority'] = pd.to_numeric(view_df['priority'], errors='coerce').fillna(999)
    view_df = view_df.sort_values("priority")

    for idx, row in view_df.iterrows():
        # ✨ 固定寬度欄位佈局
        col_zh, col_en, col_main, col_edit = st.columns([0.05, 0.05, 0.8, 0.1])
        
        with col_zh:
            if st.button("中", key=f"btn_zh_{idx}"):
                # 使用最穩定的方式：在上方顯示一個可點擊複製的區塊
                st.session_state[f"temp_copy_{idx}"] = row["content_tw"]
                st.toast("已讀取中文內容")

        with col_en:
            if st.button("英", key=f"btn_en_{idx}"):
                st.session_state[f"temp_copy_{idx}"] = row["content_en"]
                st.toast("已讀取英文內容")

        with col_main:
            note_display = f" ｜ 🏷️ {row['note']}" if row['note'] else ""
            header_text = f"📌 **{row['title']}** {note_display}"
            with st.expander(header_text):
                # 如果使用者有點擊中/英按鈕，就在這裡顯示一個方便一鍵複製的 code 區塊
                if f"temp_copy_{idx}" in st.session_state:
                    st.success("👇 請點擊下方右側圖示快速複製")
                    st.code(st.session_state[f"temp_copy_{idx}"], language="text")
                    if st.button("關閉複製框", key=f"close_{idx}"):
                        del st.session_state[f"temp_copy_{idx}"]
                        st.rerun()
                
                st.write("**🇺🇸 English**")
                st.code(row['content_en'], language="text")
                st.write("**🇹🇼 中文**")
                st.code(row['content_tw'], language="text")
        
        # 管理功能 (編輯/刪除)
        if is_admin:
            with col_edit:
                c1, c2 = st.columns(2)
                if c1.button("✏️", key=f"ed_{idx}"):
                    st.session_state[f"edit_{idx}"] = True
                if c2.button("🗑️", key=f"de_{idx}"):
                    st.session_state.df = st.session_state.df.drop(idx)
                    save_to_gs(st.session_state.df)
                    st.rerun()