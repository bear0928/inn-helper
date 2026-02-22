import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from deep_translator import GoogleTranslator
from streamlit_sortables import sort_items
import streamlit.components.v1 as components

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
    df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
    df['priority'] = pd.to_numeric(df['priority'], errors='coerce').fillna(999).astype(int)
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
st.set_page_config(page_title="旅館客服管理系統", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; }
    
    /* 側邊欄拖拽樣式修正 */
    div[data-testid="stSidebar"] iframe { width: 100% !important; }

    /* 方框閱覽模式樣式 */
    .card-container {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 15px;
        background-color: #f9f9f9;
        margin-bottom: 15px;
        height: 100%;
    }
    .card-title {
        color: #ff4b4b;
        font-weight: bold;
        font-size: 1.1rem;
        border-bottom: 1px solid #eee;
        padding-bottom: 5px;
        margin-bottom: 10px;
    }
    .card-content {
        font-size: 0.9rem;
        color: #333;
        white-space: pre-wrap;
    }

    div[data-testid="stTextArea"] textarea { font-size: 18px !important; }
    </style>
""", unsafe_allow_html=True)

components.html(
    """
    <script>
    const doc = window.parent.document;
    doc.addEventListener('keydown', function(e) {
        if (e.target.tagName === 'TEXTAREA' && e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault(); e.target.blur();
            setTimeout(() => e.target.focus(), 100);
        }
    });

    setInterval(() => {
        const iframes = doc.querySelectorAll('iframe');
        iframes.forEach(iframe => {
            try {
                const innerDoc = iframe.contentDocument || iframe.contentWindow.document;
                if (innerDoc && !innerDoc.getElementById('fix-sort-width')) {
                    const style = innerDoc.createElement('style');
                    style.id = 'fix-sort-width';
                    style.innerHTML = `
                        #root > div, .sortable-list, ul { display: flex !important; flex-direction: column !important; align-items: stretch !important; width: 100% !important; }
                        #root > div > div, .sortable-item, li { 
                            width: 100% !important; background-color: #ff4b4b !important; color: white !important; 
                            padding: 12px !important; margin-bottom: 8px !important; border-radius: 6px !important; 
                            text-align: center !important; cursor: grab !important; border: none !important;
                        }
                    `;
                    innerDoc.head.appendChild(style);
                }
            } catch(e) {}
        });
    }, 500);
    </script>
    """, height=0,
)

if 'df' not in st.session_state: st.session_state.df = get_gs_data()
if 'authenticated' not in st.session_state: st.session_state.authenticated = False

ALL_BRANCHES = ["喜園館", "中華館", "長沙館"]

# --- 3. 側邊欄 ---
with st.sidebar:
    st.header("⚙️ 系統控制")
    branch = st.radio("📍 選擇目前分館", ALL_BRANCHES, index=0)
    user_mode = st.segmented_control("🔑 運作模式", ["公版回覆", "個人常用"], default="公版回覆")
    
    st.divider()
    
    is_admin = False
    staff_name = "Kuma"
    if user_mode == "公版回覆":
        if not st.session_state.authenticated:
            pwd = st.text_input("管理員密碼", type="password")
            if pwd == "000000": st.session_state.authenticated = True; st.rerun()
        else:
            is_admin = True
            if st.button("🔓 登出管理員", use_container_width=True): st.session_state.authenticated = False; st.rerun()
    else:
        is_admin = True
        staff_list = sorted(st.session_state.df[st.session_state.df['category'] != "公版回覆"]['category'].unique().tolist())
        staff_name = st.selectbox("切換個人帳號", staff_list) if staff_list else st.text_input("建立新帳號", value="Kuma")

    if is_admin:
        st.divider()
        sort_mode = st.toggle("↕️ 開啟拖拽排序模式")
        if sort_mode:
            current_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
            sort_df = st.session_state.df[(st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat)].sort_values("priority")
            if not sort_df.empty:
                titles = sort_df['title'].tolist()
                sorted_titles = sort_items(titles, key="drag_sort_list")
                if st.button("💾 儲存排序", use_container_width=True, type="primary"):
                    for i, t in enumerate(sorted_titles):
                        st.session_state.df.loc[(st.session_state.df['title'] == t) & (st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat), 'priority'] = i
                    save_to_gs(st.session_state.df); st.rerun()
            st.divider()

        with st.expander("➕ 新增回覆模板"):
            with st.form("add_form", clear_on_submit=True):
                n_t, n_n = st.text_input("標題"), st.text_input("備註")
                n_e, n_w = st.text_area("英文內容"), st.text_area("中文內容")
                if st.form_submit_button("💾 儲存項目", use_container_width=True):
                    if n_t:
                        target_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
                        next_id = int(st.session_state.df['id'].max()) + 1 if not st.session_state.df.empty else 1
                        current_max_p = st.session_state.df[st.session_state.df['branch'] == branch]['priority'].max()
                        next_p = int(current_max_p) + 1 if pd.notna(current_max_p) else 0
                        new_row = pd.DataFrame([{"id": next_id, "branch": branch, "category": target_cat, "title": n_t, "content_en": n_e, "content_tw": n_w, "note": n_n, "priority": next_p}])
                        st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                        save_to_gs(st.session_state.df); st.rerun()

# --- 4. 主畫面：翻譯與檢視切換 ---
st.title(f"🏨 {branch} 客服系統")

with st.container(border=True):
    st.subheader("🌐 雙向翻譯中心")
    src_text = st.text_area("輸入內容：", placeholder="Enter 翻譯 / Shift+Enter 換行", height=150, key="trans_input")
    if src_text.strip():
        translated_to_tw = GoogleTranslator(source='auto', target='zh-TW').translate(src_text)
        final_result = GoogleTranslator(source='auto', target='en').translate(src_text) if src_text.strip() == translated_to_tw.strip() else translated_to_tw
        st.success("**翻譯結果：**")
        st.code(final_result, language="text")

st.divider()

# --- 檢視模式切換 ---
view_mode = st.radio("👁️ 檢視方式", ["條列 (點開閱覽)", "方框 (直接顯示)"], horizontal=True)

current_cat = "公版回覆" if user_mode == "公版回覆" else staff_name
view_df = st.session_state.df[(st.session_state.df['branch'] == branch) & (st.session_state.df['category'] == current_cat)].sort_values("priority")

if not view_df.empty:
    if view_mode == "方框 (直接顯示)":
        # 每列顯示 2 個方塊
        cols = st.columns(2)
        for i, (idx, row) in enumerate(view_df.iterrows()):
            with cols[i % 2]:
                st.markdown(f"""
                <div class="card-container">
                    <div class="card-title">📌 {row['title']} {f'({row["note"]})' if row['note'] else ''}</div>
                    <div style="font-size:0.8rem; color:gray; margin-bottom:5px;">English:</div>
                    <div class="card-content">{row['content_en']}</div>
                    <div style="font-size:0.8rem; color:gray; margin:10px 0 5px 0;">中文:</div>
                    <div class="card-content">{row['content_tw']}</div>
                </div>
                """, unsafe_allow_html=True)
                # 方塊模式下也提供編輯按鈕
                if is_admin:
                    if st.button("✏️ 編輯項目", key=f"ed_card_{idx}", use_container_width=True):
                        st.session_state[f"edit_mode_{idx}"] = True; st.rerun()
    else:
        # 原有的條列模式
        for idx, row in view_df.iterrows():
            col_main, col_edit, col_del = st.columns([0.88, 0.06, 0.06])
            with col_main:
                with st.expander(f"📌 **{row['title']}** {f'｜ 🏷️ {row["note"]}' if row['note'] else ''}"):
                    st.caption("🇺🇸 English"); st.code(row['content_en'], language="text")
                    st.caption("🇹🇼 中文"); st.code(row['content_tw'], language="text")
            if is_admin:
                if col_edit.button("✏️", key=f"ed_{idx}"): st.session_state[f"edit_mode_{idx}"] = True; st.rerun()
                if col_del.button("🗑️", key=f"de_{idx}"): st.session_state.df = st.session_state.df.drop(idx); save_to_gs(st.session_state.df); st.rerun()

    # 統一處理編輯邏輯 (不論哪種檢視模式點開編輯)
    for idx, row in view_df.iterrows():
        if st.session_state.get(f"edit_mode_{idx}", False):
            with st.container(border=True):
                st.write(f"🔧 **修改資料 (ID: {row['id']})**")
                ec1, ec2 = st.columns(2)
                et = ec1.text_input("標題", row['title'], key=f"t_{idx}")
                en = ec2.text_input("備註", row['note'], key=f"n_{idx}")
                ee = st.text_area("英文內容", row['content_en'], key=f"ee_{idx}", height=200)
                ew = st.text_area("中文內容", row['content_tw'], key=f"ew_{idx}", height=200)
                eb1, eb2 = st.columns(2)
                if eb1.button("💾 儲存並關閉", key=f"save_{idx}", use_container_width=True, type="primary"):
                    st.session_state.df.loc[idx, ['title','note','content_en','content_tw']] = [et, en, ee, ew]
                    save_to_gs(st.session_state.df); st.session_state[f"edit_mode_{idx}"] = False; st.rerun()
                if eb2.button("✖️ 取消", key=f"cancel_{idx}", use_container_width=True): st.session_state[f"edit_mode_{idx}"] = False; st.rerun()
else:
    st.info("💡 目前尚無資料。")