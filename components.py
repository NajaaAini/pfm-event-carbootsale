import streamlit as st
import base64
import pandas as pd
from pathlib import Path
from datetime import datetime

def _image_base64(image_path):
    path = Path(image_path)
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def page_header(title="", subtitle="", image_path="assets/headerpfm.jpeg"):
    """Straight banner image only — no title, no subtitle."""
    img_b64 = _image_base64(image_path)

    if img_b64:
        st.markdown(f"""
        <div style="
            overflow: hidden;
            margin-bottom: 2rem;
            height: 320px;
            background-image: url('data:image/jpeg;base64,{img_b64}');
            background-size: cover;
            background-position: center;
            margin-left: -1rem;
            margin-right: -1rem;
            margin-top: -1rem;
        "></div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #a8a29e 0%, #78716c 100%);
            height: 320px;
            margin-bottom: 2rem;
            margin-left: -1rem;
            margin-right: -1rem;
            margin-top: -1rem;
        "></div>
        """, unsafe_allow_html=True)


def load_sheet_safe(conn, worksheet, ttl=600):
    """
    Safely read from Google Sheets with friendly error messages.
    Returns DataFrame or None on error.
    """
    try:
        return conn.read(worksheet=worksheet, ttl=ttl)

    except Exception as e:
        error_msg = str(e).lower()

        # Quota error (429)
        if "429" in error_msg or "quota" in error_msg or "rate_limit" in error_msg:
            st.warning("""
            ⏳ **Sistem sedang sibuk.**

            Terlalu banyak permintaan dalam masa singkat. Sila tunggu **1-2 minit** dan cuba lagi.
            """)
            if st.button("🔄 Cuba Lagi"):
                st.cache_data.clear()
                st.rerun()
            return None

        # Auth / permission error
        elif "permission" in error_msg or "forbidden" in error_msg or "403" in error_msg:
            st.error("""
            🔒 **Akses ditolak.**

            Sistem tidak dapat membaca data. Sila hubungi admin untuk semak kebenaran.
            """)
            return None

        # Network / connection error
        elif "connection" in error_msg or "timeout" in error_msg or "network" in error_msg:
            st.warning("""
            🌐 **Masalah sambungan.**

            Tidak dapat sambung ke pelayan. Sila semak internet anda dan cuba lagi.
            """)
            if st.button("🔄 Cuba Lagi"):
                st.cache_data.clear()
                st.rerun()
            return None

        # Generic error
        else:
            st.error("""
            ⚠️ **Ada masalah teknikal.**

            Sistem tidak dapat memuatkan data. Sila cuba lagi atau hubungi admin.
            """)
            with st.expander("Lihat butiran teknikal"):
                st.code(str(e))
            return None


def log_action(conn, admin_name, action, plate, details=""):
    """
    Log admin actions to Log sheet.
    Auto-create if Log sheet doesn't exist yet.
    """
    try:
        logs = conn.read(worksheet="Log", ttl=0)
        # Kalau sheet kosong atau takde column, reset
        if logs is None or logs.empty:
            logs = pd.DataFrame(columns=["Timestamp", "Admin", "Action", "Plate", "Details"])
    except Exception:
        # Sheet "Log" belum wujud — create structure baru
        logs = pd.DataFrame(columns=["Timestamp", "Admin", "Action", "Plate", "Details"])

    new_log = pd.DataFrame([{
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Admin": admin_name,
        "Action": action,
        "Plate": plate,
        "Details": details,
    }])

    updated = pd.concat([logs, new_log], ignore_index=True)

    try:
        conn.update(worksheet="Log", data=updated)
    except Exception:
        # Kalau update fail (contoh: sheet tak wujud), skip tanpa crash
        pass


def convert_df_to_csv(df):
    """
    Convert DataFrame to CSV bytes for download.
    """
    return df.to_csv(index=False).encode("utf-8")