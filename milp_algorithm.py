import os
os.environ['GRB_LICENSE_FILE'] = r"D:\.kuliah\_SKRIPSI\gurobi.lic"

import gurobipy as gp
from gurobipy import GRB
from core_objects import Bin, Item
import copy
import itertools

# 6 kemungkinan rotasi ortogonal (permutasi indeks dimensi)
ORIENT_PERMS = list(itertools.permutations([0, 1, 2]))

def run_milp(bin_obj, items, time_limit=36000):
    m = gp.Model("3D-BPP_Full")
    m.setParam('TimeLimit',     time_limit)
    m.setParam('OutputFlag',    0)
    m.setParam('MIPGap',        0.05)
    m.setParam('Threads',       2)
    m.setParam('NodefileStart', 0.5)

    n = len(items)
    L, W, H = bin_obj.length, bin_obj.width, bin_obj.height
    M = max(L, W, H) * 2
    R = 6  # jumlah orientasi

    # Pre-hitung dimensi tiap item untuk setiap orientasi
    item_dims = []
    for i in range(n):
        base = [items[i].length, items[i].width, items[i].height]
        item_dims.append([
            tuple(base[k] for k in perm)
            for perm in ORIENT_PERMS
        ])

    # ── VARIABEL KEPUTUSAN ─────────────────────────────────────

    # s[i]     : 1 jika barang i dimuat
    s  = m.addVars(n,    vtype=GRB.BINARY,     name="s")
    # x,y,z    : koordinat posisi sudut kiri-bawah-depan
    x  = m.addVars(n,    vtype=GRB.CONTINUOUS, lb=0, name="x")
    y  = m.addVars(n,    vtype=GRB.CONTINUOUS, lb=0, name="y")
    z  = m.addVars(n,    vtype=GRB.CONTINUOUS, lb=0, name="z")
    # o[i,r]   : 1 jika barang i memakai orientasi r
    o  = m.addVars(n, R, vtype=GRB.BINARY,     name="o")
    # dx,dy,dz : dimensi aktual sesuai orientasi yang dipilih
    dx = m.addVars(n,    vtype=GRB.CONTINUOUS, lb=0, name="dx")
    dy = m.addVars(n,    vtype=GRB.CONTINUOUS, lb=0, name="dy")
    dz = m.addVars(n,    vtype=GRB.CONTINUOUS, lb=0, name="dz")

    # Variabel posisi relatif antar pasang barang (non-overlapping)
    lft = m.addVars(n, n, vtype=GRB.BINARY, name="lft")
    rgt = m.addVars(n, n, vtype=GRB.BINARY, name="rgt")
    frt = m.addVars(n, n, vtype=GRB.BINARY, name="frt")
    beh = m.addVars(n, n, vtype=GRB.BINARY, name="beh")
    blw = m.addVars(n, n, vtype=GRB.BINARY, name="blw")
    abv = m.addVars(n, n, vtype=GRB.BINARY, name="abv")

    # Variabel gravitasi
    # on_floor[i] : 1 jika barang i menapak langsung di lantai bak
    # sup[i,j]    : 1 jika barang j menopang barang i dari bawah
    on_floor = m.addVars(n,    vtype=GRB.BINARY, name="on_floor")
    sup      = m.addVars(n, n, vtype=GRB.BINARY, name="sup")

    # ── CONSTRAINT ORIENTASI ───────────────────────────────────
    for i in range(n):
        # Tepat 1 orientasi jika dimuat, 0 jika tidak
        m.addConstr(
            gp.quicksum(o[i,r] for r in range(R)) == s[i]
        )
        # Dimensi aktual = dimensi pada orientasi yang dipilih
        m.addConstr(dx[i] == gp.quicksum(
            o[i,r] * item_dims[i][r][0] for r in range(R)
        ))
        m.addConstr(dy[i] == gp.quicksum(
            o[i,r] * item_dims[i][r][1] for r in range(R)
        ))
        m.addConstr(dz[i] == gp.quicksum(
            o[i,r] * item_dims[i][r][2] for r in range(R)
        ))

    # ── CONSTRAINT BATAS BAK ───────────────────────────────────
    for i in range(n):
        m.addConstr(x[i] + dx[i] <= L + M * (1 - s[i]))
        m.addConstr(y[i] + dy[i] <= W + M * (1 - s[i]))
        m.addConstr(z[i] + dz[i] <= H + M * (1 - s[i]))
        m.addConstr(x[i] <= M * s[i])
        m.addConstr(y[i] <= M * s[i])
        m.addConstr(z[i] <= M * s[i])

    # ── CONSTRAINT NON-OVERLAPPING ─────────────────────────────
    for i in range(n):
        for j in range(i + 1, n):
            m.addConstr(
                lft[i,j] + rgt[i,j] + frt[i,j] +
                beh[i,j] + blw[i,j] + abv[i,j] >= s[i] + s[j] - 1
            )
            m.addConstr(x[i] + dx[i] <= x[j] + M * (1 - lft[i,j]))
            m.addConstr(x[j] + dx[j] <= x[i] + M * (1 - rgt[i,j]))
            m.addConstr(y[i] + dy[i] <= y[j] + M * (1 - frt[i,j]))
            m.addConstr(y[j] + dy[j] <= y[i] + M * (1 - beh[i,j]))
            m.addConstr(z[i] + dz[i] <= z[j] + M * (1 - blw[i,j]))
            m.addConstr(z[j] + dz[j] <= z[i] + M * (1 - abv[i,j]))

    # ── CONSTRAINT GRAVITASI ───────────────────────────────────
    # Tambahan variabel untuk cek overlap XY antara pasang barang
    # ax[i,j]=1 jika i melewati tepi kiri j di sumbu X
    # bx[i,j]=1 jika j melewati tepi kiri i di sumbu X
    # ay[i,j]=1 jika i melewati tepi depan j di sumbu Y
    # by[i,j]=1 jika j melewati tepi depan i di sumbu Y
    ax = m.addVars(n, n, vtype=GRB.BINARY, name="ax")
    bx = m.addVars(n, n, vtype=GRB.BINARY, name="bx")
    ay = m.addVars(n, n, vtype=GRB.BINARY, name="ay")
    by = m.addVars(n, n, vtype=GRB.BINARY, name="by")

    EPS = 0.01  # toleransi kecil untuk overlap

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            # Linearisasi: x[i] + dx[i] > x[j] ↔ ax[i,j]=1
            m.addConstr(x[i] + dx[i] - x[j] >= EPS - M * (1 - ax[i,j]))
            m.addConstr(x[i] + dx[i] - x[j] <= M * ax[i,j])
            # Linearisasi: x[j] + dx[j] > x[i] ↔ bx[i,j]=1
            m.addConstr(x[j] + dx[j] - x[i] >= EPS - M * (1 - bx[i,j]))
            m.addConstr(x[j] + dx[j] - x[i] <= M * bx[i,j])
            # Linearisasi: y[i] + dy[i] > y[j] ↔ ay[i,j]=1
            m.addConstr(y[i] + dy[i] - y[j] >= EPS - M * (1 - ay[i,j]))
            m.addConstr(y[i] + dy[i] - y[j] <= M * ay[i,j])
            # Linearisasi: y[j] + dy[j] > y[i] ↔ by[i,j]=1
            m.addConstr(y[j] + dy[j] - y[i] >= EPS - M * (1 - by[i,j]))
            m.addConstr(y[j] + dy[j] - y[i] <= M * by[i,j])

    for i in range(n):
        # Setiap barang yang dimuat WAJIB di lantai ATAU ditopang
        m.addConstr(
            on_floor[i] + gp.quicksum(
                sup[i,j] for j in range(n) if j != i
            ) >= s[i]
        )
        m.addConstr(on_floor[i] <= s[i])

        # Jika di lantai → z[i] = 0
        m.addConstr(z[i] <= M * (1 - on_floor[i]))

        for j in range(n):
            if j == i:
                continue
            m.addConstr(sup[i,j] <= s[i])
            m.addConstr(sup[i,j] <= s[j])

            # Jika j menopang i → z tepat di atas j
            m.addConstr(z[i] >= z[j] + dz[j] - M * (1 - sup[i,j]))
            m.addConstr(z[i] <= z[j] + dz[j] + M * (1 - sup[i,j]))

            # sup[i,j]=1 hanya boleh jika i dan j overlap di XY
            # (keempat kondisi overlap harus terpenuhi)
            m.addConstr(sup[i,j] <= ax[i,j])
            m.addConstr(sup[i,j] <= bx[i,j])
            m.addConstr(sup[i,j] <= ay[i,j])
            m.addConstr(sup[i,j] <= by[i,j])

    # ── FUNGSI OBJEKTIF ────────────────────────────────────────
    # Utama  : maksimalkan volume barang yang muat
    # Sekunder: minimasi posisi z → mendorong barang ke lantai
    vol_obj   = gp.quicksum(
        items[i].length * items[i].width * items[i].height * s[i]
        for i in range(n)
    )
    z_penalty = gp.quicksum(z[i] for i in range(n))
    m.setObjective(vol_obj * 10000 - z_penalty, GRB.MAXIMIZE)

    m.optimize()

    # ── AMBIL HASIL ────────────────────────────────────────────
    result_bin = Bin(L, W, H)
    if m.SolCount > 0:
        for i in range(n):
            if s[i].x > 0.5:
                packed_item   = copy.deepcopy(items[i])
                packed_item.x = round(x[i].x, 2)
                packed_item.y = round(y[i].x, 2)
                packed_item.z = round(z[i].x, 2)
                # Terapkan dimensi sesuai orientasi terpilih
                for r in range(R):
                    if o[i,r].x > 0.5:
                        packed_item.length = item_dims[i][r][0]
                        packed_item.width  = item_dims[i][r][1]
                        packed_item.height = item_dims[i][r][2]
                        break
                result_bin.fitted_items.append(packed_item)

    return result_bin