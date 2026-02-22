import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from deep_translator import GoogleTranslator
from streamlit_sortables import sort_items

# --- 1. 初始化 Google Sheets 連線 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_gs_data():
    """讀取 Google Sheets 資料"""
    # ttl=0 代表不快取，每次都抓最新的
    return conn.read(ttl=0).dropna(how="all")

def save_to_gs(df):
    """將完整的 DataFrame 寫回 Google Sheets"""
    conn.update(data=df)
    st.toast("🚀 資料已同步至 Google Sheets")

# --- 2. 網頁基礎配置 ---
st.set_page_config(page_title="旅館客服系統 (Sheets版)", layout="wide")

st.markdown("""
    <style>
    code { white-space: pre-wrap !important; }
    textarea { font-family: sans-serif !important; }
    </style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "000000"

# --- 3. 讀取資料 ---
df = get_gs_data()

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
    staff_list = sorted(df[df['category'] != "公版回覆"]['category'].unique()) if not df.empty else []
    if staff_list:
        staff_name = st.sidebar.selectbox("員工帳號", staff_list)
    else:
        staff_name = st.sidebar.text_input("輸入員工姓名", value="Kuma")

# --- 5. 新增模板 ---
if is_admin:
    st.sidebar.divider()
    with st.sidebar.expander("➕ 新增回覆模板", expanded=False):
        with st.form("add_form", clear_on_submit=True):
            n_t = st.text_input("模板標題")
            n_n = st.text_input("備註標籤")
            n_e = st.text_area("英文內容", height=200)
            n_w = st.text_area("中文內容", height=200)
            
            if st.form_submit_button("💾 確認儲存模板"):
                if n_t:
                    target_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
                    new_row = pd.DataFrame([{
                        "id": len(df) + 1,
                        "branch": branch,
                        "category": target_cat,
                        "title": n_t,
                        "content_en": n_e,
                        "content_tw": n_w,
                        "note": n_n,
                        "priority": len(df)
                    }])
                    df = pd.concat([df, new_row], ignore_index=True)
                    save_to_gs(df)
                    st.success("✅ 雲端寫入成功！")
                    st.rerun()

# --- 6. 主畫面 ---
st.title(f"💬 {branch} 客服中心")
src_text = st.text_input("🌐 翻譯中心：")
if src_text:
    st.info(f"**翻譯：** {GoogleTranslator(source='auto', target='zh-TW').translate(src_text)}")

st.divider()

# --- 7. 內容顯示與操作 ---
sort_mode = st.sidebar.toggle("🔄 排序模式")
current_cat = "公版回覆" if user_mode == "公版回覆" else staff_name

if not df.empty:
    view_df = df[(df['branch'] == branch) & (df['category'] == current_cat)].copy()
    view_df['priority'] = pd.to_numeric(view_df['priority']).fillna(999)
    view_df = view_df.sort_values("priority")

    if sort_mode:
        titles = view_df['title'].tolist()
        sorted_titles = sort_items(titles)
        if st.button("🚀 儲存順序"):
            for i, t in enumerate(sorted_titles):
                df.loc[(df['title'] == t) & (df['category'] == current_cat), 'priority'] = i
            save_to_gs(df)
            st.rerun()
    else:
        for idx, row in view_df.iterrows():
            col1, col2 = st.columns([0.9, 0.1])
            with col1:
                with st.expander(f"📌 {row['title']} {row['note'] if pd.notna(row['note']) else ''}"):
                    st.write("**🇺🇸 English**")
                    st.code(row['content_en'])
                    st.write("**🇹🇼 中文**")
                    st.code(row['content_tw'])
            
            if is_admin:
                with col2:
                    if st.button("🗑️", key=f"del_{idx}"):
                        df = df.drop(idx)
                        save_to_gs(df)
                        st.rerun()