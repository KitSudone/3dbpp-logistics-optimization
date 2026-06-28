import json
import os
from datetime import datetime

INVENTORY_FILE = "inventory_riwayat.json"


def init_inventory():
    if not os.path.exists(INVENTORY_FILE):
        default = {
            "riwayat_gudang": [],
            "riwayat_toko": {
                "Toko 1": [],
                "Toko 2": []
            }
        }
        save_inventory(default)


def load_inventory():
    with open(INVENTORY_FILE, "r") as f:
        return json.load(f)


def save_inventory(data):
    with open(INVENTORY_FILE, "w") as f:
        json.dump(data, f, indent=4)


def get_timestamp():
    return datetime.now().strftime("%d-%m-%Y %H:%M:%S")


def catat_pengiriman_gudang(fitted_items, data_master_list):
    """
    Dipanggil saat gudang klik 'Konfirmasi Kirim'.
    Mencatat setiap item yang dikirim beserta tujuan, qty, dan waktu.
    """
    inv = load_inventory()
    ts  = get_timestamp()

    # Rekap: {(id_barang, tujuan): qty}
    rekap = {}
    for item in fitted_items:
        base_id    = item.item_id.split("_")[0]
        toko_tujuan = "Toko 1" if item.route_priority == 2 else "Toko 2"
        key = (base_id, toko_tujuan)
        rekap[key] = rekap.get(key, 0) + 1

    # Mapping id → nama
    nama_map = {d["ID"]: d["Nama"] for d in data_master_list}

    for (base_id, toko_tujuan), qty in rekap.items():
        inv["riwayat_gudang"].append({
            "timestamp" : ts,
            "tujuan"    : toko_tujuan,
            "id_barang" : base_id,
            "nama_barang": nama_map.get(base_id, base_id),
            "qty"       : qty
        })

    save_inventory(inv)


def catat_masuk_toko(fitted_items, data_master_list):
    """
    Dipanggil saat gudang klik 'Konfirmasi Kirim'.
    Mencatat barang MASUK ke masing-masing toko.
    """
    inv = load_inventory()
    ts  = get_timestamp()

    rekap = {}
    for item in fitted_items:
        base_id     = item.item_id.split("_")[0]
        toko_tujuan = "Toko 1" if item.route_priority == 2 else "Toko 2"
        key = (base_id, toko_tujuan)
        rekap[key] = rekap.get(key, 0) + 1

    nama_map = {d["ID"]: d["Nama"] for d in data_master_list}

    for (base_id, toko_tujuan), qty in rekap.items():
        inv["riwayat_toko"][toko_tujuan].append({
            "timestamp"  : ts,
            "jenis"      : "Masuk",
            "id_barang"  : base_id,
            "nama_barang": nama_map.get(base_id, base_id),
            "qty"        : qty
        })

    save_inventory(inv)


def catat_keluar_toko(nama_toko, edited_df, data_master_list):
    inv = load_inventory()
    ts  = get_timestamp()
    nama_map = {d["ID"]: d["Nama"] for d in data_master_list}

    for _, row in edited_df.iterrows():
        qty_keluar = int(row["Kurangi Stok (Jual)"])
        if qty_keluar > 0:
            inv["riwayat_toko"][nama_toko].append({
                "timestamp"  : ts,
                "jenis"      : "Keluar",
                "id_barang"  : row["ID Barang"],
                "nama_barang": nama_map.get(row["ID Barang"], row["ID Barang"]),
                "qty"        : qty_keluar
            })

    save_inventory(inv)

def catat_koreksi_toko(nama_toko, id_barang, nama_barang, qty_tambah):
    """Mencatat koreksi penambahan stok akibat kesalahan input."""
    inv = load_inventory()
    ts  = get_timestamp()
    inv["riwayat_toko"][nama_toko].append({
        "timestamp"  : ts,
        "jenis"      : "Koreksi",
        "id_barang"  : id_barang,
        "nama_barang": nama_barang,
        "qty"        : qty_tambah
    })
    save_inventory(inv)


init_inventory()