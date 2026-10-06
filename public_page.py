import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from style import apply_style
from components import page_header, load_sheet_safe

apply_style()
page_header()

# ============================================================
# TITLE
# ============================================================
st.markdown("""
<div style="
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
">
    <div style="
        width: 44px;
        height: 44px;
        background-color: #f2ebe0;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.4rem;
    ">🔍</div>
    <h1 style="
        margin: 0;
        color: #292524;
        font-weight: 600;
        font-size: 1.85rem;
        border: none;
        padding: 0;
    ">Semak Kelayakan</h1>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<p style="
    color: #78716c;
    font-size: 0.95rem;
    margin-bottom: 2rem;
">Masukkan No. Pendaftaran Kenderaan/Plate Number anda untuk semak status permohonan.</p>
""", unsafe_allow_html=True)

# ============================================================
# LOAD DATA
# ============================================================
@st.cache_data(ttl=600, show_spinner="Memuatkan data...")
def load_vendors():
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        return conn.read(worksheet="Vendors", ttl=600), None
    except Exception as e:
        return None, str(e)

df, err = load_vendors()

if df is None:
    error_msg = (err or "").lower()
    if "429" in error_msg or "quota" in error_msg:
        st.warning("""
        ⏳ **Sistem sedang sibuk.**

        Terlalu banyak permintaan. Sila tunggu **1-2 minit** dan cuba lagi.
        """)
        if st.button("🔄 Cuba Lagi"):
            st.cache_data.clear()
            st.rerun()
    else:
        st.error("⚠️ Sistem tidak dapat memuatkan data. Sila cuba lagi.")
        with st.expander("Butiran teknikal"):
            st.code(err)
    st.stop()

# ============================================================
# SEARCH FORM
# ============================================================
with st.form("search"):
    query = st.text_input(
        "No. Pendaftaran Kenderaan/Plate Number",
        placeholder="Contoh: NNA1806"
    ).strip().upper()

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        submitted = st.form_submit_button("Semak Status", type="primary", use_container_width=True)

