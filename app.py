import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from deep_translator import GoogleTranslator
from streamlit_sortables import sort_items

# --- 1. 初始化 Google Sheets (使用 Secrets 憑證) ---
def init_gspread():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # --- 核心修正區：強制修復 private_key 的換行問題 ---
        info = dict(st.secrets["gcp_service_account"])
        if "private_key" in info:
            # 將字面上的 \n 替換成真正的換行符號
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
    """讀取雲端資料並轉換為 DataFrame"""
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    # 確保必要欄位存在
    cols = ["id", "branch", "category", "title", "content_en", "content_tw", "note", "priority"]
    for col in cols:
        if col not in df.columns:
            df[col] = ""
    return df

def save_to_gs(df):
    """將 DataFrame 完整覆蓋回雲端"""
    try:
        # 將 NaN 轉為空字串避免寫入錯誤
        df_clean = df.fillna("")
        # 準備資料列表 (標題 + 內容)
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
    </style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "000000"

# --- 3. 讀取最新資料 ---
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
    # 找出所有非公版的員工名稱
    staff_list = sorted(st.session_state.df[st.session_state.df['category'] != "公版回覆"]['category'].unique().tolist())
    if staff_list:
        staff_name = st.sidebar.selectbox("員工帳號", staff_list)
    else:
        staff_name = st.sidebar.text_input("輸入新員工姓名", value="Kuma")

# --- 5. 新增模板 (Form) ---
if is_admin:
    st.sidebar.divider()
    with st.sidebar.expander("➕ 新增回覆模板", expanded=False):
        with st.form("add_form", clear_on_submit=True):
            n_t = st.text_input("模板標題 (必填)")
            n_n = st.text_input("備註標籤")
            n_e = st.text_area("英文內容", height=200)
            n_w = st.text_area("中文內容", height=200)
            
            if st.form_submit_button("💾 確認儲存模板"):
                if n_t:
                    target_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
                    new_row = pd.DataFrame([{
                        "id": int(pd.to_numeric(st.session_state.df['id']).max() + 1) if not st.session_state.df.empty else 1,
                        "branch": branch,
                        "category": target_cat,
                        "title": n_t,
                        "content_en": n_e,
                        "content_tw": n_w,
                        "note": n_n,
                        "priority": len(st.session_state.df)
                    }])
                    st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                    if save_to_gs(st.session_state.df):
                        st.success("✅ 儲存成功！")
                        st.rerun()
                else:
                    st.error("標題必填！")

# --- 6. 主畫面：翻譯與顯示 ---
st.title(f"💬 {branch} 客服中心")
src_text = st.text_input("🌐 翻譯中心 (自動偵測 -> 繁中)：")
if src_text:
    res = GoogleTranslator(source='auto', target='zh-TW').translate(src_text)
    st.info(f"**翻譯結果：** {res}")

st.divider()

# 過濾顯示內容
current_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
view_df = st.session_state.df[(st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat)].copy()

if view_df.empty:
    st.info(f"目前【{current_cat}】尚無模板資料。")
else:
    sort_mode = st.sidebar.toggle("🔄 拖動排序模式")
    
    # 確保 priority 為數字以便排序
    view_df['priority'] = pd.to_numeric(view_df['priority'], errors='coerce').fillna(999)
    view_df = view_df.sort_values("priority")

    if sort_mode:
        st.subheader("🖱️ 拖動標題調整順序")
        titles = view_df['title'].tolist()
        sorted_titles = sort_items(titles)
        if st.button("🚀 儲存新順序"):
            # 更新總表中的 priority
            for i, t in enumerate(sorted_titles):
                mask = (st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat) & (st.session_state.df['title'] == t)
                st.session_state.df.loc[mask, 'priority'] = i
            save_to_gs(st.session_state.df)
            st.rerun()
    else:
        for idx, row in view_df.iterrows():
            col1, col2 = st.columns([0.85, 0.15])
            with col1:
                display_note = f" {row['note']}" if row['note'] else ""
                with st.expander(f"📌 {row['title']} {display_note}"):
                    st.write("**🇺🇸 English**")
                    st.code(row['content_en'], language="text")
                    st.write("**🇹🇼 中文**")
                    st.code(row['content_tw'], language="text")
            
            if is_admin:
                with col2:
                    if st.button("✏️", key=f"edit_btn_{idx}"):
                        st.session_state[f"edit_mode_{idx}"] = True
                    if st.button("🗑️", key=f"del_btn_{idx}"):
                        st.session_state.df = st.session_state.df.drop(idx)
                        save_to_gs(st.session_state.df)
                        st.rerun()
                
                # 修改功能大框框
                if st.session_state.get(f"edit_mode_{idx}", False):
                    with st.container(border=True):
                        st.subheader(f"🛠️ 修改模板：{row['title']}")
                        et = st.text_input("標題", row['title'], key=f"t_{idx}")
                        en = st.text_input("備註", row['note'], key=f"n_{idx}")
                        ee = st.text_area("英文內容", row['content_en'], key=f"en_{idx}", height=300)
                        ew = st.text_area("中文內容", row['content_tw'], key=f"tw_{idx}", height=300)
                        
                        c1, c2 = st.columns(2)
                        if c1.button("💾 儲存修改", key=f"save_edit_{idx}"):
                            st.session_state.df.at[idx, 'title'] = et
                            st.session_state.df.at[idx, 'note'] = en
                            st.session_state.df.at[idx, 'content_en'] = ee
                            st.session_state.df.at[idx, 'content_tw'] = ew
                            save_to_gs(st.session_state.df)
                            st.session_state[f"edit_mode_{idx}"] = False
                            st.rerun()
                        if c2.button("✖️ 取消", key=f"cancel_{idx}"):
                            st.session_state[f"edit_mode_{idx}"] = False
                            st.rerun()