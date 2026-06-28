# cd "code\gurobi1203\Code Skripsi"
# streamlit run app.py

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import json
import os
import time

from core_objects import Bin, Item
from ffd_algorithm import run_ffd
from sa_algorithm import run_sa
from milp_algorithm import run_milp  # IMPORT BARU UNTUK GUROBI
from generate_pdf import generate_surat_jalan_pdf
from inventory_db import (
    catat_pengiriman_gudang,
    catat_masuk_toko,
    catat_keluar_toko,
    catat_koreksi_toko,
    load_inventory
)


# ==========================================
# DEFINISI INDEKS MESH3D
# ==========================================
IDX_I = (0, 0, 4, 4, 0, 0, 3, 3, 0, 0, 1, 1)
IDX_J = (1, 2, 5, 6, 1, 5, 2, 6, 3, 7, 2, 6)
IDX_K = (2, 3, 6, 7, 5, 4, 6, 7, 7, 4, 6, 5)
# Warna per jenis barang
ITEM_COLORS = {
    "B-001": "#E74C3C",
    "B-002": "#3498DB",
    "B-003": "#2ECC71",
    "B-004": "#F39C12",
    "B-005": "#9B59B6",
    "B-006": "#1ABC9C",
    "B-007": "#E67E22",
    "B-008": "#34495E",
    "T-001": "#E91E63",
    "T-002": "#00BCD4",
    "T-003": "#8BC34A",
}

st.set_page_config(page_title="Sistem Logistik 3D-BPP", layout="wide")

# ==========================================
# DATABASE JSON
# ==========================================
DB_FILE = "database_stok.json"


def init_db():
    if not os.path.exists(DB_FILE):
        default_data = {
            "Toko 1": {
                "B-001": 50,
                "B-002": 50,
                "B-003": 50,
                "B-004": 50,
                "B-005": 50,
                "B-006": 50,
                "B-007": 50,
                "B-008": 50,
                "T-001": 50,
                "T-002": 50,
                "T-003": 50
            },
            "Toko 2": {
                "B-001": 50,
                "B-002": 50,
                "B-003": 50,
                "B-004": 50,
                "B-005": 50,
                "B-006": 50,
                "B-007": 50,
                "B-008": 50,
                "T-001": 50,
                "T-002": 50,
                "T-003": 50
            }
        }
        save_db(default_data)


def load_db():
    with open(DB_FILE, "r") as f:
        return json.load(f)


def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)


init_db()

# ==========================================
# SESSION STATE
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = ""

if "siap_kirim" not in st.session_state:
    st.session_state.siap_kirim = False
if "hasil_sa" not in st.session_state:
    st.session_state.hasil_sa = None
if "hasil_sa_2" not in st.session_state:
    st.session_state.hasil_sa_2 = None
if "waktu_eksekusi" not in st.session_state:
    st.session_state.waktu_eksekusi = 0.0
# ==========================================
# DATA MASTER
# ==========================================
DATA_MASTER = [
    {"ID": "B-001", "Nama": "Bal Botol 600ml", "P": 69, "L": 46, "T": 24},
    {"ID": "B-002", "Nama": "Bal Botol 250ml (Tipis)", "P": 52, "L": 44, "T": 16},
    {"ID": "B-003", "Nama": "Bal Botol 250ml (Sedang)", "P": 52, "L": 44, "T": 16},
    {"ID": "B-004", "Nama": "Bal Botol 250ml (Tebal)", "P": 52, "L": 44, "T": 16},
    {"ID": "B-005", "Nama": "Bal Botol 330ml", "P": 75, "L": 47, "T": 18},
    {"ID": "B-006", "Nama": "Bal Botol 1000ml (Kecil)", "P": 40, "L": 36, "T": 24},
    {"ID": "B-007", "Nama": "Bal Botol 1000ml (Sedang)", "P": 50, "L": 36, "T": 24},
    {"ID": "B-008", "Nama": "Bal Botol 1000ml (Besar)", "P": 100, "L": 36, "T": 24},
    {"ID": "T-001", "Nama": "Bal Toples 600ml", "P": 64, "L": 46, "T": 11},
    {"ID": "T-002", "Nama": "Bal Toples 400ml", "P": 82, "L": 60, "T": 7},
    {"ID": "T-003", "Nama": "Bal Toples 800ml", "P": 80, "L": 65, "T": 13},
]

