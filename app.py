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
    # 核心欄位，移除 color
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

# --- 2. 網頁基礎配置與核心 CSS ---
st.set_page_config(page_title="旅館客服雲端系統", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; max-width: 100% !important; }
    
    /* 模式 A：方框按鈕樣式 */
    div.stButton > button {
        width: 100% !important;
        height: 110px !important;
        border-radius: 12px !important;
        font-size: 18px !important;
        font-weight: bold !important;
        background-color: white !important;
        color: #31333F !important;
        border: 1px solid #ddd !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        white-space: normal !important;
        word-wrap: break-word !important;
        box-shadow: 2px 2px 6px rgba(0,0,0,0.05) !important;
        transition: all 0.1s !important;
    }

    div.stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 4px 4px 10px rgba(0,0,0,0.1) !important;
        border-color: #ff4b4b !important;
    }

    /* 強制排序模式下的項目佔滿全寬 */
    div[data-testid="stVerticalBlock"] > div:has(.st-emotion-cache-1vt4581) { 
        width: 100% !important; 
    }
    .st-emotion-cache-1vt4581 {
        display: block !important;
        width: 100% !important;
        margin-bottom: 10px !important;
        padding: 15px !important;
        text-align: left !important;
        font-size: 16px !important;
        background-color: #f8f9fa !important;
        border-radius: 8px !important;
        border: 1px solid #eee !important;
    }
    
    div[data-testid="stMarkdownContainer"] pre {
        max-height: 200px !important;
        overflow-y: auto !important;
        border: 1px solid #eee !important;
    }
    </style>
