import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from deep_translator import GoogleTranslator
from streamlit_sortables import sort_items

# --- 1. 初始化 Google Sheets (整合自動修復邏輯) ---
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

st.markdown("""
    <style>
    code { white-space: pre-wrap !important; word-break: break-word !important; }
    textarea { font-family: sans-serif !important; }
    /* 讓內部的摘要文字顏色淺一點 */
    .preview-text { color: #666; font-size: 0.85rem; margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "000000"

if 'df' not in st.session_state:
    st.session_state.df = get_gs_data()

# --- 4. 側邊欄邏輯 ---
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
    staff_name = st.sidebar.selectbox("員工帳號", staff_list) if staff_list else st.sidebar.text_input("帳號", value="Kuma")

# --- 5. 新增模板 ---
if is_admin:
    st.sidebar.divider()
    with st.sidebar.expander("➕ 新增回覆模板"):
        with st.form("add_form", clear_on_submit=True):
            n_t = st.text_input("模板標題")
            n_n = st.text_input("備註標籤")
            n_e = st.text_area("英文內容")
            n_w = st.text_area("中文內容")
            if st.form_submit_button("💾 儲存"):
                if n_t:
                    target_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
                    new_row = pd.DataFrame([{"id": 99, "branch": branch, "category": target_cat, "title": n_t, "content_en": n_e, "content_tw": n_w, "note": n_n, "priority": len(st.session_state.df)}])
                    st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                    save_to_gs(st.session_state.df)
                    st.rerun()

# --- 6. 主畫面 ---
st.title(f"💬 {branch} 客服中心")
st.divider()

current_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
view_df = st.session_state.df[(st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat)].copy()

if not view_df.empty:
    view_df['priority'] = pd.to_numeric(view_df['priority'], errors='coerce').fillna(999)
    view_df = view_df.sort_values("priority")

    for idx, row in view_df.iterrows():
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            note_display = f" ｜ 🏷️ {row['note']}" if row['note'] else ""
            header_text = f"📌 **{row['title']}** {note_display}"
            
            with st.expander(header_text):
                # --- 修正處：將內容縮短檢視 ---
                # 英文部分
                en_preview = (row['content_en'][:40] + '...') if len(row['content_en']) > 40 else row['content_en']
                st.markdown(f"**🇺🇸 English Preview:** `{en_preview}`")
                with st.expander("展開完整英文內容"):
                    st.code(row['content_en'], language="text")
                
                st.write("") # 間隔
                
                # 中文部分
                tw_preview = (row['content_tw'][:40] + '...') if len(row['content_tw']) > 40 else row['content_tw']
                st.markdown(f"**🇹🇼 中文預覽:** `{tw_preview}`")
                with st.expander("展開完整中文內容"):
                    st.code(row['content_tw'], language="text")
        
        if is_admin:
            with col2:
                if st.button("🗑️", key=f"del_{idx}"):
                    st.session_state.df = st.session_state.df.drop(idx)
                    save_to_gs(st.session_state.df)
                    st.rerun()