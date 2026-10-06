import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date, timedelta, datetime
from style import apply_style
from components import page_header, load_sheet_safe, log_action, convert_df_to_csv

st.set_page_config(page_title="Admin Panel", layout="wide")
apply_style()

# ============================================================
# SEMAKAN LOG MASUK
# ============================================================
if not st.session_state.get("is_admin", False):
    st.error("Sila log masuk di sidebar kiri.")
    st.stop()

page_header()

ADMIN_NAME = st.session_state.get("admin_name", "Admin")

# ============================================================
# KONFIGURASI
# ============================================================
CAR_BOOT_LIMIT = st.secrets["event"]["total_car_boot"]
FB_OVERALL_LIMIT = st.secrets["event"]["total_fb"]
FB_CATEGORY_LIMIT = st.secrets["event"]["fb_per_category"]
EVENT_DATE = date.fromisoformat(st.secrets["event"]["event_date"])
PAYMENT_DEADLINE_DAYS = 2

FB_CATEGORIES = [
    "Local Food", "Dessert", "Coffee/Air", "Grill and BBQ",
    "Deep-Fry", "Italian/Western Food", "Japanese Food", "Chinese Food",
]

COL_NAME = "Nama/Name"
COL_PHONE = "Nombor Telefon/Phone Number"
COL_TYPE = "Kategori Produk/Product Category"
COL_CAT = "F&B CATEGORY"
COL_PLATE = "Plate Number"

# ============================================================
# SAMBUNGAN DATA
# ============================================================
conn = st.connection("gsheets", type=GSheetsConnection)
df = load_sheet_safe(conn, "Vendors", ttl=0)

if df is None:
    st.stop()

df["Paid"] = df["Paid"].fillna(False).astype(bool)
df["Status"] = df["Status"].fillna("Pending")

if "Notes" not in df.columns:
    df["Notes"] = ""

# ============================================================
# FUNGSI BANTUAN
# ============================================================
def committed(**filters):
    mask = pd.Series(True, index=df.index)
    for col, val in filters.items():
        mask &= (df[col] == val)
    mask &= df["Status"].isin(["Approved", "Pending"])
    return df[mask].shape[0]

# ============================================================
# DIALOG PENGESAHAN
# ============================================================
@st.dialog("Sahkan Tindakan")
def confirm_approve_dialog(plate, vendor_name):
    st.write("Anda akan **meluluskan** permohonan ini:")
    st.markdown(f"**No. Plate:** `{plate}`  \n**Nama:** {vendor_name}")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ya, Luluskan", type="primary", use_container_width=True):
            df.loc[df[COL_PLATE] == plate, "Status"] = "Approved"
            conn.update(data=df)
            log_action(conn, ADMIN_NAME, "APPROVE", plate, f"Lulus: {vendor_name}")
            st.toast(f"✅ {plate} telah diluluskan", icon="✅")
            st.rerun()
    with col2:
        if st.button("Batal", use_container_width=True):
            st.rerun()

@st.dialog("Sahkan Tindakan")
def confirm_reject_dialog(plate, vendor_name):
    st.write("Anda akan **menolak** permohonan ini:")
    st.markdown(f"**No. Plate:** `{plate}`  \n**Nama:** {vendor_name}")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ya, Tolak", type="primary", use_container_width=True):
            df.loc[df[COL_PLATE] == plate, "Status"] = "Rejected"
            conn.update(data=df)
            log_action(conn, ADMIN_NAME, "REJECT", plate, f"Tolak: {vendor_name}")
            st.toast(f"❌ {plate} telah ditolak", icon="❌")
            st.rerun()
    with col2:
        if st.button("Batal", use_container_width=True):
            st.rerun()

@st.dialog("Sahkan Pembatalan")
def confirm_cancel_all_dialog(count):
    st.warning(f"Anda akan membatalkan **{count}** vendor yang belum bayar.")
    st.write("Tindakan ini tidak boleh diundur.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ya, Batalkan Semua", type="primary", use_container_width=True):
            df.loc[(df["Status"] == "Approved") & (~df["Paid"]), "Status"] = "Cancelled"
            conn.update(data=df)
            log_action(conn, ADMIN_NAME, "CANCEL_ALL", "-", f"{count} vendor dibatalkan")
            st.toast(f"✅ {count} vendor telah dibatalkan", icon="✅")
            st.rerun()
    with col2:
        if st.button("Batal", use_container_width=True):
            st.rerun()

