import streamlit as st
import pandas as pd
import os
from deep_translator import GoogleTranslator
from streamlit_sortables import sort_items # 請確保 requirements.txt 有這行

# 網頁基礎設定
st.set_page_config(page_title="旅館客服系統", layout="wide")

# 強制自動換行 CSS
st.markdown("""
    <style>
    code { white-space: pre-wrap !important; word-break: break-word !important; }
    </style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "000000" 
CSV_FILE = 'templates.csv'

def load_data():
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            required_cols = ["branch", "category", "title", "content_en", "content_tw", "note", "priority"]
            for col in required_cols:
                if col not in df.columns:
                    df[col] = 999 if col == "priority" else ""
            return df
        except:
            return pd.DataFrame(columns=["branch", "category", "title", "content_en", "content_tw", "note", "priority"])
    else:
        return pd.DataFrame(columns=["branch", "category", "title", "content_en", "content_tw", "note", "priority"])

def save_data(df):
    df['priority'] = pd.to_numeric(df['priority'], errors='coerce').fillna(999)
    df = df.sort_values(by="priority")
    df.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 側邊欄 ---
st.sidebar.title("🏨 管理系統")
branch = st.sidebar.selectbox("切換分館", ["喜園館", "中華館", "長沙館"])
user_mode = st.sidebar.radio("類別選擇", ["公版回覆", "個人常用"])

is_admin = False
if user_mode == "公版回覆":
    pwd = st.sidebar.text_input("輸入管理密碼以修改內容", type="password")
    if pwd == ADMIN_PASSWORD:
        is_admin = True
        st.sidebar.success("管理權限已開啟")
else:
    is_admin = True

# --- 1. 新增模板區塊 (放在側邊欄顯眼處) ---
if is_admin:
    st.sidebar.divider()
    with st.sidebar.expander("➕ 新增回覆模板", expanded=False):
        n_title = st.text_input("模板標題 (必填)")
        n_note = st.text_input("備註標籤 (如: ⚠️, 💰)")
        n_en = st.text_area("英文內容")
        n_tw = st.text_area("中文內容")
        
        # 決定分類
        staff_name = ""
        if user_mode == "個人常用":
            staff_name = st.text_input("員工姓名", value="Kuma")
        target_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
        
        if st.button("💾 確認儲存模板"):
            if n_title:
                new_data = {
                    "branch": branch, "category": target_cat, "title": n_title, 
                    "content_en": n_en, "content_tw": n_tw, "note": n_note, 
                    "priority": len(st.session_state.df) + 1 # 預設排最後
                }
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_data])], ignore_index=True)
                save_data(st.session_state.df)
                st.success("✅ 已成功寫入 CSV！")
                st.rerun()

st.sidebar.divider()
sort_mode = st.sidebar.toggle("🔄 開啟拖動排序模式", value=False)

# --- 主畫面 ---
st.title(f"💬 {branch} 客服中心")
src_text = st.text_input("🌐 翻譯中心 (輸入任何語言自動轉中文)：")
if src_text:
    res = GoogleTranslator(source='auto', target='zh-TW').translate(src_text)
    st.info(f"**翻譯結果：** {res}")

st.divider()

# --- 2. 顯示與排序邏輯 ---
current_staff = "公版回覆"
if user_mode == "個人常用":
    # 這裡可以篩選個人分類，簡單起見先列出非公版內容
    current_staff = "個人常用" # 或根據你的邏輯調整

mask = (st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == ("公版回覆" if user_mode == "公版回覆" else st.session_state.get('last_staff', '個人常用')))
# (為了簡化，如果是個人常用，建議你還是讓員工選一下名字)

view_df = st.session_state.df[st.session_state.df['branch'] == branch]
if user_mode == "公版回覆":
    view_df = view_df[view_df['category'] == "公版回覆"]
else:
    # 個人專區顯示邏輯
    u_list = [c for c in st.session_state.df['category'].unique() if c != "公版回覆"]
    if u_list:
        sel_u = st.selectbox("選擇查看對象", u_list)
        view_df = view_df[view_df['category'] == sel_u]
    else:
        st.info("目前尚無個人模板")
        view_df = pd.DataFrame()

if not view_df.empty:
    view_df['priority'] = pd.to_numeric(view_df['priority'], errors='coerce').fillna(999)
    view_df = view_df.sort_values(by="priority")

    if sort_mode:
        st.subheader("🖱️ 拖動標題調整順序 (排好後請按下方儲存)")
        items_to_sort = view_df['title'].tolist()
        sorted_items = sort_items(items_to_sort)
        
        if st.button("🚀 儲存新順序並更新 CSV"):
            for i, title in enumerate(sorted_items):
                # 精確匹配更新
                st.session_state.df.loc[(st.session_state.df['branch'] == branch) & 
                                        (st.session_state.df['title'] == title), 'priority'] = i
            save_data(st.session_state.df)
            st.success("順序已寫入檔案！")
            st.rerun()
    else:
        for idx, row in view_df.iterrows():
            m_cols = st.columns([0.85, 0.15]) if is_admin else st.columns([1.0])
            with m_cols[0]:
                label = f"🏷️ {row['note']}" if row['note'] else ""
                with st.expander(f"📌 {row['title']} {label}"):
                    st.write("**🇺🇸 English**")
                    st.code(row['content_en'], language="text")
                    st.write("**🇹🇼 中文**")
                    st.code(row['content_tw'], language="text")

            if is_admin:
                with m_cols[1]:
                    if st.button("✏️", key=f"e_{idx}"): st.session_state[f"edit_{idx}"] = True
                    if st.button("🗑️", key=f"d_{idx}"):
                        st.session_state.df = st.session_state.df.drop(idx)
                        save_data(st.session_state.df)
                        st.rerun()
                
                if st.session_state.get(f"edit_{idx}", False):
                    with st.container(border=True):
                        et = st.text_input("修改標題", row['title'], key=f"t_{idx}")
                        en = st.text_input("修改備註", row['note'], key=f"n_{idx}")
                        ee = st.text_area("修改英文", row['content_en'], key=f"en_{idx}")
                        etw = st.text_area("修改中文", row['content_tw'], key=f"tw_{idx}")
                        if st.button("💾 儲存修改至 CSV", key=f"s_{idx}"):
                            st.session_state.df.at[idx, 'title'] = et
                            st.session_state.df.at[idx, 'note'] = en
                            st.session_state.df.at[idx, 'content_en'] = ee
                            st.session_state.df.at[idx, 'content_tw'] = etw
                            save_data(st.session_state.df)
                            st.session_state[f"edit_{idx}"] = False
                            st.rerun()