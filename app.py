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
        max-height: 180px !important; 
        overflow-y: auto !important;
        border: 1px solid #ddd !important;
        background-color: #f9f9f9 !important;
    }
    code { white-space: pre-wrap !important; word-break: break-word !important; }
    
    /* 自定義方框選擇器的樣式優化 (針對 st.pills 或 segmented_control) */
    .st-emotion-cache-12w0qpk { gap: 10px; } 
    </style>
""", unsafe_allow_html=True)

if 'df' not in st.session_state:
    st.session_state.df = get_gs_data()

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# --- 3. 頂部方框式 UI 選擇區 ---
st.title("🏨 旅館客服管理系統")

# 使用 st.pills (方框標籤式 UI) 取代下拉選單
col_ui1, col_ui2 = st.columns([0.5, 0.5])

with col_ui1:
    st.write("📍 **選擇分館**")
    branch = st.pills(
        "分館切換", 
        ["喜園館", "中華館", "長沙館"], 
        selection_mode="single", 
        default="喜園館",
        label_visibility="collapsed"
    )

with col_ui2:
    st.write("🔑 **切換模式**")
    user_mode = st.pills(
        "類別選擇", 
        ["公版回覆", "個人常用"], 
        selection_mode="single", 
        default="公版回覆",
        label_visibility="collapsed"
    )

st.divider()

# --- 4. 權限與管理邏輯 ---
is_admin = False
staff_name = "Kuma"
ADMIN_PASSWORD = "000000"

# 側邊欄改為放置管理功能
if user_mode == "公版回覆":
    if not st.session_state.authenticated:
        with st.sidebar:
            pwd = st.text_input("管理員密碼登入", type="password")
            if pwd == ADMIN_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            elif pwd != "":
                st.error("密碼錯誤")
    else:
        is_admin = True
        st.sidebar.success("✅ 已取得管理權限")
        if st.sidebar.button("登出管理模式"):
            st.session_state.authenticated = False
            st.rerun()
else:
    is_admin = True # 個人模式預設可編輯
    staff_list = sorted(st.session_state.df[st.session_state.df['category'] != "公版回覆"]['category'].unique().tolist())
    with st.sidebar:
        if staff_list:
            staff_name = st.selectbox("切換員工帳號", staff_list)
        else:
            staff_name = st.text_input("建立新帳號", value="Kuma")

# --- 5. 側邊欄：新增模板 & 排序 ---
if is_admin:
    with st.sidebar:
        st.divider()
        sort_mode = st.toggle("🔄 開啟排序模式")
        with st.expander("➕ 新增回覆模板", expanded=False):
            with st.form("add_form", clear_on_submit=True):
                n_t = st.text_input("模板標題")
                n_n = st.text_input("備註標籤")
                n_e = st.text_area("英文內容", height=150)
                n_w = st.text_area("中文內容", height=150)
                if st.form_submit_button("💾 儲存"):
                    if n_t:
                        target_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
                        new_id = int(pd.to_numeric(st.session_state.df['id']).max() + 1) if not st.session_state.df.empty else 1
                        new_row = pd.DataFrame([{"id": new_id, "branch": branch, "category": target_cat, "title": n_t, "content_en": n_e, "content_tw": n_w, "note": n_n, "priority": len(st.session_state.df)}])
                        st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                        save_to_gs(st.session_state.df)
                        st.rerun()

# --- 6. 主畫面：翻譯中心 ---
src_text = st.text_input("🌐 翻譯中心 (自動偵測 -> 繁中)：", placeholder="在此輸入客人的訊息...")
if src_text:
    translated = GoogleTranslator(source='auto', target='zh-TW').translate(src_text)
    st.code(translated, language="text")

st.divider()

# --- 7. 內容顯示 ---
current_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
view_df = st.session_state.df[(st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat)].copy()

if view_df.empty:
    st.info(f"目前【{branch} - {current_cat}】尚無資料。")
else:
    view_df['priority'] = pd.to_numeric(view_df['priority'], errors='coerce').fillna(999)
    view_df = view_df.sort_values("priority")

    if is_admin and sort_mode:
        titles = view_df['title'].tolist()
        sorted_titles = sort_items(titles, key="sort_list")
        if st.button("🚀 儲存新順序"):
            for i, t in enumerate(sorted_titles):
                mask = (st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat) & (st.session_state.df['title'] == t)
                st.session_state.df.loc[mask, 'priority'] = i
            save_to_gs(st.session_state.df)
            st.rerun()
    else:
        for idx, row in view_df.iterrows():
            col1, col2, col3 = st.columns([0.86, 0.07, 0.07])
            with col1:
                note_display = f" 🏷️ {row['note']}" if row['note'] else ""
                with st.expander(f"📌 **{row['title']}** {note_display}"):
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
                
                if st.session_state.get(f"edit_mode_{idx}", False):
                    with st.container(border=True):
                        et = st.text_input("編輯標題", row['title'], key=f"t_{idx}")
                        en = st.text_input("編輯標籤", row['note'], key=f"n_{idx}")
                        ee = st.text_area("編輯英文", row['content_en'], key=f"en_{idx}", height=200)
                        ew = st.text_area("編輯中文", row['content_tw'], key=f"tw_{idx}", height=200)
                        c1, c2 = st.columns(2)
                        if c1.button("💾 儲存", key=f"s_{idx}"):
                            st.session_state.df.at[idx, 'title'] = et
                            st.session_state.df.at[idx, 'note'] = en
                            st.session_state.df.at[idx, 'content_en'] = ee
                            st.session_state.df.at[idx, 'content_tw'] = ew
                            save_to_gs(st.session_state.df); st.session_state[f"edit_mode_{idx}"] = False; st.rerun()
                        if c2.button("✖️ 取消", key=f"c_{idx}"):
                            st.session_state[f"edit_mode_{idx}"] = False; st.rerun()