@st.dialog("Edit Maklumat Vendor")
def edit_vendor_dialog(plate):
    vendor = df[df[COL_PLATE] == plate].iloc[0]

    st.caption(f"Mengedit vendor: **{plate}**")

    new_name = st.text_input("Nama", value=str(vendor.get(COL_NAME, "")))
    new_phone = st.text_input("Telefon", value=str(vendor.get(COL_PHONE, "")))

    type_options = ["Car Boot Sales", "F&B"]
    current_type = str(vendor.get(COL_TYPE, "Car Boot Sales"))
    type_index = type_options.index(current_type) if current_type in type_options else 0
    new_type = st.selectbox("Kategori Produk", options=type_options, index=type_index)

    if new_type == "F&B":
        current_cat = str(vendor.get(COL_CAT, ""))
        cat_index = FB_CATEGORIES.index(current_cat) if current_cat in FB_CATEGORIES else 0
        new_cat = st.selectbox("F&B Category", options=FB_CATEGORIES, index=cat_index)
    else:
        new_cat = ""

    new_plate = st.text_input("No. Plate", value=str(vendor.get(COL_PLATE, "")))

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Simpan", type="primary", use_container_width=True):
            idx = df[df[COL_PLATE] == plate].index[0]
            df.at[idx, COL_NAME] = new_name
            df.at[idx, COL_PHONE] = new_phone
            df.at[idx, COL_TYPE] = new_type
            df.at[idx, COL_CAT] = new_cat
            df.at[idx, COL_PLATE] = new_plate

            conn.update(data=df)
            log_action(conn, ADMIN_NAME, "EDIT", plate, f"Nama: {new_name}, Plate: {new_plate}")
            st.toast(f"✅ {plate} telah dikemaskini", icon="✅")
            st.rerun()
    with col2:
        if st.button("Batal", use_container_width=True):
            st.rerun()

@st.dialog("Sahkan Padam")
def confirm_delete_dialog(plate, vendor_name):
    st.warning("Anda akan **memadam** rekod vendor ini:")
    st.markdown(f"**No. Plate:** `{plate}`  \n**Nama:** {vendor_name}")
    st.write("")
    st.error("⚠️ **Tindakan ini tidak boleh diundur.** Data akan dibuang dari Google Sheet.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ya, Padam", type="primary", use_container_width=True):
            global df
            df = df[df[COL_PLATE] != plate].reset_index(drop=True)
            conn.update(data=df)
            log_action(conn, ADMIN_NAME, "DELETE", plate, f"Padam: {vendor_name}")
            st.toast(f"🗑️ {plate} telah dipadam", icon="🗑️")
            st.rerun()
    with col2:
        if st.button("Batal", use_container_width=True):
            st.rerun()

# ============================================================
# PAPAN PEMANTAUAN
# ============================================================
st.subheader("Papan Pemantauan Kuota")

cb_committed = committed(**{COL_TYPE: "Car Boot Sales"})
fb_committed = committed(**{COL_TYPE: "F&B"})

c1, c2, c3 = st.columns(3)
c1.metric("Car Boot", f"{cb_committed} / {CAR_BOOT_LIMIT}")
c2.metric("F&B Keseluruhan", f"{fb_committed} / {FB_OVERALL_LIMIT}")
c3.metric("Tarikh Event", EVENT_DATE.strftime("%d %b %Y"))

pc1, pc2 = st.columns(2)
with pc1:
    st.markdown("**Car Boot**")
    st.progress(min(cb_committed / CAR_BOOT_LIMIT, 1.0), text=f"{cb_committed}/{CAR_BOOT_LIMIT}")
with pc2:
    st.markdown("**F&B Keseluruhan**")
    st.progress(min(fb_committed / FB_OVERALL_LIMIT, 1.0), text=f"{fb_committed}/{FB_OVERALL_LIMIT}")