""", unsafe_allow_html=True)

if 'df' not in st.session_state:
    st.session_state.df = get_gs_data()
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# --- 3. 頂部選擇區 ---
st.title("🏨 旅館客服管理系統")
c_ui1, c_ui2, c_ui3 = st.columns([0.35, 0.35, 0.3])
with c_ui1:
    branch = st.pills("📍 分館", ["喜園館", "中華館", "長沙館"], default="喜園館")
with c_ui2:
    user_mode = st.pills("🔑 模式", ["公版回覆", "個人常用"], default="公版回覆")
with c_ui3:
    ui_style = st.toggle("🔲 方框大格模式", value=True)

st.divider()

# --- 4. 權限管理 ---
is_admin = False
staff_name = "Kuma"
if user_mode == "公版回覆":
    if not st.session_state.authenticated:
        with st.sidebar:
            pwd = st.text_input("管理員密碼", type="password")
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

# --- 5. 側邊欄：新增模板 ---
if is_admin:
    with st.sidebar:
        st.divider()
        sort_mode = st.toggle("↕️ 開啟拖拽排序模式")
        with st.expander("➕ 新增回覆模板"):
            with st.form("add_form", clear_on_submit=True):
                n_t = st.text_input("標題")
                n_n = st.text_input("備註")
                n_e = st.text_area("英文內容", height=100)
                n_w = st.text_area("中文內容", height=100)
                if st.form_submit_button("💾 儲存"):
                    if n_t:
                        target_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
                        new_row = pd.DataFrame([{"id": 999, "branch": branch, "category": target_cat, "title": n_t, "content_en": n_e, "content_tw": n_w, "note": n_n, "priority": 999}])
                        st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                        save_to_gs(st.session_state.df)
                        st.rerun()

# --- 6. 翻譯中心 ---
src_text = st.text_input("🌐 翻譯中心 (自動偵測 -> 繁中)：", placeholder="在此貼上訊息...")
if src_text:
    translated = GoogleTranslator(source='auto', target='zh-TW').translate(src_text)
    st.code(translated, language="text")

st.divider()

# --- 7. 內容顯示與拖拽排序 ---
current_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
view_df = st.session_state.df[(st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat)].copy()

if not view_df.empty:
    view_df['priority'] = pd.to_numeric(view_df['priority'], errors='coerce').fillna(999)
    view_df = view_df.sort_values("priority")

    # ↕️ 拖拽排序模式 (佔滿全寬列表)
    if is_admin and sort_mode:
        st.info("💡 請直接「上下拖拽」標籤來調整順序，完成後點擊下方儲存。")
        titles = view_df['title'].tolist()
        sorted_titles = sort_items(titles, key="drag_sort_list")
        
        st.markdown("---")
        if st.button("💾 儲存全新排序順序", use_container_width=True, type="primary"):
            for i, t in enumerate(sorted_titles):
                st.session_state.df.loc[(st.session_state.df['title'] == t) & 
                                        (st.session_state.df['branch'] == branch) & 
                                        (st.session_state.df['category'] == current_cat), 'priority'] = i
            save_to_gs(st.session_state.df)
            st.rerun()
    
    # 🔲 模式 A：方框大格模式
    elif ui_style:
        items = list(view_df.iterrows())
        for row_idx in range(0, len(items), 4):
            cols = st.columns(4)
            row_items = items[row_idx:row_idx+4]
            for col_idx, (idx, row) in enumerate(row_items):
                with cols[col_idx]:
                    if st.button(f"{row['title']}", key=f"btn_{idx}"):
                        st.session_state[f"show_{idx}"] = not st.session_state.get(f"show_{idx}", False)
                    
                    if st.session_state.get(f"show_{idx}", False):
                        if not st.session_state.get(f"edit_{idx}", False):
                            with st.container(border=True):
                                if row['note']: st.caption(f"🏷️ {row['note']}")
                                st.code(row['content_en'], language="text")
                                st.code(row['content_tw'], language="text")
                                if is_admin:
                                    c1, c2 = st.columns(2)
                                    if c1.button("✏️", key=f"e_v_{idx}"): st.session_state[f"edit_{idx}"] = True; st.rerun()
                                    if c2.button("🗑️", key=f"d_v_{idx}"): 
                                        st.session_state.df = st.session_state.df.drop(idx); save_to_gs(st.session_state.df); st.rerun()
                        else:
                            # 方框正下方的編輯區
                            with st.container(border=True):
                                et = st.text_input("標題", row['title'], key=f"t_{idx}")
                                en = st.text_input("備註", row['note'], key=f"n_{idx}")
                                ee = st.text_area("英文", row['content_en'], key=f"ee_{idx}", height=120)
                                ew = st.text_area("中文", row['content_tw'], key=f"ew_{idx}", height=120)
                                b1, b2 = st.columns(2)
                                if b1.button("💾 儲存", key=f"s_{idx}"):
                                    st.session_state.df.loc[idx, ['title','note','content_en','content_tw']] = [et, en, ee, ew]
                                    save_to_gs(st.session_state.df)
                                    st.session_state[f"edit_{idx}"] = False; st.rerun()
                                if b2.button("✖️ 取消", key=f"c_{idx}"):
                                    st.session_state[f"edit_{idx}"] = False; st.rerun()

    # 📜 模式 B：清單模式 (下拉 Expand)
    else:
        for idx, row in view_df.iterrows():
            col_l1, col_l2, col_l3 = st.columns([0.86, 0.07, 0.07])
            with col_l1:
                with st.expander(f"📌 **{row['title']}** {' ｜ 🏷️ '+row['note'] if row['note'] else ''}"):
                    st.code(row['content_en'], language="text")
                    st.code(row['content_tw'], language="text")
            if is_admin:
                with col_l2:
                    if st.button("✏️", key=f"ed_l_{idx}"): st.session_state[f"edit_{idx}"] = True; st.rerun()
                with col_l3:
                    if st.button("🗑️", key=f"de_l_{idx}"): 
                        st.session_state.df = st.session_state.df.drop(idx); save_to_gs(st.session_state.df); st.rerun()
            
            # 清單正下方的編輯區
            if st.session_state.get(f"edit_{idx}", False):
                with st.container(border=True):
                    st.markdown(f"🛠️ **正在編輯：{row['title']}**")
                    c1, c2 = st.columns(2)
                    with c1: et = st.text_input("修改標題", row['title'], key=f"lt_{idx}")
                    with c2: en = st.text_input("修改備註", row['note'], key=f"ln_{idx}")
                    ee = st.text_area("編輯英文", row['content_en'], key=f"lee_{idx}", height=150)
                    ew = st.text_area("編輯中文", row['content_tw'], key=f"lew_{idx}", height=150)
                    b1, b2 = st.columns(2)
                    if b1.button("💾 儲存修改", key=f"ls_{idx}"):
                        st.session_state.df.loc[idx, ['title','note','content_en','content_tw']] = [et, en, ee, ew]
                        save_to_gs(st.session_state.df)
                        st.session_state[f"edit_{idx}"] = False; st.rerun()
                    if b2.button("✖️ 取消", key=f"lc_{idx}"):
                        st.session_state[f"edit_{idx}"] = False; st.rerun()