if "solver_input" not in st.session_state:
    df_init = pd.DataFrame(DATA_MASTER)
    df_init["Qty Kirim"] = 0
    df_init["Tujuan (Rute)"] = "Belum Dipilih"
    st.session_state.solver_input = df_init

# ==========================================
# VISUALISASI 3D
# ==========================================
def draw_3d_bin(bin_obj):

    fig = go.Figure()

    L, W, H = bin_obj.length, bin_obj.width, bin_obj.height

    fig.add_trace(
        go.Scatter3d(
            x=(0, L, L, 0, 0, 0, L, L, 0, 0, 0, 0, L, L, L, L),
            y=(0, 0, W, W, 0, 0, 0, W, W, 0, W, W, W, W, 0, 0),
            z=(0, 0, 0, 0, 0, H, H, H, H, H, H, 0, 0, H, H, 0),
            mode='lines',
            line=dict(color='red', width=6),
            hoverinfo='none',
            showlegend=False
        )
    )

    for item in bin_obj.fitted_items:

        x, y, z    = item.x, item.y, item.z
        dx, dy, dz = item.length, item.width, item.height
        base_id    = item.item_id.split("_")[0]
        item_color = ITEM_COLORS.get(base_id, "#95A5A6")

        x_pts = (x, x+dx, x+dx, x, x, x+dx, x+dx, x)
        y_pts = (y, y, y+dy, y+dy, y, y, y+dy, y+dy)
        z_pts = (z, z, z, z, z+dz, z+dz, z+dz, z+dz)

        fig.add_trace(
            go.Mesh3d(
                x=x_pts,
                y=y_pts,
                z=z_pts,
                i=IDX_I,
                j=IDX_J,
                k=IDX_K,
                color=item_color,
                opacity=0.6,
                text=f"""
                <b>ID:</b> {item.item_id}<br>
                <b>Rute:</b> {item.route_priority}<br>
                <b>Posisi:</b> ({item.x}, {item.y}, {item.z})
                """,
                hoverinfo="text",
                showlegend=False
            )
        )

        x_edges = (x, x+dx, None, x+dx, x+dx, None, x+dx, x, None, x, x, None, x, x+dx, None, x+dx, x+dx, None, x+dx, x, None, x, x, None, x, x, None, x+dx, x+dx, None, x+dx, x+dx, None, x, x)
        y_edges = (y, y, None, y, y+dy, None, y+dy, y+dy, None, y+dy, y, None, y, y, None, y, y+dy, None, y+dy, y+dy, None, y+dy, y, None, y, y, None, y, y, None, y+dy, y+dy, None, y+dy, y+dy)
        z_edges = (z, z, None, z, z, None, z, z, None, z, z, None, z+dz, z+dz, None, z+dz, z+dz, None, z+dz, z+dz, None, z+dz, z+dz, None, z, z+dz, None, z, z+dz, None, z, z+dz, None, z, z+dz)

        fig.add_trace(
            go.Scatter3d(
                x=x_edges,
                y=y_edges,
                z=z_edges,
                mode='lines',
                line=dict(color='black', width=3),
                hoverinfo='none',
                showlegend=False
            )
        )

    fig.update_layout(
        scene=dict(
            xaxis=dict(range=[0, L+15]),
            yaxis=dict(range=[0, W+15]),
            zaxis=dict(range=[0, H+15]),
            aspectmode='data'
        ),
        margin=dict(l=0, r=0, b=0, t=0)
    )

    return fig

def generate_3d_views(bin_obj):
    """Membuat 6 gambar PNG dari sudut pandang berbeda"""
    views = [
        ("1. Tampak Depan",    dict(x=0,    y=-2.5, z=0.5)),
        ("2. Tampak Belakang", dict(x=0,    y=2.5,  z=0.5)),
        ("3. Tampak Kanan",    dict(x=2.5,  y=0,    z=0.5)),
        ("4. Tampak Kiri",     dict(x=-2.5, y=0,    z=0.5)),
        ("5. Tampak Atas",     dict(x=0,    y=0,    z=2.5)),
        ("6. Tampak Bawah",    dict(x=0.1,  y=0.1,  z=-2.5)),
    ]

    fig = draw_3d_bin(bin_obj)
    images = []

    for label, eye in views:
        fig.update_layout(
            scene_camera=dict(eye=eye),
            title=dict(text=label, x=0.5, font=dict(size=14))
        )
        img_bytes = fig.to_image(format="png", width=800, height=600)
        images.append((label, img_bytes))

    return images