st.markdown(f"**Pecahan Kategori F&B (had: {FB_CATEGORY_LIMIT} setiap satu)**")

rows = []
for cat in FB_CATEGORIES:
    a = df[(df[COL_TYPE] == "F&B") & (df[COL_CAT] == cat) & (df["Status"] == "Approved")].shape[0]
    p = df[(df[COL_TYPE] == "F&B") & (df[COL_CAT] == cat) & (df["Status"] == "Pending")].shape[0]
    committed_n = a + p
    left = max(0, FB_CATEGORY_LIMIT - committed_n)
    status_text = "Tersedia" if left > 0 else "Penuh"
    rows.append({
        "Status": status_text, "Kategori": cat, "Diluluskan": a, "Menunggu": p,
        "Komited": committed_n, "Had": FB_CATEGORY_LIMIT, "Slot Baki": left,
    })

fb_df = pd.DataFrame(rows)
st.dataframe(fb_df, hide_index=True, use_container_width=True)

try:
    import plotly.express as px
    approved_fb = df[(df[COL_TYPE] == "F&B") & (df["Status"] == "Approved")]
    if not approved_fb.empty:
        st.markdown("**Carta Pecahan Kategori F&B (Diluluskan)**")
        fig = px.pie(approved_fb, names=COL_CAT, hole=0.4,
                     color_discrete_sequence=px.colors.sequential.Oranges_r)
        fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=300)
        st.plotly_chart(fig, use_container_width=True)
except ImportError:
    pass

st.divider()

# ============================================================
# TARIKH AKHIR BAYARAN
# ============================================================
st.subheader("Tarikh Akhir Bayaran")
cutoff_date = EVENT_DATE - timedelta(days=PAYMENT_DEADLINE_DAYS)
st.caption(f"Vendor yang belum bayar akan dibatalkan selepas **{cutoff_date.strftime('%d %b %Y')}**.")

today = date.today()
if today > cutoff_date:
    expired = df[(df["Status"] == "Approved") & (~df["Paid"])]
    if not expired.empty:
        st.warning(f"{len(expired)} vendor belum membuat bayaran selepas tarikh akhir.")
        st.dataframe(expired[[COL_PLATE, COL_NAME, COL_PHONE, COL_TYPE, COL_CAT]],
                     hide_index=True, use_container_width=True)
        if st.button("Batalkan Semua Yang Belum Bayar", type="primary"):
            confirm_cancel_all_dialog(len(expired))
    else:
        st.success("Semua vendor yang diluluskan telah membuat bayaran.")
else:
    days_left = (cutoff_date - today).days
    st.info(f"Tarikh akhir — {days_left} hari lagi.")

st.divider()

# ============================================================
# LINK GOOGLE FORM RESPONSES
# ============================================================
try:
    form_url = st.secrets["event"].get("google_form_responses_url", "")
except Exception:
    form_url = ""

