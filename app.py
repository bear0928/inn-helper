import streamlit as st
import pandas as pd
import os
from deep_translator import GoogleTranslator

# 網頁基礎設定
st.set_page_config(page_title="旅館客服系統", layout="wide")

# --- 設定密碼 (可自行修改) ---
ADMIN_PASSWORD = "ximen888" 

# --- 1. 資料處理函數 ---
CSV_FILE = 'templates.csv'

def load_data():
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            required_cols = ["branch", "category", "title", "content_en", "content_tw", "note"]
            for col in required_cols:
                if col not in df.columns:
                    df[col] = ""
            return df
        except:
            return pd.DataFrame(columns=["branch", "category", "title", "content_en", "content_tw", "note"])
    else:
        return pd.DataFrame(columns=["branch", "category", "title", "content_en", "content_tw", "note"])

def save_data(df):
    df.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')

# 初始化 Session State
if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 2. 側邊欄設定 ---
st.sidebar.title("🏨 管理系統")
branch = st.sidebar.selectbox("切換分館", ["喜園館", "中華館", "長沙館"])
user_mode = st.sidebar.radio("類別", ["公版回覆", "個人常用"])

# 權限檢查
is_admin = False
if user_mode == "公版回覆":
    pwd = st.sidebar.text_input("輸入管理密碼以修改公版", type="password")
    if pwd == ADMIN_PASSWORD:
        is_admin = True
        st.sidebar.success("管理員已解鎖")
    elif pwd:
        st.sidebar.error("密碼錯誤")
else:
    is_admin = True # 個人專區預設可編輯自己的

staff_name = ""
if user_mode == "個人常用":
    existing_staff = st.session_state.df[st.session_state.df['category'] != "公版回覆"]['category'].unique().tolist()
    if not existing_staff:
        existing_staff = ["Kuma"]
    staff_options = sorted(existing_staff) + ["+ 新增員工"]
    selected_staff = st.sidebar.selectbox("選擇員工姓名", staff_options)
    
    if selected_staff == "+ 新增員工":
        new_staff_input = st.sidebar.text_input("請輸入新員工姓名")
        staff_name = new_staff_input if new_staff_input else "New Staff"
    else:
        staff_name = selected_staff

st.sidebar.divider()

# --- 3. 新增模板功能 ---
if is_admin:
    with st.sidebar.expander("➕ 新增回覆模板"):
        new_title = st.text_input("模板標題")
        new_note = st.text_input("小備註 (標籤)")
        new_en = st.text_area("英文內容", key="new_en")
        new_tw = st.text_area("中文內容", key="new_tw")
        target_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
        
        if st.button("確認儲存模板"):
            if new_title:
                new_row = {
                    "branch": branch, "category": target_cat,
                    "title": new_title, "content_en": new_en,
                    "content_tw": new_tw, "note": new_note
                }
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(st.session_state.df)
                st.success(f"✅ 已存入 {target_cat}")
                st.rerun()

# --- 4. 主畫面：翻譯窗口 ---
st.title(f"💬 {branch} 客服小幫手")
source_text = st.text_input("🌐 貼上顧客訊息並按下 Enter 翻譯：")
if source_text:
    try:
        translated_res = GoogleTranslator(source='auto', target='zh-TW').translate(source_text)
        st.info(f"**【翻譯結果】**\n\n{translated_res}")
    except:
        st.error("翻譯連線超時")

st.divider()

# --- 5. 主畫面：模板庫 ---
st.subheader(f"📄 {user_mode}：{staff_name if user_mode=='個人常用' else ''}")
current_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
mask = (st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat)
view_df = st.session_state.df[mask]

if view_df.empty:
    st.info("尚無模板。")
else:
    for index, row in view_df.iterrows():
        # --- 修正後的佈局邏輯 ---
        if is_admin:
            # 管理員模式：顯示 標題(大)、編輯(小)、刪除(小)
            cols = st.columns([0.8, 0.1, 0.1])
            col_main, col_edit, col_del = cols[0], cols[1], cols[2]
        else:
            # 一般模式：只顯示標題
            cols = st.columns([1.0])
            col_main = cols[0]

        with col_main:
            note_label = f" 🏷️ {row['note']}" if pd.notna(row['note']) and row['note'] != "" else ""
            with st.expander(f"📌 {row['title']} {note_label}"):
                if note_label: st.warning(f"**💡 提示：** {row['note']}")
                c_en, c_tw = st.columns(2)
                c_en.code(row['content_en'], language="text")
                c_tw.code(row['content_tw'], language="text")

        if is_admin:
            if col_edit.button("✏️", key=f"ed_{index}"):
                st.session_state[f"edit_{index}"] = True
            if col_del.button("🗑️", key=f"de_{index}"):
                st.session_state.df = st.session_state.df.drop(index)
                save_data(st.session_state.df)
                st.rerun()

            # 編輯區 (點擊鉛筆後出現)
            if st.session_state.get(f"edit_{index}", False):
                with st.container(border=True):
                    st.write(f"✍️ 編輯模板：{row['title']}")
                    e_title = st.text_input("標題", value=row['title'], key=f"ti_{index}")
                    e_note = st.text_input("備註", value=row['note'], key=f"no_{index}")
                    e_en = st.text_area("英文", value=row['content_en'], key=f"en_{index}")
                    e_tw = st.text_area("中文", value=row['content_tw'], key=f"tw_{index}")
                    cb1, cb2 = st.columns(2)
                    if cb1.button("💾 儲存", key=f"sv_{index}"):
                        st.session_state.df.at[index, 'title'] = e_title
                        st.session_state.df.at[index, 'note'] = e_note
                        st.session_state.df.at[index, 'content_en'] = e_en
                        st.session_state.df.at[index, 'content_tw'] = e_tw
                        save_data(st.session_state.df)
                        st.session_state[f"edit_{index}"] = False
                        st.rerun()
                    if cb2.button("✖️ 取消", key=f"cc_{index}"):
                        st.session_state[f"edit_{index}"] = False
                        st.rerun()