import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from deep_translator import GoogleTranslator

# --- 1. 初始化 Google Sheets ---
def init_gspread():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        info = dict(st.secrets["gcp_service_account"])
        if "private_key" in info:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(info, scopes=scope)
        client = gspread.authorize(creds)
        sh = client.open("InnHelperDB")
        return sh.get_worksheet(0)
    except Exception as e:
        st.error(f"❌ 連接失敗: {e}")
        st.stop()

worksheet = init_gspread()

def get_gs_data():
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

def save_to_gs(df):
    try:
        df_clean = df.fillna("")
        data_to_save = [df_clean.columns.values.tolist()] + df_clean.values.tolist()
        worksheet.clear()
        worksheet.update(data_to_save)
        st.toast("🚀 雲端同步成功")
        return True
    except Exception as e:
        st.error(f"❌ 同步失敗: {e}")
        return False

# --- 2. 網頁配置與 CSS ---
st.set_page_config(page_title="旅館客服系統", layout="wide")

st.markdown("""
    <style>
    /* 移除所有 code 框的背景與邊框，使其看起來像純文字 */
    code { 
        background-color: transparent !important; 
        color: #333 !important; 
        padding: 0 !important;
        font-family: sans-serif !important;
        white-space: pre-wrap !important;
    }
    /* 限制檢視區域高度並允許捲動，但不顯示灰色背景 */
    .text-container {
        max-height: 150px;
        overflow-y: auto;
        padding: 10px;
        border-left: 3px solid #f0f2f6;
        margin: 10px 0;
    }
    div.stButton > button {
        width: 100%;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

if 'df' not in st.session_state:
    st.session_state.df = get_gs_data()

# --- 3. 側邊欄 ---
branch = st.sidebar.selectbox("分館", ["喜園館", "中華館", "長沙館"])
user_mode = st.sidebar.radio("類別", ["公版回覆", "個人常用"])
is_admin = (st.sidebar.text_input("管理密碼", type="password") == "000000") if user_mode == "公版回覆" else True

# --- 4. 主畫面：翻譯中心 ---
st.title(f"💬 {branch} 客服中心")

src_text = st.text_input("🌐 快速翻譯：", placeholder="輸入文字自動轉繁中...")
if src_text:
    res = GoogleTranslator(source='auto', target='zh-TW').translate(src_text)
    st.info(f"**翻譯結果：**")
    st.write(res) # 使用純文字顯示翻譯

st.divider()

# --- 5. 模板內容顯示 ---
current_cat = "公版回覆" if user_mode == "公版回覆" else "Kuma"
view_df = st.session_state.df[(st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat)].copy()

if not view_df.empty:
    view_df['priority'] = pd.to_numeric(view_df['priority'], errors='coerce').fillna(999)
    view_df = view_df.sort_values("priority")

    for idx, row in view_df.iterrows():
        note_display = f" ｜ 🏷️ {row['note']}" if row['note'] else ""
        header_text = f"📌 **{row['title']}** {note_display}"
        
        with st.expander(header_text):
            c1, c2 = st.columns(2)
            
            show_key = f"view_{idx}"
            if show_key not in st.session_state:
                st.session_state[show_key] = None

            # 點擊按鈕
            if c1.button("👁️ 檢視英文", key=f"v_en_{idx}"):
                st.session_state[show_key] = ("🇺🇸 英文內容", row['content_en'])
            if c2.button("👁️ 檢視中文", key=f"v_tw_{idx}"):
                st.session_state[show_key] = ("🇹🇼 中文內容", row['content_tw'])

            # 顯示純文字檢視區
            if st.session_state[show_key]:
                label, content = st.session_state[show_key]
                st.markdown(f"**{label}**")
                
                # 使用 HTML div 包裹純文字，達成限高且無框的效果
                st.markdown(f'''
                    <div class="text-container">
                        {content}
                    </div>
                ''', unsafe_allow_html=True)
                
                # 提示使用者手動全選複製
                st.caption("💡 請長按上方文字即可全選複製")
                
                if st.button("✖️ 關閉", key=f"close_{idx}"):
                    st.session_state[show_key] = None
                    st.rerun()
            
            if is_admin:
                st.divider()
                if st.button("🗑️ 刪除", key=f"del_{idx}"):
                    st.session_state.df = st.session_state.df.drop(idx)
                    save_to_gs(st.session_state.df)
                    st.rerun()