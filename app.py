import streamlit as st
import pandas as pd
import os
from deep_translator import GoogleTranslator

# 網頁基礎設定
st.set_page_config(page_title="旅館客服系統", layout="wide")

# --- 設定密碼 (您可以在這裡修改) ---
ADMIN_PASSWORD = "000000" 

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

# 權限檢查：如果是公版回覆，需要輸入密碼才能管理
is_admin = False
if user_mode == "公版回覆":
    pwd = st.sidebar.text_input("輸入管理密碼以修改公版", type="password")
    if pwd == ADMIN_PASSWORD:
        is_admin = True
        st.sidebar.success("管理員已解鎖")
    elif pwd:
        st.sidebar.error("密碼錯誤")
else:
    # 個人專區預設可以修改自己的內容
    is_admin = True

staff_name = ""
if user_mode == "個人常用":
    existing_staff = st.session_state.df[st.session_state.df['category'] != "公版回覆"]['category'].unique().tolist()
    if not existing_staff:
        existing_staff = ["Kuma"]
    staff_options = sorted(existing_staff) + ["+ 新增員工"]
    selected_staff = st.sidebar.selectbox("選擇員工姓名", staff_options)
    
    if selected_staff == "+ 新增員工":
        new_staff_input = st.sidebar.text_input("請輸入新員工姓名", placeholder="例如: Amber")
        staff_name = new_staff_input if new_staff_input else "New Staff"
    else:
        staff_name = selected_staff

st.sidebar.divider()

# --- 3. 新增模板功能 (僅限解鎖後顯示) ---
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
st.subheader("🌐 即時翻譯中心 (外語 → 繁中)")
source_text = st.text_input("貼上顧客訊息並按下 Enter：")

if source_text:
    try:
        with st.spinner('翻譯中...'):
            translated_res = GoogleTranslator(source='auto', target='zh-TW').translate(source_text)
            st.info(f"**【中文翻譯結果】**\n\n{translated_res}")
    except Exception:
        st.error("翻譯失敗")

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
        # 如果未解鎖，就不顯示刪除按鈕
        col_width = [0.85, 0.08, 0.07] if is_admin else [0.93, 0.07, 0.00]
        col_main, col_edit, col_del = st.columns(col_width)
        
        with col_main:
            note_label = f" 🏷️ {row['note']}" if pd.notna(row['note']) and row['note'] != "" else ""
            exp = st.expander(f"📌 {row['title']} {note_label}")
            with exp:
                if note_label: st.warning(f"**💡 操作提示：** {row['note']}")
                c_en, c_tw = st.columns(2)
                with c_en:
                    st.write("**🇺🇸 English**")
                    st.code(row['content_en'], language="text")
                with c_tw:
                    st.write("**🇹🇼 中文回覆**")
                    st.code(row['content_tw'], language="text")

        if is_admin:
            with col_edit:
                if st.button("✏️", key=f"edit_btn_{index}", help="修改此模板"):
                    st.session_state[f"editing_{index}"] = True
            
            with col_del:
                if st.button("🗑️", key=f"del_{index}", help="刪除此模板"):
                    st.session_state.df = st.session_state.df.drop(index)
                    save_data(st.session_state.df)
                    st.rerun()
            
            # 編輯區塊：當點擊 ✏️ 後觸發
            if st.session_state.get(f"editing_{index}", False):
                with st.container():
                    st.markdown("---")
                    st.write(f"✍️ 正在編輯：{row['title']}")
                    edit_title = st.text_input("編輯標題", value=row['title'], key=f"et_{index}")
                    edit_note = st.text_input("編輯備註", value=row['note'], key=f"enote_{index}")
                    e_en, e_tw = st.columns(2)
                    edit_en = e_en.text_area("編輯英文", value=row['content_en'], key=f"ee_{index}")
                    edit_tw = e_tw.text_area("編輯中文", value=row['content_tw'], key=f"etw_{index}")
                    
                    c_save, c_cancel = st.columns(2)
                    if c_save.button("💾 儲存修改", key=f"es_{index}"):
                        st.session_state.df.at[index, 'title'] = edit_title
                        st.session_state.df.at[index, 'note'] = edit_note
                        st.session_state.df.at[index, 'content_en'] = edit_en
                        st.session_state.df.at[index, 'content_tw'] = edit_tw
                        save_data(st.session_state.df)
                        st.session_state[f"editing_{index}"] = False
                        st.success("修改成功！")
                        st.rerun()
                    if c_cancel.button("✖️ 取消", key=f"ec_{index}"):
                        st.session_state[f"editing_{index}"] = False
                        st.rerun()

# 頁尾
st.sidebar.divider()
st.sidebar.caption(f"數據庫總量: {len(st.session_state.df)} 筆")