# ==========================================
# LOGIN PAGE
# ==========================================
def login_page():

    st.markdown("<br><br><br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col2:

        st.markdown(
            "<h2 style='text-align:center;'>Sistem Distribusi & Optimasi Logistik</h2>",
            unsafe_allow_html=True
        )

        st.markdown(
            "<h4 style='text-align:center;color:gray;'>Silakan Login</h4>",
            unsafe_allow_html=True
        )

        with st.form("login_form"):

            username = st.text_input("Username")
            password = st.text_input("Password", type="password")

            submit = st.form_submit_button(
                "Login",
                use_container_width=True
            )

            if submit:

                if username == "admin1" and password == "Gudang1":
                    st.session_state.logged_in = True
                    st.session_state.role = "Gudang"
                    st.rerun()

                elif username == "admin2" and password == "Toko1":
                    st.session_state.logged_in = True
                    st.session_state.role = "Toko 1"
                    st.rerun()

                elif username == "admin3" and password == "Toko2":
                    st.session_state.logged_in = True
                    st.session_state.role = "Toko 2"
                    st.rerun()

                else:
                    st.error("Username atau Password salah!")

# ==========================================
# HALAMAN TOKO
# ==========================================
def halaman_toko():

    nama_toko = st.session_state.role
    db_stok   = load_db()

    st.title(f"Dashboard {nama_toko}")

    tab1, tab2, tab3 = st.tabs(["📦 Kelola Stok", "🔧 Koreksi Stok", "📋 Riwayat Stok"])

    # ── TAB 1: KELOLA STOK ──────────────────────────────────
    with tab1:

        colA, colB = st.columns(2)
        with colA:
            st.write("Pantau stok barang toko.")
        with colB:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()

        tabel_stok = []
        for item in DATA_MASTER:
            tabel_stok.append({
                "ID Barang"          : item["ID"],
                "Nama Barang"        : item["Nama"],
                "Sisa Stok"          : db_stok[nama_toko][item["ID"]],
                "Kurangi Stok (Jual)": 0
            })

        edited_df = st.data_editor(
            pd.DataFrame(tabel_stok),
            disabled=["ID Barang", "Nama Barang", "Sisa Stok"],
            use_container_width=True,
            hide_index=True
        )

        if st.button("Simpan Pengurangan Stok", type="primary"):
            db_stok = load_db()

            # Validasi dulu sebelum simpan
            ada_over = False
            pesan_over = []

            for _, row in edited_df.iterrows():
                kurang = int(row["Kurangi Stok (Jual)"])
                if kurang > 0:
                    stok_tersedia = db_stok[nama_toko][row["ID Barang"]]
                    if kurang > stok_tersedia:
                        ada_over = True
                        pesan_over.append(
                            f"**{row['Nama Barang']}** ({row['ID Barang']}): "
                            f"stok tersedia {stok_tersedia}, diminta {kurang}"
                        )

            if ada_over:
                st.warning(
                    "⚠️ Input melebihi stok yang tersedia, perbaiki terlebih dahulu:\n\n" +
                    "\n".join(f"- {p}" for p in pesan_over)
                )
            else:
                for _, row in edited_df.iterrows():
                    kurang = int(row["Kurangi Stok (Jual)"])
                    if kurang > 0:
                        db_stok[nama_toko][row["ID Barang"]] -= kurang

                save_db(db_stok)
                catat_keluar_toko(nama_toko, edited_df, DATA_MASTER)
                st.success("Stok berhasil diperbarui!")
                st.rerun()

    # ── TAB 2: KOREKSI STOK ─────────────────────────────────  ← TAMBAHKAN INI
    with tab2:

        st.write("Gunakan fitur ini untuk **mengoreksi stok** jika terjadi kesalahan input penjualan.")
        st.warning("⚠️ Fitur ini hanya untuk koreksi kesalahan, bukan untuk mencatat barang masuk dari gudang.")

        db_stok  = load_db()
        nama_map = {d["ID"]: d["Nama"] for d in DATA_MASTER}

        tabel_koreksi = []
        for item in DATA_MASTER:
            tabel_koreksi.append({
                "ID Barang"            : item["ID"],
                "Nama Barang"          : item["Nama"],
                "Sisa Stok"            : db_stok[nama_toko][item["ID"]],
                "Tambah Stok (Koreksi)": 0
            })

        edited_koreksi = st.data_editor(
            pd.DataFrame(tabel_koreksi),
            disabled=["ID Barang", "Nama Barang", "Sisa Stok"],
            use_container_width=True,
            hide_index=True
        )

        if st.button("💾 Simpan Koreksi Stok", type="primary"):
            db_stok    = load_db()
            ada_koreksi = False

            for _, row in edited_koreksi.iterrows():
                tambah = int(row["Tambah Stok (Koreksi)"])
                if tambah > 0:
                    ada_koreksi = True
                    db_stok[nama_toko][row["ID Barang"]] += tambah
                    catat_koreksi_toko(
                        nama_toko,
                        row["ID Barang"],
                        row["Nama Barang"],
                        tambah
                    )

            if ada_koreksi:
                save_db(db_stok)
                st.success("Koreksi stok berhasil disimpan!")
                st.rerun()
            else:
                st.warning("Tidak ada koreksi yang diinput.")

    # ── TAB 3: RIWAYAT STOK ─────────────────────────────────
    with tab3:

        if st.button("🔄 Refresh Riwayat", use_container_width=True):
            st.rerun()

        inv     = load_inventory()
        riwayat = inv["riwayat_toko"].get(nama_toko, [])

        if not riwayat:
            st.info("Belum ada riwayat transaksi.")
        else:
            df_riwayat = pd.DataFrame(riwayat)
            df_riwayat = df_riwayat.rename(columns={
                "timestamp"  : "Waktu",
                "jenis"      : "Jenis",
                "id_barang"  : "ID Barang",
                "nama_barang": "Nama Barang",
                "qty"        : "Qty"
            })
            df_riwayat = df_riwayat[["Waktu", "Jenis", "ID Barang", "Nama Barang", "Qty"]]

            filter_jenis = st.selectbox(
                "Filter Transaksi",
                ["Semua", "Masuk", "Keluar", "Koreksi"],
                key="filter_riwayat_toko"
            )
            if filter_jenis != "Semua":
                df_riwayat = df_riwayat[df_riwayat["Jenis"] == filter_jenis]
                
            def warnai(row):
                if row["Jenis"] == "Masuk":
                    return ["background-color: #d4edda; color: black; text-align: left"] * len(row)
                elif row["Jenis"] == "Koreksi":
                    return ["background-color: #fff3cd; color: black; text-align: left"] * len(row)
                else:
                    return ["background-color: #f8d7da; color: black; text-align: left"] * len(row)

            st.dataframe(
                df_riwayat.sort_values("Waktu", ascending=False).style.apply(warnai, axis=1).set_properties(**{'text-align': 'left'}),
                use_container_width=True,
                hide_index=True
            )
            st.caption(f"Total {len(df_riwayat)} transaksi ditemukan.")

# ==========================================
# HALAMAN GUDANG
# ==========================================
def halaman_gudang():

    menu = st.sidebar.radio(
        "Menu Gudang",
        ["Dashboard Gudang", "Solver", "Riwayat Pengiriman"] # MENU 
    )

    db_stok = load_db()

    # ======================================
    # DASHBOARD
    # ======================================
    if menu == "Dashboard Gudang":
        
        st.title("Dashboard Admin Gudang")
        
        colA, colB = st.columns(2)
        
        with colA:
            st.write("Pantau stok seluruh toko secara real-time.")
        
        with colB:
            if st.button(
                "🔄 Refresh Data",
                use_container_width=True
            ):
                st.rerun()
        
        c1, c2 = st.columns(2)

        nama_map = {d["ID"]: d["Nama"] for d in DATA_MASTER}

        with c1:
            st.subheader("Stok Toko 1")
            st.dataframe(
                pd.DataFrame([
                    {"ID": k, "Nama Barang": nama_map.get(k, k), "Sisa Stok": v}
                    for k, v in db_stok["Toko 1"].items()
                ]),
                use_container_width=True, hide_index=True
            )

        with c2:
            st.subheader("Stok Toko 2")
            st.dataframe(
                pd.DataFrame([
                    {"ID": k, "Nama Barang": nama_map.get(k, k), "Sisa Stok": v}
                    for k, v in db_stok["Toko 2"].items()
                ]),
                use_container_width=True, hide_index=True
            )
           

    # ======================================
    # SOLVER
    # ======================================
    elif menu == "Solver":

        st.title("Solver Optimasi 3D-BPP")

        with st.expander("Lihat Sisa Stok Toko (Klik untuk Buka)"):
            c1, c2 = st.columns(2)
            c1.markdown("**Stok Toko 1**")
            c1.dataframe(pd.DataFrame([{"ID": k, "Sisa": v} for k, v in db_stok["Toko 1"].items()]), hide_index=True, use_container_width=True)
            c2.markdown("**Stok Toko 2**")
            c2.dataframe(pd.DataFrame([{"ID": k, "Sisa": v} for k, v in db_stok["Toko 2"].items()]), hide_index=True, use_container_width=True)

        st.markdown("---")
        st.subheader("⚙️ Pengaturan Pengiriman")

        col_k, col_u = st.columns(2)
        with col_k:
            jumlah_kendaraan = st.radio(
                "Jumlah Kendaraan", [1, 2],
                horizontal=True,
                format_func=lambda x: f"{x} Kendaraan"
            )
        with col_u:
            ukuran_tipe = st.radio(
                "Ukuran Kontainer",
                ["Standar (220×148×80 cm)", "Custom"],
                horizontal=True
            )

        if ukuran_tipe == "Custom":
            st.caption("Masukkan ukuran kontainer dalam satuan cm.")
            c1, c2, c3 = st.columns(3)
            panjang = c1.number_input("Panjang (cm)", min_value=1, value=220)
            lebar   = c2.number_input("Lebar (cm)",   min_value=1, value=148)
            tinggi  = c3.number_input("Tinggi (cm)",  min_value=1, value=80)
        else:
            panjang, lebar, tinggi = 220, 148, 80

        milp_time_limit = st.slider(
            "⏱️ Batas Waktu MILP (detik)",
            min_value=60, max_value=36000, value=36000, step=60,
            help="Hanya berlaku saat menjalankan MILP Gurobi."
        )

        st.info("💡 **Aturan LIFO:** Rute 1 (Toko 2) = paling dalam. Rute 2 (Toko 1) = dekat pintu.")
        st.markdown("---")

        # ── FORM INPUT ───────────────────────────────────────
        with st.form(key="form_input_solver"):
            edited_input = st.data_editor(
                st.session_state.solver_input,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Tujuan (Rute)": st.column_config.SelectboxColumn(
                        "Tujuan",
                        options=[
                            "Belum Dipilih",
                            "Toko 1 (Dekat)",
                            "Toko 2 (Jauh)"
                        ]
                    )
                }
            )
            konfirmasi_input = st.form_submit_button(
                "✅ Konfirmasi Input",
                use_container_width=True
            )

        if konfirmasi_input:
            st.session_state.solver_input = edited_input
            st.success("Input tersimpan! Sekarang pilih metode yang ingin dijalankan.")

        # ── 3 TOMBOL RUN ─────────────────────────────────────
        st.markdown("---")
        st.subheader("▶ Jalankan Metode")
        btn1, btn2, btn3 = st.columns(3)

        def buat_pesanan():
            pesanan   = []
            ada_error = False
            for _, row in st.session_state.solver_input.iterrows():
                qty    = int(row["Qty Kirim"])
                tujuan = row["Tujuan (Rute)"]
                if qty > 0:
                    if tujuan == "Belum Dipilih":
                        ada_error = True
                        break
                    rute_map = {"Toko 2 (Jauh)": 1, "Toko 1 (Dekat)": 2}
                    rute = rute_map.get(tujuan, 0)
                    for i in range(qty):
                        pesanan.append(Item(f"{row['ID']}_{i+1}", row["P"], row["L"], row["T"], rute))
            return pesanan, ada_error

        with btn1:
            if st.button("🔵 Jalankan FFD", use_container_width=True, type="primary"):
                pesanan, err = buat_pesanan()
                if err:   st.error("Masih ada rute belum dipilih.")
                elif not pesanan: st.warning("Isi Qty terlebih dahulu.")
                else:
                    with st.spinner("FFD berjalan..."):
                        t0 = time.time()
                        h1 = run_ffd(Bin(panjang, lebar, tinggi), pesanan)
                        h2 = None
                        if jumlah_kendaraan == 2:
                            sisa = [i for i in pesanan if i.item_id not in {x.item_id for x in h1.fitted_items}]
                            if sisa: h2 = run_ffd(Bin(panjang, lebar, tinggi), sisa)
                        st.session_state.hasil_ffd   = h1
                        st.session_state.hasil_ffd2  = h2
                        st.session_state.waktu_ffd   = time.time() - t0
                        st.session_state.total_diminta = len(pesanan)
                        st.session_state.jumlah_kendaraan = jumlah_kendaraan
                        st.session_state.siap_kirim  = True

        with btn2:
            if st.button("🟢 Jalankan FFD+SA", use_container_width=True, type="primary"):
                pesanan, err = buat_pesanan()
                if err:   st.error("Masih ada rute belum dipilih.")
                elif not pesanan: st.warning("Isi Qty terlebih dahulu.")
                else:
                    with st.spinner("FFD+SA berjalan..."):
                        t0      = time.time()
                        _tmp    = run_ffd(Bin(panjang, lebar, tinggi), pesanan)
                        sisa_sa = [i for i in pesanan if i.item_id not in {x.item_id for x in _tmp.fitted_items}]
                        h1      = run_sa(Bin(panjang, lebar, tinggi), list(_tmp.fitted_items) + sisa_sa)
                        h2      = None
                        if jumlah_kendaraan == 2:
                            sisa = [i for i in pesanan if i.item_id not in {x.item_id for x in h1.fitted_items}]
                            if sisa:
                                _tmp2 = run_ffd(Bin(panjang, lebar, tinggi), sisa)
                                h2    = run_sa(Bin(panjang, lebar, tinggi), list(_tmp2.fitted_items))
                        st.session_state.hasil_sa    = h1
                        st.session_state.hasil_sa2   = h2
                        st.session_state.waktu_sa    = time.time() - t0
                        st.session_state.total_diminta = len(pesanan)
                        st.session_state.jumlah_kendaraan = jumlah_kendaraan
                        st.session_state.siap_kirim  = True

        with btn3:
            if st.button("🟡 Jalankan MILP Gurobi", use_container_width=True, type="primary"):
                pesanan, err = buat_pesanan()
                if err:   st.error("Masih ada rute belum dipilih.")
                elif not pesanan: st.warning("Isi Qty terlebih dahulu.")
                else:
                    with st.spinner("MILP berjalan..."):
                        t0 = time.time()
                        h1 = None
                        h2 = None
                        try:
                            h1 = run_milp(Bin(panjang, lebar, tinggi), pesanan, time_limit=milp_time_limit)
                            if jumlah_kendaraan == 2:
                                sisa = [i for i in pesanan if i.item_id not in {x.item_id for x in h1.fitted_items}]
                                if sisa: h2 = run_milp(Bin(panjang, lebar, tinggi), sisa, time_limit=milp_time_limit)
                        except Exception as e:
                            st.error(f"❌ MILP Error: {e}")
                        st.session_state.hasil_milp  = h1
                        st.session_state.hasil_milp2 = h2
                        st.session_state.waktu_milp  = time.time() - t0
                        st.session_state.total_diminta = len(pesanan)
                        st.session_state.jumlah_kendaraan = jumlah_kendaraan
                        st.session_state.siap_kirim  = True

        # ── HASIL 3 KOLOM BERDAMPINGAN ────────────────────────
        if st.session_state.siap_kirim:

            hasil_ffd   = st.session_state.get("hasil_ffd")
            hasil_ffd2  = st.session_state.get("hasil_ffd2")
            hasil_sa    = st.session_state.get("hasil_sa")
            hasil_sa2   = st.session_state.get("hasil_sa2")
            hasil_milp  = st.session_state.get("hasil_milp")
            hasil_milp2 = st.session_state.get("hasil_milp2")
            jml_kend    = st.session_state.jumlah_kendaraan
            total_dim   = st.session_state.total_diminta
            vol_bin     = panjang * lebar * tinggi

            def info_metode(h1, h2):
                if not h1:
                    return None, None, None
                muat = len(h1.fitted_items) + (len(h2.fitted_items) if h2 else 0)
                vol  = sum(i.length*i.width*i.height for i in h1.fitted_items)
                if h2: vol += sum(i.length*i.width*i.height for i in h2.fitted_items)
                bins = 2 if h2 and len(h2.fitted_items) > 0 else 1
                fr   = (vol / (vol_bin * bins)) * 100
                return muat, fr, total_dim - muat

            muat_ffd,  fr_ffd,  sisa_ffd  = info_metode(hasil_ffd,  hasil_ffd2)
            muat_sa,   fr_sa,   sisa_sa   = info_metode(hasil_sa,   hasil_sa2)
            muat_milp, fr_milp, sisa_milp = info_metode(hasil_milp, hasil_milp2)

            # ── TABEL PERBANDINGAN ────────────────────────
            st.markdown("---")
            st.subheader("📊 Tabel Perbandingan")
            rows_cmp = []
            if hasil_ffd:
                rows_cmp.append(["FFD",
                    f"{st.session_state.get('waktu_ffd', 0):.4f}",
                    muat_ffd, f"{fr_ffd:.2f}%", sisa_ffd])
            if hasil_sa:
                rows_cmp.append(["FFD+SA",
                    f"{st.session_state.get('waktu_sa', 0):.4f}",
                    muat_sa, f"{fr_sa:.2f}%", sisa_sa])
            if hasil_milp:
                rows_cmp.append(["MILP Gurobi",
                    f"{st.session_state.get('waktu_milp', 0):.4f}",
                    muat_milp, f"{fr_milp:.2f}%", sisa_milp])
            if rows_cmp:
                st.dataframe(
                    pd.DataFrame(rows_cmp, columns=["Metode", "Waktu (detik)", "Barang Muat", "Fill Rate", "Tertinggal"]),
                    use_container_width=True, hide_index=True
                )

            # ── VISUALISASI 3D BERDAMPINGAN ───────────────
            st.markdown("---")
            st.subheader("🗂️ Visualisasi 3D Perbandingan")
            col1, col2, col3 = st.columns(3)

            def tampil_kolom(col, h1, h2, label, waktu_key):
                with col:
                    st.markdown(f"### {label}")
                    if not h1:
                        st.info("Belum dijalankan.")
                        return
                    muat, fr, sisa = info_metode(h1, h2)
                    st.metric("Fill Rate", f"{fr:.2f}%")
                    st.metric("Waktu", f"{st.session_state.get(waktu_key, 0):.4f}s")
                    if sisa > 0:
                        st.warning(f"⚠️ {sisa} bal tertinggal")
                    else:
                        st.success("✅ Semua muat")
                    # Kendaraan 1
                    st.markdown("**🚛 Kendaraan 1**")
                    st.plotly_chart(draw_3d_bin(h1), use_container_width=True,
                                    key=f"chart_{label}_1")
                    # Kendaraan 2
                    if jml_kend == 2 and h2 and len(h2.fitted_items) > 0:
                        st.markdown("**🚛 Kendaraan 2**")
                        st.plotly_chart(draw_3d_bin(h2), use_container_width=True,
                                        key=f"chart_{label}_2")

            tampil_kolom(col1, hasil_ffd,  hasil_ffd2,  "FFD",  "waktu_ffd")
            tampil_kolom(col2, hasil_sa,   hasil_sa2,   "FFDSA","waktu_sa")
            tampil_kolom(col3, hasil_milp, hasil_milp2, "MILP", "waktu_milp")

            # ── MANIFEST & DOWNLOAD PER METODE ───────────
            st.markdown("---")
            st.subheader("📋 Manifest & Surat Jalan")

            def tampil_manifest_download(h1, h2, label):
                if not h1: return
                st.markdown(f"**📄 Manifest {label}**")
                for h, nomor in [(h1, 1), (h2, 2)]:
                    if not h or len(h.fitted_items) == 0: continue
                    st.markdown(f"**Kendaraan {nomor}**")
                    data_m = []
                    for item in h.fitted_items:
                        base_id = item.item_id.split("_")[0]
                        tujuan_aktual = "Toko 1" if item.route_priority == 2 else "Toko 2"
                        nama_map = {d["ID"]: d["Nama"] for d in DATA_MASTER}
                        data_m.append({
                            "ID Barang"  : base_id,
                            "Nama Barang": nama_map.get(base_id, base_id),
                            "Kode Muat"  : item.item_id,
                            "Tujuan"     : tujuan_aktual,
                            "Koordinat"  : f"X:{item.x}, Y:{item.y}, Z:{item.z}"
                        })
                    df_m = pd.DataFrame(data_m)
                    st.dataframe(df_m, use_container_width=True, hide_index=True)
                    with st.spinner("Menyiapkan PDF..."):
                        images_3d = generate_3d_views(h)
                    pdf = generate_surat_jalan_pdf(df_m, images_3d=images_3d)
                    st.download_button(
                        f"📥 Download Surat Jalan {label} - Kendaraan {nomor}",
                        data=pdf,
                        file_name=f"SJ_{label}_K{nomor}.pdf",
                        mime="application/pdf",
                        key=f"dl_{label}_{nomor}"
                    )

            tampil_manifest_download(hasil_ffd,  hasil_ffd2,  "FFD")
            tampil_manifest_download(hasil_sa,   hasil_sa2,   "FFDSA")
            tampil_manifest_download(hasil_milp, hasil_milp2, "MILP")

            # ── KONFIRMASI KIRIM ─────────────────────────
            st.markdown("---")
            st.subheader("🚚 Konfirmasi Pengiriman")

            pilihan_tersedia = []
            if hasil_ffd:  pilihan_tersedia.append("FFD")
            if hasil_sa:   pilihan_tersedia.append("FFD+SA")
            if hasil_milp: pilihan_tersedia.append("MILP Gurobi")

            if pilihan_tersedia:
                metode_kirim = st.selectbox(
                    "Pilih hasil metode yang akan dikirim:", pilihan_tersedia
                )
                if st.button("🚚 Konfirmasi Kirim & Update Stok Toko", type="primary"):
                    if metode_kirim == "FFD":         h1, h2 = hasil_ffd,  hasil_ffd2
                    elif metode_kirim == "FFD+SA":    h1, h2 = hasil_sa,   hasil_sa2
                    else:                             h1, h2 = hasil_milp, hasil_milp2

                    db_stok_terbaru = load_db()
                    semua_fitted    = list(h1.fitted_items)
                    if h2: semua_fitted += list(h2.fitted_items)

                    for item in semua_fitted:
                        base_id     = item.item_id.split("_")[0]
                        toko_tujuan = "Toko 1" if item.route_priority == 2 else "Toko 2"
                        db_stok_terbaru[toko_tujuan][base_id] += 1

                    save_db(db_stok_terbaru)
                    catat_pengiriman_gudang(semua_fitted, DATA_MASTER)
                    catat_masuk_toko(semua_fitted, DATA_MASTER)

                    st.session_state.solver_input['Qty Kirim']     = 0
                    st.session_state.solver_input['Tujuan (Rute)'] = "Belum Dipilih"
                    st.session_state.siap_kirim                    = False
                    st.session_state.hasil_ffd  = None
                    st.session_state.hasil_sa   = None
                    st.session_state.hasil_milp = None
                    st.success("Stok berhasil diupdate!")
                    st.rerun()
            else:
                st.info("Jalankan minimal satu metode terlebih dahulu.")

    # ======================================
    # RIWAYAT PENGIRIMAN GUDANG
    # ======================================
    elif menu == "Riwayat Pengiriman":

        st.title("Riwayat Pengiriman Gudang")

        inv = load_inventory()
        riwayat = inv["riwayat_gudang"]

        colA, colB = st.columns(2)
        with colB:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()

        if not riwayat:
            st.info("Belum ada riwayat pengiriman.")
        else:
            df_riwayat = pd.DataFrame(riwayat)
            df_riwayat = df_riwayat.rename(columns={
                "timestamp"  : "Waktu",
                "tujuan"     : "Tujuan",
                "id_barang"  : "ID Barang",
                "nama_barang": "Nama Barang",
                "qty"        : "Qty Terkirim"
            })
            df_riwayat = df_riwayat[["Waktu", "Tujuan", "ID Barang", "Nama Barang", "Qty Terkirim"]]

            tujuan_filter = st.selectbox(
                "Filter Tujuan",
                ["Semua", "Toko 1", "Toko 2"]
            )
            if tujuan_filter != "Semua":
                df_riwayat = df_riwayat[df_riwayat["Tujuan"] == tujuan_filter]

            st.dataframe(
                df_riwayat.sort_values("Waktu", ascending=False),
                use_container_width=True,
                hide_index=True
            )
            st.caption(f"Total {len(df_riwayat)} transaksi ditemukan.")
            
            
# ==========================================
# ROUTING
# ==========================================
if not st.session_state.logged_in:

    login_page()

else:

    colA, colB = st.sidebar.columns(2)

    with colA:
        st.write(
            f"Login: **{st.session_state.role}**"
        )

    with colB:

        if st.button(
            "Keluar",
            use_container_width=True
        ):

            st.session_state.logged_in = False
            st.session_state.role = ""
            st.session_state.siap_kirim = False

            st.rerun()

    st.sidebar.markdown("---")

    if st.session_state.role == "Gudang":
        halaman_gudang()

    elif st.session_state.role in ["Toko 1", "Toko 2"]:
        halaman_toko()