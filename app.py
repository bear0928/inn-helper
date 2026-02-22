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

# --- 2. 網頁基礎配置與 CSS ---
st.set_page_config(page_title="旅館客服雲端系統", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; max-width: 100% !important; }
    .stExpander { width: 100% !important; }
    
    /* 限制 st.code 高度並允許滾動 */
    div[data-testid="stMarkdownContainer"] pre {
        max-height: 200px !important; 
        overflow-y: auto !important;
        border: 1px solid #ddd !important;
        background-color: #f9f9f9 !important;
    }
    code { white-space: pre-wrap !important; word-break: break-word !important; }
    
    /* 方框 UI 的按鈕樣式 */
    div.stButton > button {
        width: 100%;
        height: 80px;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        background-color: white;
        transition: all 0.2s;
        font-size: 18px !important;
        font-weight: 600 !important;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    div.stButton > button:hover {
        border-color: #ff4b4b;
        color: #ff4b4b;
        background-color: #fffafa;
    }
    </style>
""", unsafe_allow_html=True)

if 'df' not in st.session_state:
    st.session_state.df = get_gs_data()

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# --- 3. 頂部選擇區 ---
st.title("🏨 旅館客服管理系統")

col_ui1, col_ui2, col_ui3 = st.columns([0.35, 0.35, 0.3])

with col_ui1:
    branch = st.pills("📍 分館", ["喜園館", "中華館", "長沙館"], default="喜園館")

with col_ui2:
    user_mode = st.pills("🔑 模式", ["公版回覆", "個人常用"], default="公版回覆")

with col_ui3:
    # 這裡就是切換開關
    ui_style = st.toggle("🔲 方框模式", value=False, help="開啟後將以大按鈕形式顯示模板，點擊即展開")

st.divider()

# --- 4. 權限邏輯 ---
is_admin = False
staff_name = "Kuma"
if user_mode == "公版回覆":
    if not st.session_state.authenticated:
        with st.sidebar:
            pwd = st.text_input("管理密碼", type="password")
            if pwd == "000000":
                st.session_state.authenticated = True
                st.rerun()
    else:
        is_admin = True
        st.sidebar.button("🔓 登出管理員", on_click=lambda: st.session_state.update({"authenticated": False}))
else:
    is_admin = True
    staff_list = sorted(st.session_state.df[st.session_state.df['category'] != "公版回覆"]['category'].unique().tolist())
    staff_name = st.sidebar.selectbox("員工帳號", staff_list) if staff_list else st.sidebar.text_input("新帳號", value="Kuma")

# --- 5. 側邊欄功能 ---
if is_admin:
    with st.sidebar:
        st.divider()
        sort_mode = st.toggle("🔄 排序模式")
        with st.expander("➕ 新增模板"):
            with st.form("add_form", clear_on_submit=True):
                n_t = st.text_input("標題")
                n_n = st.text_input("備註")
                n_e = st.text_area("英文", height=100)
                n_w = st.text_area("中文", height=100)
                if st.form_submit_button("儲存"):
                    if n_t:
                        target_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
                        new_row = pd.DataFrame([{"id": 999, "branch": branch, "category": target_cat, "title": n_t, "content_en": n_e, "content_tw": n_w, "note": n_n, "priority": 999}])
                        st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                        save_to_gs(st.session_state.df); st.rerun()

# --- 6. 翻譯中心 ---
src_text = st.text_input("🌐 翻譯中心：", placeholder="輸入客人訊息...")
if src_text:
    translated = GoogleTranslator(source='auto', target='zh-TW').translate(src_text)
    st.code(translated, language="text")

st.divider()

# --- 7. 模板顯示邏輯 ---
current_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
view_df = st.session_state.df[(st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat)].copy()

if not view_df.empty:
    view_df['priority'] = pd.to_numeric(view_df['priority'], errors='coerce').fillna(999)
    view_df = view_df.sort_values("priority")

    if is_admin and sort_mode:
        titles = view_df['title'].tolist()
        sorted_titles = sort_items(titles, key="sort_list")
        if st.button("🚀 儲存新順序"):
            for i, t in enumerate(sorted_titles):
                st.session_state.df.loc[st.session_state.df['title'] == t, 'priority'] = i
            save_to_gs(st.session_state.df); st.rerun()
    
    # 🔲 方框模式 UI
    elif ui_style:
        cols = st.columns(3) # 設定一行三個方框
        for i, (idx, row) in enumerate(view_df.iterrows()):
            with cols[i % 3]:
                # 點擊按鈕後將該 ID 存入 Session 以顯示詳情
                if st.button(f"📌 {row['title']}\n{row['note'][:10]}...", key=f"box_{idx}"):
                    st.session_state[f"show_detail_{idx}"] = not st.session_state.get(f"show_detail_{idx}", False)
                
                if st.session_state.get(f"show_detail_{idx}", False):
                    with st.container(border=True):
                        st.code(row['content_en'], language="text")
                        st.code(row['content_tw'], language="text")
                        if is_admin:
                            c1, c2 = st.columns(2)
                            if c1.button("✏️", key=f"ed_v_{idx}"): st.session_state[f"edit_mode_{idx}"] = True
                            if c2.button("🗑️", key=f"de_v_{idx}"):
                                st.session_state.df = st.session_state.df.drop(idx)
                                save_to_gs(st.session_state.df); st.rerun()

    # 📜 清單模式 UI (原本的樣子)
    else:
        for idx, row in view_df.iterrows():
            col1, col2, col3 = st.columns([0.86, 0.07, 0.07])
            with col1:
                with st.expander(f"📌 **{row['title']}** ｜ 🏷️ {row['note']}"):
                    st.write("**🇺🇸 English**")
                    st.code(row['content_en'], language="text")
                    st.write("**🇹🇼 中文**")
                    st.code(row['content_tw'], language="text")
            if is_admin:
                with col2:
                    if st.button("✏️", key=f"ed_{idx}"): st.session_state[f"edit_mode_{idx}"] = True
                with col3:
                    if st.button("🗑️", key=f"de_{idx}"):
                        st.session_state.df = st.session_state.df.drop(idx)
                        save_to_gs(st.session_state.df); st.rerun()

            # 編輯邏輯 (共用)
            if st.session_state.get(f"edit_mode_{idx}", False):
                with st.container(border=True):
                    et = st.text_input("修改標題", row['title'], key=f"t_{idx}")
                    en = st.text_input("修改標籤", row['note'], key=f"n_{idx}")
                    ee = st.text_area("編輯英文", row['content_en'], key=f"en_{idx}", height=150)
                    ew = st.text_area("編輯中文", row['content_tw'], key=f"tw_{idx}", height=150)
                    c1, c2 = st.columns(2)
                    if c1.button("💾 儲存修改", key=f"s_{idx}"):
                        st.session_state.df.at[idx, 'title'] = et
                        st.session_state.df.at[idx, 'note'] = en
                        st.session_state.df.at[idx, 'content_en'] = ee
                        st.session_state.df.at[idx, 'content_tw'] = ew
                        save_to_gs(st.session_state.df); st.session_state[f"edit_mode_{idx}"] = False; st.rerun()
                    if c2.button("✖️ 取消", key=f"c_{idx}"):
                        st.session_state[f"edit_mode_{idx}"] = False; st.rerun()