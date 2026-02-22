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
    .block-container { padding-top: 2rem; max-width: 100% !important; }
    .stExpander { width: 100% !important; }
    
    /* 限制 st.code 高度並允許滾動 */
    div[data-testid="stMarkdownContainer"] pre {
        max-height: 180px !important; 
        overflow-y: auto !important;
        border: 1px solid #ddd !important;
        background-color: #f9f9f9 !important;
    }
    code { white-space: pre-wrap !important; word-break: break-word !important; }
    textarea { font-family: sans-serif !important; }
    </style>
""", unsafe_allow_html=True)

if 'df' not in st.session_state:
    st.session_state.df = get_gs_data()

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# --- 3. 側邊欄：權限與登入 ---
st.sidebar.title("🏨 旅館管理系統")
branch = st.sidebar.selectbox("切換分館", ["喜園館", "中華館", "長沙館"])
user_mode = st.sidebar.radio("權限類別", ["公版回覆", "個人常用"])

is_admin = False
staff_name = "Kuma"
ADMIN_PASSWORD = "000000"

if user_mode == "公版回覆":
    if not st.session_state.authenticated:
        pwd = st.sidebar.text_input("管理密碼", type="password")
        if pwd == ADMIN_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
    else:
        is_admin = True
        if st.sidebar.button("登出管理員"):
            st.session_state.authenticated = False
            st.rerun()
else:
    is_admin = True
    staff_list = sorted(st.session_state.df[st.session_state.df['category'] != "公版回覆"]['category'].unique().tolist())
    staff_name = st.sidebar.selectbox("切換員工帳號", staff_list) if staff_list else st.sidebar.text_input("建立新帳號", value="Kuma")

# --- 4. 側邊欄：新增模板 & 排序開關 ---
if is_admin:
    st.sidebar.divider()
    # 排序模式開關
    sort_mode = st.sidebar.toggle("🔄 開啟排序模式")
    
    with st.sidebar.expander("➕ 新增回覆模板", expanded=False):
        with st.form("add_form", clear_on_submit=True):
            n_t = st.text_input("模板標題 (必填)")
            n_n = st.text_input("備註標籤")
            n_e = st.text_area("英文內容", height=150)
            n_w = st.text_area("中文內容", height=150)
            if st.form_submit_button("💾 確認儲存模板"):
                if n_t:
                    target_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
                    new_id = int(pd.to_numeric(st.session_state.df['id']).max() + 1) if not st.session_state.df.empty else 1
                    new_row = pd.DataFrame([{
                        "id": new_id, "branch": branch, "category": target_cat, 
                        "title": n_t, "content_en": n_e, "content_tw": n_w, 
                        "note": n_n, "priority": len(st.session_state.df)
                    }])
                    st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                    save_to_gs(st.session_state.df)
                    st.rerun()

# --- 5. 主畫面：翻譯中心 ---
st.title(f"💬 {branch} 客服中心")
src_text = st.text_input("🌐 各國語言翻譯 (自動偵測 -> 繁中)：", placeholder="請貼上客人訊息...")
if src_text:
    translated = GoogleTranslator(source='auto', target='zh-TW').translate(src_text)
    st.info("**翻譯結果：**")
    st.code(translated, language="text")

st.divider()

# --- 6. 內容顯示與排序邏輯 ---
current_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
view_df = st.session_state.df[(st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat)].copy()

if view_df.empty:
    st.info(f"目前【{current_cat}】尚無資料。")
else:
    # 依照優先權排序
    view_df['priority'] = pd.to_numeric(view_df['priority'], errors='coerce').fillna(999)
    view_df = view_df.sort_values("priority")

    # A. 排序模式：顯示可拖動清單
    if is_admin and sort_mode:
        st.subheader("🖱️ 拖動標題調整顯示順序")
        titles = view_df['title'].tolist()
        sorted_titles = sort_items(titles, direction='vertical', key="sort_list")
        
        if st.button("🚀 儲存新順序"):
            with st.spinner('更新排序中...'):
                for i, t in enumerate(sorted_titles):
                    mask = (st.session_state.df['branch'] == branch) & \
                           (st.session_state.df['category'] == current_cat) & \
                           (st.session_state.df['title'] == t)
                    st.session_state.df.loc[mask, 'priority'] = i
                if save_to_gs(st.session_state.df):
                    st.rerun()

    # B. 一般模式：顯示回覆內容
    else:
        for idx, row in view_df.iterrows():
            col1, col2, col3 = st.columns([0.86, 0.07, 0.07])
            with col1:
                note_display = f" ｜ 🏷️ {row['note']}" if row['note'] else ""
                header_text = f"📌 **{row['title']}** {note_display}"
                with st.expander(header_text):
                    st.write("**🇺🇸 English**")
                    st.code(row['content_en'], language="text")
                    st.write("**🇹🇼 中文**")
                    st.code(row['content_tw'], language="text")
            
            if is_admin:
                with col2:
                    if st.button("✏️", key=f"edit_btn_{idx}"):
                        st.session_state[f"edit_mode_{idx}"] = True
                with col3:
                    if st.button("🗑️", key=f"del_btn_{idx}"):
                        st.session_state.df = st.session_state.df.drop(idx)
                        save_to_gs(st.session_state.df)
                        st.rerun()
                
                # 編輯介面
                if st.session_state.get(f"edit_mode_{idx}", False):
                    with st.container(border=True):
                        st.markdown(f"🛠️ **修改模板：{row['title']}**")
                        et = st.text_input("標題", row['title'], key=f"t_{idx}")
                        en = st.text_input("備註", row['note'], key=f"n_{idx}")
                        ee = st.text_area("英文內容", row['content_en'], key=f"en_{idx}", height=250)
                        ew = st.text_area("中文內容", row['content_tw'], key=f"tw_{idx}", height=250)
                        
                        ec1, ec2 = st.columns(2)
                        if ec1.button("💾 儲存修改", key=f"save_edit_{idx}"):
                            st.session_state.df.at[idx, 'title'] = et
                            st.session_state.df.at[idx, 'note'] = en
                            st.session_state.df.at[idx, 'content_en'] = ee
                            st.session_state.df.at[idx, 'content_tw'] = ew
                            if save_to_gs(st.session_state.df):
                                st.session_state[f"edit_mode_{idx}"] = False
                                st.rerun()
                        if ec2.button("✖️ 取消", key=f"cancel_{idx}"):
                            st.session_state[f"edit_mode_{idx}"] = False
                            st.rerun()