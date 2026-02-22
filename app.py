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
        st.toast("🚀 雲端同步成功！")
        return True
    except Exception as e:
        st.error(f"❌ 同步失敗: {e}")
        return False

# --- 2. 網頁基礎配置與 CSS ---
st.set_page_config(page_title="旅館客服管理系統", layout="wide")

st.markdown("""
    <style>
    /* 主容器 */
    .block-container { padding-top: 1.5rem; }
    
    /* 側邊欄拖拽項目樣式 */
    [data-testid="stSidebar"] div:has(.st-emotion-cache-1vt4581) { 
        width: 100% !important; 
    }
    .st-emotion-cache-1vt4581 {
        display: block !important;
        width: 100% !important;
        margin-bottom: 6px !important;
        padding: 10px !important;
        background-color: #ffffff !important;
        border: 1px solid #ddd !important;
        border-radius: 6px !important;
        font-size: 14px !important;
        color: #333 !important;
    }

    /* 程式碼區塊樣式 */
    div[data-testid="stMarkdownContainer"] pre {
        background-color: #f8f9fa !important;
        border-radius: 8px !important;
    }
    </style>
""", unsafe_allow_html=True)

if 'df' not in st.session_state:
    st.session_state.df = get_gs_data()
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# --- 3. 側邊欄：控制中心與工具 ---
with st.sidebar:
    st.header("🏨 系統控制台")
    
    # 分館與模式選擇
    branch = st.radio("📍 選擇分館", ["喜園館", "中華館", "長沙館"], index=0)
    user_mode = st.segmented_control("🔑 運作模式", ["公版回覆", "個人常用"], default="公版回覆")
    
    st.divider()

    # 🌐 翻譯中心 (移動至側邊欄)
    st.subheader("🌐 雙向翻譯中心")
    src_text = st.text_area("自動偵測語言：", placeholder="貼上英文則轉中文\n貼上中文則轉英文...", height=100)
    if src_text:
        # 簡單邏輯判斷：如果包含中文則翻譯成英文，否則翻譯成繁中
        is_chinese = any('\u4e00' <= char <= '\u9fff' for char in src_text)
        target_lang = 'en' if is_chinese else 'zh-TW'
        
        translated = GoogleTranslator(source='auto', target=target_lang).translate(src_text)
        st.success(f"**翻譯結果 ({target_lang})：**\n\n{translated}")
    
    st.divider()
    
    # 權限與管理功能
    is_admin = False
    staff_name = "Kuma"
    if user_mode == "公版回覆":
        if not st.session_state.authenticated:
            pwd = st.text_input("管理員密碼", type="password")
            if pwd == "000000":
                st.session_state.authenticated = True
                st.rerun()
        else:
            is_admin = True
            if st.button("🔓 登出管理員", use_container_width=True):
                st.session_state.authenticated = False
                st.rerun()
    else:
        is_admin = True
        staff_list = sorted(st.session_state.df[st.session_state.df['category'] != "公版回覆"]['category'].unique().tolist())
        staff_name = st.selectbox("帳號切換", staff_list) if staff_list else st.text_input("新帳號", value="Kuma")

    if is_admin:
        st.divider()
        sort_mode = st.toggle("↕️ 開啟拖拽排序")
        
        with st.expander("➕ 新增回覆模板"):
            with st.form("add_form", clear_on_submit=True):
                n_t = st.text_input("標題")
                n_n = st.text_input("備註")
                n_e = st.text_area("英文內容")
                n_w = st.text_area("中文內容")
                if st.form_submit_button("💾 儲存項目", use_container_width=True):
                    if n_t:
                        target_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
                        new_row = pd.DataFrame([{"id": 999, "branch": branch, "category": target_cat, "title": n_t, "content_en": n_e, "content_tw": n_w, "note": n_n, "priority": 999}])
                        st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                        save_to_gs(st.session_state.df)
                        st.rerun()

# --- 4. 主畫面：內容顯示 ---
st.title(f"旅館客服回覆系統 - {branch}")
st.caption(f"當前模式：{user_mode} ({'管理員已登入' if st.session_state.authenticated else '檢視模式'})")

current_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
view_df = st.session_state.df[(st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat)].copy()

if not view_df.empty:
    view_df['priority'] = pd.to_numeric(view_df['priority'], errors='coerce').fillna(999)
    view_df = view_df.sort_values("priority")

    # ↕️ 側邊欄拖拽排序邏輯
    if is_admin and sort_mode:
        with st.sidebar:
            st.subheader("↕️ 拖拽調整順序")
            titles = view_df['title'].tolist()
            sorted_titles = sort_items(titles, key="drag_sort_list")
            if st.button("💾 儲存順序", use_container_width=True, type="primary"):
                for i, t in enumerate(sorted_titles):
                    st.session_state.df.loc[(st.session_state.df['title'] == t) & 
                                            (st.session_state.df['branch'] == branch) & 
                                            (st.session_state.df['category'] == current_cat), 'priority'] = i
                save_to_gs(st.session_state.df)
                st.rerun()

    # 清單內容
    for idx, row in view_df.iterrows():
        col_main, col_edit, col_del = st.columns([0.88, 0.06, 0.06])
        
        with col_main:
            title_text = f"📌 **{row['title']}**"
            if row['note']: title_text += f" ｜ 🏷️ {row['note']}"
            with st.expander(title_text):
                st.caption("🇺🇸 English")
                st.code(row['content_en'], language="text")
                st.caption("🇹🇼 中文")
                st.code(row['content_tw'], language="text")
        
        if is_admin:
            with col_edit:
                if st.button("✏️", key=f"ed_{idx}"):
                    st.session_state[f"edit_mode_{idx}"] = not st.session_state.get(f"edit_mode_{idx}", False)
                    st.rerun()
            with col_del:
                if st.button("🗑️", key=f"de_{idx}"):
                    st.session_state.df = st.session_state.df.drop(idx)
                    save_to_gs(st.session_state.df)
                    st.rerun()
        
        if st.session_state.get(f"edit_mode_{idx}", False):
            with st.container(border=True):
                st.write(f"🔧 **編輯：{row['title']}**")
                ec1, ec2 = st.columns(2)
                with ec1: et = st.text_input("標題", row['title'], key=f"t_{idx}")
                with ec2: en = st.text_input("備註", row['note'], key=f"n_{idx}")
                ee = st.text_area("英文內容", row['content_en'], key=f"ee_{idx}", height=120)
                ew = st.text_area("中文內容", row['content_tw'], key=f"ew_{idx}", height=120)
                
                eb1, eb2 = st.columns(2)
                if eb1.button("💾 確認更新", key=f"save_{idx}", use_container_width=True):
                    st.session_state.df.loc[idx, ['title','note','content_en','content_tw']] = [et, en, ee, ew]
                    save_to_gs(st.session_state.df)
                    st.session_state[f"edit_mode_{idx}"] = False
                    st.rerun()
                if eb2.button("✖️ 取消", key=f"cancel_{idx}", use_container_width=True):
                    st.session_state[f"edit_mode_{idx}"] = False
                    st.rerun()
else:
    st.info("💡 目前尚無資料。")