if form_url:
    st.markdown(f"""
    <div style="
        background-color: #f2ebe0;
        border: 1px solid #e8dcc7;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
    ">
        <div>
            <div style="font-weight: 600; color: #292524; font-size: 0.95rem;">📋 Response Google Form</div>
            <div style="color: #78716c; font-size: 0.85rem; margin-top: 0.25rem;">Buka Responses tab untuk tengok/edit/delete response asal</div>
        </div>
        <a href="{form_url}" target="_blank" style="
            background-color: #78350f;
            color: #ffffff;
            padding: 0.55rem 1.1rem;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9rem;
            white-space: nowrap;
        ">Buka Form</a>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# PERMOHONAN MENUNGGU
# ============================================================
st.subheader("Permohonan Menunggu")
pending_df = df[df["Status"] == "Pending"]

if pending_df.empty:
    st.info("Tiada permohonan yang menunggu.")
else:
    f_col1, f_col2, f_col3 = st.columns([2, 2, 1])

    with f_col1:
        search_query = st.text_input(
            "Cari (No. Plate / Nama / Telefon)",
            placeholder="Contoh: PSC5435 atau Ali",
            key="pending_search"
        ).strip()

    with f_col2:
        type_options = ["Semua"] + pending_df[COL_TYPE].dropna().unique().tolist()
        type_filter = st.selectbox("Kategori", options=type_options, key="pending_type")

    with f_col3:
        sort_options = ["Terbaru", "Terlama", "Nama A-Z"]
        sort_by = st.selectbox("Susun", options=sort_options, key="pending_sort")

    filtered = pending_df.copy()

    if search_query:
        q = search_query.lower()
        filtered = filtered[
            filtered[COL_PLATE].astype(str).str.lower().str.contains(q, na=False)
            | filtered[COL_NAME].astype(str).str.lower().str.contains(q, na=False)
            | filtered[COL_PHONE].astype(str).str.lower().str.contains(q, na=False)
        ]

    if type_filter != "Semua":
        filtered = filtered[filtered[COL_TYPE] == type_filter]

    if sort_by == "Terbaru":
        try: filtered = filtered.sort_values("Timestamp", ascending=False)
        except Exception: pass
    elif sort_by == "Terlama":
        try: filtered = filtered.sort_values("Timestamp", ascending=True)
        except Exception: pass
    elif sort_by == "Nama A-Z":
        filtered = filtered.sort_values(COL_NAME, ascending=True)

    st.caption(f"Menunjukkan **{len(filtered)}** daripada **{len(pending_df)}** permohonan menunggu.")

    csv_data = convert_df_to_csv(filtered)
    st.download_button(
        "📥 Muat Turun CSV (Senarai Menunggu)",
        data=csv_data,
        file_name=f"pending_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )

    if filtered.empty:
        st.warning("Tiada permohonan sepadan dengan carian anda.")
    else:
        st.markdown("**Pilih vendor untuk tindakan pukal:**")

        bulk_selected = []
        for _, row in filtered.iterrows():
            c1, c2 = st.columns([1, 9])
            with c1:
                checked = st.checkbox("", key=f"bulk_{row[COL_PLATE]}")
            with c2:
                cat_str = f" / {row[COL_CAT]}" if pd.notna(row[COL_CAT]) and str(row[COL_CAT]).strip() else ""
                st.markdown(f"**{row[COL_PLATE]}** — {row[COL_NAME]} ({row[COL_TYPE]}{cat_str})")
            if checked:
                bulk_selected.append(row[COL_PLATE])

        if bulk_selected:
            st.info(f"**{len(bulk_selected)}** vendor dipilih.")
            bc1, bc2 = st.columns(2)
            with bc1:
                if st.button(f"✅ Luluskan {len(bulk_selected)} Vendor", type="primary", use_container_width=True):
                    for plate in bulk_selected:
                        df.loc[df[COL_PLATE] == plate, "Status"] = "Approved"
                        log_action(conn, ADMIN_NAME, "BULK_APPROVE", plate, "Pukal")
                    conn.update(data=df)
                    st.toast(f"✅ {len(bulk_selected)} vendor diluluskan", icon="✅")
                    st.rerun()
            with bc2:
                if st.button(f"❌ Tolak {len(bulk_selected)} Vendor", use_container_width=True):
                    for plate in bulk_selected:
                        df.loc[df[COL_PLATE] == plate, "Status"] = "Rejected"
                        log_action(conn, ADMIN_NAME, "BULK_REJECT", plate, "Pukal")
                    conn.update(data=df)
                    st.toast(f"❌ {len(bulk_selected)} vendor ditolak", icon="❌")
                    st.rerun()

        st.divider()

        st.markdown("**Atau urus satu-satu:**")
        st.dataframe(filtered, hide_index=True, use_container_width=True)

        selected_plate = st.selectbox(
            "Pilih No. Plate",
            filtered[COL_PLATE].tolist(),
            key="pending_selected"
        )

        if selected_plate:
            vendor = df[df[COL_PLATE] == selected_plate].iloc[0]
            v_type = vendor[COL_TYPE]
            v_cat = vendor.get(COL_CAT, "")

            if v_type == "F&B":
                a = df[(df[COL_TYPE] == "F&B") & (df[COL_CAT] == v_cat) & (df["Status"] == "Approved")].shape[0]
                p = df[(df[COL_TYPE] == "F&B") & (df[COL_CAT] == v_cat) & (df["Status"] == "Pending")].shape[0]
                remaining = FB_CATEGORY_LIMIT - (a + p)
                if remaining > 0:
                    st.info(f"Kategori **{v_cat}**: {remaining} slot lagi.")
                else:
                    st.warning(f"Kategori **{v_cat}** telah penuh.")
            else:
                st.info(f"Car Boot komited: {cb_committed} / {CAR_BOOT_LIMIT}")

            st.markdown(
                f"**Vendor:** {vendor[COL_NAME]}  \n"
                f"**Jenis:** {v_type}  \n"
                f"**Kategori F&B:** {v_cat or '-'}  \n"
                f"**Telefon:** {vendor[COL_PHONE]}"
            )

            current_notes = vendor.get("Notes", "") if pd.notna(vendor.get("Notes")) else ""
            new_notes = st.text_area("Nota Admin (pilihan)", value=current_notes, key=f"notes_{selected_plate}")

            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                if st.button("Luluskan", type="primary", use_container_width=True, key=f"approve_{selected_plate}"):
                    ok = True
                    if v_type == "F&B":
                        a = df[(df[COL_TYPE] == "F&B") & (df[COL_CAT] == v_cat) & (df["Status"] == "Approved")].shape[0]
                        if a >= FB_CATEGORY_LIMIT:
                            st.error(f"Kategori '{v_cat}' telah penuh."); ok = False
                        elif fb_committed >= FB_OVERALL_LIMIT:
                            st.error("F&B keseluruhan telah penuh."); ok = False
                    elif v_type == "Car Boot Sales":
                        if cb_committed >= CAR_BOOT_LIMIT:
                            st.error("Car Boot telah penuh."); ok = False

                    if ok:
                        confirm_approve_dialog(selected_plate, vendor[COL_NAME])
            with c2:
                if st.button("Tolak", use_container_width=True, key=f"reject_{selected_plate}"):
                    confirm_reject_dialog(selected_plate, vendor[COL_NAME])
            with c3:
                if st.button("Edit", use_container_width=True, key=f"edit_{selected_plate}"):
                    edit_vendor_dialog(selected_plate)
            with c4:
                if st.button("Simpan Nota", use_container_width=True, key=f"savenotes_{selected_plate}"):
                    df.loc[df[COL_PLATE] == selected_plate, "Notes"] = new_notes
                    conn.update(data=df)
                    st.toast("Nota disimpan", icon="📝")
                    st.rerun()
            with c5:
                if st.button("Padam", use_container_width=True, key=f"delete_{selected_plate}"):
                    confirm_delete_dialog(selected_plate, vendor[COL_NAME])

st.divider()

# ============================================================
# PEMANTAUAN BAYARAN
# ============================================================
st.subheader("Pemantauan Bayaran")
st.caption("Tandakan 'Sudah Bayar' untuk vendor yang telah membuat bayaran.")

approved_df = df[df["Status"] == "Approved"]

if approved_df.empty:
    st.info("Belum ada vendor yang diluluskan.")
else:
    payments = load_sheet_safe(conn, "Payments", ttl=0)
    if payments is None:
        payments = pd.DataFrame()

    with st.form("payment_form"):
        new_paid_status = {}

        for _, row in approved_df.iterrows():
            plate = row[COL_PLATE]

            matched = pd.DataFrame()
            if not payments.empty and "Plate Number" in payments.columns:
                matched = payments[
                    payments["Plate Number"].astype(str).str.upper().str.replace(" ", "")
                    == str(plate).upper().replace(" ", "")
                ]

            cols = st.columns([3, 2, 2, 1])
            cols[0].write(f"**{plate}** — {row[COL_NAME]} ({row[COL_TYPE]})")

            proof_col = None
            if "ProofUrl" in matched.columns:
                proof_col = "ProofUrl"
            elif "Upload Bukti Bayaran" in matched.columns:
                proof_col = "Upload Bukti Bayaran"

            if not matched.empty and proof_col:
                proof = matched.iloc[0][proof_col]
                cols[1].markdown(f"[Bukti Pembayaran]({proof})")

                with cols[2]:
                    if st.checkbox("Preview", key=f"preview_{plate}"):
                        try:
                            st.image(proof, use_container_width=True)
                        except Exception:
                            st.caption("Tidak dapat pratonton")
            else:
                cols[1].write("_Belum upload bukti_")

            new_val = cols[3].checkbox(
                "Sudah Bayar",
                value=bool(row["Paid"]),
                key=f"paid_{plate}",
            )
            new_paid_status[plate] = new_val

        save_clicked = st.form_submit_button("Simpan Status Bayaran", type="primary")

    if save_clicked:
        with st.spinner("Menyimpan..."):
            for plate, is_paid in new_paid_status.items():
                df.loc[df[COL_PLATE] == plate, "Paid"] = is_paid
            conn.update(data=df)
        st.toast("Status bayaran disimpan", icon="💾")
        st.rerun()

st.divider()

# ============================================================
# WHATSAPP GROUP
# ============================================================
st.subheader("Hantar Mesej WhatsApp")
st.caption("Guna WhatsApp Group untuk hantar mesej kepada semua vendor.")

try:
    wa_group = st.secrets["event"]["whatsapp_group"]
except Exception:
    wa_group = ""

if wa_group:
    st.markdown(f"""
    <div style="
        background-color: #f2ebe0;
        border: 1px solid #e8dcc7;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
    ">
        <div>
            <div style="font-weight: 600; color: #292524; font-size: 1rem;">💬 WhatsApp Group Vendor</div>
            <div style="color: #78716c; font-size: 0.9rem; margin-top: 0.25rem;">
                Hantar mesej dalam group — semua vendor terima serentak tanpa spam.
            </div>
        </div>
        <a href="{wa_group}" target="_blank" style="
            background-color: #78350f;
            color: #ffffff;
            padding: 0.6rem 1.25rem;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9rem;
            white-space: nowrap;
        ">Buka Group</a>
    </div>
    """, unsafe_allow_html=True)

with st.expander("Senarai Nombor untuk Follow-up Manual"):
    st.caption("Guna senarai ni untuk WhatsApp Broadcast List (bukan spam, penerima tak nampak satu sama lain).")

    wa1, wa2 = st.columns(2)
    with wa1:
        blast_group = st.selectbox(
            "Pilih kumpulan",
            options=["Car Boot sahaja", "F&B sahaja", "Belum bayar", "Sudah bayar"],
            key="blast_group"
        )
    with wa2:
        blast_type = st.selectbox(
            "Jenis mesej",
            options=["Reminder Bayaran", "Info Event", "Custom"],
            key="blast_type"
        )

    if blast_type == "Custom":
        blast_msg = st.text_area("Mesej custom", height=100)
    elif blast_type == "Reminder Bayaran":
        blast_msg = (
            f"Hi! Ini peringatan mesra — sila buat bayaran sebelum "
            f"{cutoff_date.strftime('%d %b %Y')} untuk kekalkan slot anda. Terima kasih!"
        )
        st.code(blast_msg, language=None)
    else:
        blast_msg = (
            f"Hi! Ini info terkini untuk PFM Mega Car Boot Sale pada "
            f"{EVENT_DATE.strftime('%d %b %Y')}. Jumpa di sana!"
        )
        st.code(blast_msg, language=None)

    if blast_group == "Car Boot sahaja":
        targets = df[df[COL_TYPE] == "Car Boot Sales"]
    elif blast_group == "F&B sahaja":
        targets = df[df[COL_TYPE] == "F&B"]
    elif blast_group == "Belum bayar":
        targets = df[(df["Status"] == "Approved") & (~df["Paid"])]
    else:
        targets = df[(df["Status"] == "Approved") & (df["Paid"])]

    st.info(f"**{len(targets)}** vendor dalam kumpulan ini.")

    if st.button("Jana Senarai Nombor", type="primary"):
        phones = targets[COL_PHONE].dropna().astype(str).tolist()
        clean_phones = []
        for p in phones:
            digits = "".join(filter(str.isdigit, p))
            if digits:
                if digits.startswith("0"):
                    digits = "60" + digits[1:]
                clean_phones.append(digits)

        st.success(f"**{len(clean_phones)}** nombor sedia.")
        st.markdown("**Copy senarai ni → paste dalam WhatsApp Broadcast List:**")
        st.code("\n".join(clean_phones), language=None)
        st.caption("📌 WhatsApp → Settings → Broadcast Lists → New List → Paste nombor → Taip mesej → Hantar")

st.divider()

# ============================================================
# SEMUA VENDOR + DOWNLOAD + ACTION LOG
# ============================================================
with st.expander("📋 Lihat Semua Vendor"):
    # ---- Quick links ----
    try:
        form_url = st.secrets["event"].get("google_form_responses_url", "")
    except Exception:
        form_url = ""

    try:
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    except Exception:
        sheet_url = ""

    quick_col1, quick_col2 = st.columns(2)
    with quick_col1:
        if form_url:
            st.markdown(f"""
            <a href="{form_url}" target="_blank" style="
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.5rem;
                background-color: #78350f;
                color: #ffffff;
                padding: 0.7rem 1rem;
                border-radius: 10px;
                text-decoration: none;
                font-weight: 600;
                font-size: 0.9rem;
                transition: all 0.15s ease;
            ">📋 Buka Google Form Responses</a>
            """, unsafe_allow_html=True)

    with quick_col2:
        if sheet_url:
            st.markdown(f"""
            <a href="{sheet_url}" target="_blank" style="
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.5rem;
                background-color: #ffffff;
                color: #78350f;
                padding: 0.7rem 1rem;
                border-radius: 10px;
                text-decoration: none;
                font-weight: 600;
                font-size: 0.9rem;
                border: 1px solid #d6c4a3;
                transition: all 0.15s ease;
            ">📊 Buka Google Sheet</a>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
    st.divider()

    # ---- Filter ----
    st.markdown("**Tapis mengikut status**")
    status_options = df["Status"].dropna().unique().tolist()
    status_filter = st.multiselect(
        "Tapis mengikut status",
        options=status_options,
        default=status_options,
        label_visibility="collapsed"
    )
    filtered_all = df[df["Status"].isin(status_filter)]

    # ---- Table ----
    st.dataframe(filtered_all, hide_index=True, use_container_width=True)

    # ---- Action row: Delete + CSV ----
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    act_col1, act_col2 = st.columns([3, 1])

    with act_col1:
        plate_to_delete = st.selectbox(
            "Pilih No. Plate untuk dipadam",
            options=[""] + filtered_all[COL_PLATE].tolist(),
            key="delete_plate_select"
        )

    with act_col2:
        st.markdown("<div style='height: 1.75rem;'></div>", unsafe_allow_html=True)
        if st.button("🗑️ Padam", type="primary", use_container_width=True):
            if plate_to_delete:
                row = df[df[COL_PLATE] == plate_to_delete]
                name = row.iloc[0][COL_NAME] if not row.empty else "-"
                confirm_delete_dialog(plate_to_delete, name)
            else:
                st.error("Sila pilih No. Plate.")

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    csv_all = convert_df_to_csv(filtered_all)
    st.download_button(
        "📥 Muat Turun CSV (Semua Vendor)",
        data=csv_all,
        file_name=f"vendors_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )

with st.expander("📜 Log Tindakan Admin"):
    logs = load_sheet_safe(conn, "Log", ttl=0)
    if logs is None or logs.empty:
        st.markdown("""
        <div style="
            background-color: #f0f9ff;
            border: 1px solid #bae6fd;
            border-radius: 10px;
            padding: 1rem 1.25rem;
            color: #0c4a6e;
            font-size: 0.92rem;
        ">
            📭 Belum ada rekod tindakan admin.
        </div>
        """, unsafe_allow_html=True)
    else:
        logs_sorted = logs.sort_values("Timestamp", ascending=False)
        st.dataframe(logs_sorted, hide_index=True, use_container_width=True)

        csv_logs = convert_df_to_csv(logs_sorted)
        st.download_button(
            "📥 Muat Turun Log CSV",
            data=csv_logs,
            file_name=f"log_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )