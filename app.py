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
st.set_page_config(page_title="旅館客服雲端系統", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; max-width: 100% !important; }
    
    /* 拖拽排序項目全寬樣式 */
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
        border: 1px solid #ddd !important;
        cursor: grab;
    }

    /* 程式碼區塊高度限制 */
    div[data-testid="stMarkdownContainer"] pre {
        max-height: 250px !important;
        overflow-y: auto !important;
    }
    </style>
""", unsafe_allow_html=True)

if 'df' not in st.session_state:
    st.session_state.df = get_gs_data()
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# --- 3. 頂部選擇區 ---
st.title("🏨 旅館客服管理系統")
c_ui1, c_ui2 = st.columns([0.5, 0.5])
with c_ui1:
    branch = st.pills("📍 分館", ["喜園館", "中華館", "長沙館"], default="喜園館")
with c_ui2:
    user_mode = st.pills("🔑 模式", ["公版回覆", "個人常用"], default="公版回覆")

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

# --- 5. 側邊欄：功能選單 ---
if is_admin:
    with st.sidebar:
        st.divider()
        sort_mode = st.toggle("↕️ 開啟拖拽排序模式")
        with st.expander("➕ 新增回覆模板"):
            with st.form("add_form", clear_on_submit=True):
                n_t = st.text_input("標題")
                n_n = st.text_input("備註")
                n_e = st.text_area("英文內容")
                n_w = st.text_area("中文內容")
                if st.form_submit_button("💾 儲存項目"):
                    if n_t:
                        target_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
                        new_row = pd.DataFrame([{"id": 999, "branch": branch, "category": target_cat, "title": n_t, "content_en": n_e, "content_tw": n_w, "note": n_n, "priority": 999}])
                        st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                        save_to_gs(st.session_state.df)
                        st.rerun()

# --- 6. 翻譯中心 ---
src_text = st.text_input("🌐 翻譯中心 (自動偵測 → 繁中)：", placeholder="在此貼上客人訊息...")
if src_text:
    translated = GoogleTranslator(source='auto', target='zh-TW').translate(src_text)
    st.info(f"翻譯結果：\n\n{translated}")

st.divider()

# --- 7. 主內容區：清單顯示與操作 ---
current_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
view_df = st.session_state.df[(st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat)].copy()

if not view_df.empty:
    view_df['priority'] = pd.to_numeric(view_df['priority'], errors='coerce').fillna(999)
    view_df = view_df.sort_values("priority")

    # ↕️ 拖拽排序介面
    if is_admin and sort_mode:
        st.subheader("↕️ 調整項目順序")
        titles = view_df['title'].tolist()
        sorted_titles = sort_items(titles, key="drag_sort_list")
        if st.button("💾 儲存全新排序順序", use_container_width=True, type="primary"):
            for i, t in enumerate(sorted_titles):
                st.session_state.df.loc[(st.session_state.df['title'] == t) & 
                                        (st.session_state.df['branch'] == branch) & 
                                        (st.session_state.df['category'] == current_cat), 'priority'] = i
            save_to_gs(st.session_state.df)
            st.rerun()
    
    # 📜 標準清單模式
    else:
        for idx, row in view_df.iterrows():
            # 建立三欄：標題與內容、編輯、刪除
            col_main, col_edit, col_del = st.columns([0.86, 0.07, 0.07])
            
            with col_main:
                # 使用 expander 呈現內容
                title_display = f"📌 **{row['title']}**"
                if row['note']: title_display += f" ｜ 🏷️ {row['note']}"
                
                with st.expander(title_display):
                    st.write("**🇺🇸 English**")
                    st.code(row['content_en'], language="text")
                    st.write("**🇹🇼 中文**")
                    st.code(row['content_tw'], language="text")
            
            if is_admin:
                with col_edit:
                    if st.button("✏️", key=f"ed_{idx}", help="編輯此項"):
                        st.session_state[f"edit_mode_{idx}"] = not st.session_state.get(f"edit_mode_{idx}", False)
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"de_{idx}", help="刪除此項"):
                        st.session_state.df = st.session_state.df.drop(idx)
                        save_to_gs(st.session_state.df)
                        st.rerun()
            
            # ✨ 關鍵：編輯區塊出現在該項目的正下方
            if st.session_state.get(f"edit_mode_{idx}", False):
                with st.container(border=True):
                    st.markdown(f"🛠️ **正在編輯項目：{row['title']}**")
                    ec1, ec2 = st.columns(2)
                    with ec1: et = st.text_input("修改標題", row['title'], key=f"t_{idx}")
                    with ec2: en = st.text_input("修改備註", row['note'], key=f"n_{idx}")
                    
                    ee = st.text_area("編輯英文內容", row['content_en'], key=f"ee_{idx}", height=150)
                    ew = st.text_area("編輯中文內容", row['content_tw'], key=f"ew_{idx}", height=150)
                    
                    eb1, eb2 = st.columns(2)
                    if eb1.button("💾 確認更新", key=f"save_{idx}", use_container_width=True):
                        st.session_state.df.loc[idx, ['title','note','content_en','content_tw']] = [et, en, ee, ew]
                        save_to_gs(st.session_state.df)
                        st.session_state[f"edit_mode_{idx}"] = False
                        st.rerun()
                    if eb2.button("✖️ 取消編輯", key=f"cancel_{idx}", use_container_width=True):
                        st.session_state[f"edit_mode_{idx}"] = False
                        st.rerun()
else:
    st.info("目前尚無資料，請從側邊欄新增模板。")