# ============================================================
# RESULT
# ============================================================
if submitted and query:
    result = df[
        df["Plate Number"].astype(str).str.upper().str.replace(" ", "")
        == query.replace(" ", "")
    ]

    if result.empty:
        st.divider()
        st.markdown(f"""
        <div style="
            background-color: #fef3c7;
            border: 1px solid #fde68a;
            border-radius: 12px;
            padding: 1.5rem 1.75rem;
            margin-top: 1rem;
        ">
            <div style="
                font-size: 1.05rem;
                font-weight: 600;
                color: #78350f;
                margin-bottom: 0.5rem;
            ">❌ Tiada permohonan dijumpai</div>
            <div style="
                color: #78350f;
                font-size: 0.95rem;
                margin-bottom: 1.25rem;
            "><b>{query}</b> tidak ada dalam sistem. Sila daftar terlebih dahulu atau hubungi admin.</div>
            <a href="https://forms.gle/bheUdQTvKRTCns4eA" target="_blank" style="
                display: block;
                background-color: #78350f;
                color: #ffffff;
                text-align: center;
                padding: 0.85rem 1.5rem;
                border-radius: 8px;
                text-decoration: none;
                font-weight: 600;
                font-size: 1rem;
            ">📝 Daftar Sekarang</a>
        </div>
        """, unsafe_allow_html=True)

    else:
        row = result.iloc[0]
        status = row["Status"]
        paid = bool(row["Paid"]) if pd.notna(row["Paid"]) else False

        st.divider()

        # ====================================================
        # INFO CARD
        # ====================================================
        fb_row = ""
        if pd.notna(row.get("F&B CATEGORY")) and str(row["F&B CATEGORY"]).strip():
            fb_row = (
                f'<div style="color:#44403c;">'
                f'<span style="color:#78716c;">F&B Category:</span> '
                f'<b style="color:#292524;">{row["F&B CATEGORY"]}</b>'
                f'</div>'
            )

        info_card_html = (
            f'<div style="background-color:#ffffff;border:1px solid #e8dcc7;'
            f'border-radius:12px;padding:1.5rem 1.75rem;margin-bottom:1.5rem;">'
            f'<div style="font-size:0.8rem;color:#78716c;text-transform:uppercase;'
            f'letter-spacing:0.5px;margin-bottom:0.5rem;">Maklumat Permohonan</div>'
            f'<div style="font-size:1.3rem;font-weight:600;color:#292524;'
            f'margin-bottom:0.75rem;">{row["Plate Number"]}</div>'
            f'<div style="display:grid;gap:0.5rem;">'
            f'<div style="color:#44403c;"><span style="color:#78716c;">Nama:</span> '
            f'<b style="color:#292524;">{row["Nama/Name"]}</b></div>'
            f'<div style="color:#44403c;"><span style="color:#78716c;">Kategori:</span> '
            f'<b style="color:#292524;">{row["Kategori Produk/Product Category"]}</b></div>'
            f'{fb_row}'
            f'</div>'
            f'</div>'
        )

        st.markdown(info_card_html, unsafe_allow_html=True)

        # ====================================================
        # STATUS
        # ====================================================

        # ---------- PENDING ----------
        if status == "Pending":
            st.markdown("""
            <div style="
                background-color: #fffbeb;
                border: 1px solid #fde68a;
                border-radius: 12px;
                padding: 1.5rem 1.75rem;
                margin-bottom: 1rem;
            ">
                <div style="
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                    margin-bottom: 0.75rem;
                ">
                    <div style="
                        width: 36px;
                        height: 36px;
                        background-color: #f59e0b;
                        color: #ffffff;
                        border-radius: 50%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 1.1rem;
                        font-weight: 700;
                    ">⏳</div>
                    <div style="
                        font-size: 1.15rem;
                        font-weight: 700;
                        color: #78350f;
                    ">Permohonan Sedang Disemak</div>
                </div>
                <div style="
                    color: #78350f;
                    font-size: 0.95rem;
                ">Permohonan anda telah diterima dan sedang dalam proses semakan admin. Sila semak semula dalam <b>1-2 hari</b>. Anda akan dimaklumkan melalui WhatsApp setelah diluluskan.</div>
            </div>
            """, unsafe_allow_html=True)

            st.info("📌 **Belum perlu buat bayaran.** Bayaran hanya diperlukan selepas permohonan anda diluluskan.")

        # ---------- REJECTED ----------
        elif status == "Rejected":
            st.markdown("""
            <div style="
                background-color: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 12px;
                padding: 1.5rem 1.75rem;
            ">
                <div style="
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                    margin-bottom: 0.75rem;
                ">
                    <div style="
                        width: 36px;
                        height: 36px;
                        background-color: #dc2626;
                        color: #ffffff;
                        border-radius: 50%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 1.1rem;
                        font-weight: 700;
                    ">✕</div>
                    <div style="
                        font-size: 1.15rem;
                        font-weight: 700;
                        color: #991b1b;
                    ">Permohonan Tidak Berjaya</div>
                </div>
                <div style="
                    color: #991b1b;
                    font-size: 0.95rem;
                ">Maaf, permohonan anda tidak dipilih untuk event ini. Hubungi admin untuk maklumat lanjut.</div>
            </div>
            """, unsafe_allow_html=True)

        # ---------- CANCELLED ----------
        elif status == "Cancelled":
            st.markdown("""
            <div style="
                background-color: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 12px;
                padding: 1.5rem 1.75rem;
            ">
                <div style="
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                    margin-bottom: 0.75rem;
                ">
                    <div style="
                        width: 36px;
                        height: 36px;
                        background-color: #dc2626;
                        color: #ffffff;
                        border-radius: 50%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 1.1rem;
                        font-weight: 700;
                    ">🚫</div>
                    <div style="
                        font-size: 1.15rem;
                        font-weight: 700;
                        color: #991b1b;
                    ">Slot Dibatalkan</div>
                </div>
                <div style="
                    color: #991b1b;
                    font-size: 0.95rem;
                ">Slot anda telah dibatalkan kerana bayaran tidak diterima sebelum tarikh akhir. Hubungi admin jika ada masalah.</div>
            </div>
            """, unsafe_allow_html=True)

        # ---------- APPROVED ----------
        elif status == "Approved":
            if not paid:
                # ---- Approved but not paid ----
                st.markdown("""
                <div style="
                    background-color: #fffbeb;
                    border: 1px solid #fde68a;
                    border-radius: 12px;
                    padding: 1.5rem 1.75rem;
                    margin-bottom: 1rem;
                ">
                    <div style="
                        display: flex;
                        align-items: center;
                        gap: 0.75rem;
                        margin-bottom: 0.75rem;
                    ">
                        <div style="
                            width: 36px;
                            height: 36px;
                            background-color: #78350f;
                            color: #ffffff;
                            border-radius: 50%;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-size: 1.1rem;
                            font-weight: 700;
                        ">✓</div>
                        <div style="
                            font-size: 1.15rem;
                            font-weight: 700;
                            color: #78350f;
                        ">Permohonan Diluluskan</div>
                    </div>
                    <div style="
                        color: #78350f;
                        font-size: 0.95rem;
                    ">Tahniah! Permohonan anda telah diluluskan. Sila buat bayaran dan upload bukti untuk konfirmasi slot anda.</div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("""
                <div style="
                    background-color: #fef2f2;
                    border: 1px solid #fecaca;
                    border-radius: 12px;
                    padding: 1rem 1.25rem;
                    margin-bottom: 1rem;
                ">
                    <div style="color: #991b1b; font-size: 0.9rem; font-weight: 500;">
                        ⚠️ <b>Penting:</b> Kalau bayaran tidak diterima <b>2 hari sebelum event</b>, slot anda akan dibatalkan automatik.
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Button proper brown
                try:
                    st.link_button(
                        "📤  Upload Bukti Bayaran",
                        st.secrets["event"]["payment_form_url"],
                        use_container_width=True,
                        type="primary"
                    )
                except AttributeError:
                    st.markdown(
                        f"""
                        <a href="{st.secrets['event']['payment_form_url']}" target="_blank" style="
                            display: block;
                            background-color: #78350f;
                            color: #ffffff;
                            text-align: center;
                            padding: 0.85rem 1.5rem;
                            border-radius: 8px;
                            text-decoration: none;
                            font-weight: 600;
                            font-size: 1rem;
                            margin-top: 0.5rem;
                        ">📤 Upload Bukti Bayaran</a>
                        """,
                        unsafe_allow_html=True
                    )

            else:
                # ---- Approved & Paid ----
                st.markdown("""
                <div style="
                    background-color: #f0fdf4;
                    border: 1px solid #86efac;
                    border-radius: 12px;
                    padding: 1.5rem 1.75rem;
                    margin-bottom: 1rem;
                ">
                    <div style="
                        display: flex;
                        align-items: center;
                        gap: 0.75rem;
                        margin-bottom: 0.75rem;
                    ">
                        <div style="
                            width: 36px;
                            height: 36px;
                            background-color: #16a34a;
                            color: #ffffff;
                            border-radius: 50%;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-size: 1.1rem;
                            font-weight: 700;
                        ">✓</div>
                        <div style="
                            font-size: 1.15rem;
                            font-weight: 700;
                            color: #14532d;
                        ">Permohonan Disahkan</div>
                    </div>
                    <div style="
                        color: #166534;
                        font-size: 0.95rem;
                    ">Tahniah! Anda telah berjaya mendaftar dan membuat pembayaran. Sertai kumpulan WhatsApp vendor untuk maklumat lanjut.</div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("""
                <div style="
                    font-size: 1rem;
                    font-weight: 600;
                    color: #292524;
                    margin-top: 1.5rem;
                    margin-bottom: 0.25rem;
                ">Sertai WhatsApp Group Vendor</div>
                <div style="
                    color: #78716c;
                    font-size: 0.9rem;
                    margin-bottom: 1rem;
                ">Dapatkan maklumat terkini tentang event, susun atur booth, dan update penting.</div>
                """, unsafe_allow_html=True)

                # Button proper brown (bukan hijau)
                try:
                    st.link_button(
                        "💬  Join WhatsApp Group",
                        st.secrets["event"]["whatsapp_group"],
                        use_container_width=True,
                        type="primary"
                    )
                except AttributeError:
                    st.markdown(
                        f"""
                        <a href="{st.secrets['event']['whatsapp_group']}" target="_blank" style="
                            display: block;
                            background-color: #78350f;
                            color: #ffffff;
                            text-align: center;
                            padding: 0.85rem 1.5rem;
                            border-radius: 8px;
                            text-decoration: none;
                            font-weight: 600;
                            font-size: 1rem;
                        ">Join WhatsApp Group</a>
                        """,
                        unsafe_allow_html=True
                    )

                st.balloons()