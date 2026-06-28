from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io
from datetime import datetime


def generate_surat_jalan_pdf(df_manifest, images_3d=None, nama_pengirim="Gudang Pusat"):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )

    styles = getSampleStyleSheet()
    story  = []

    # ─── HEADER ───────────────────────────────────────────────
    story.append(Paragraph("<b>SURAT JALAN</b>", ParagraphStyle(
        "title", parent=styles["Title"], alignment=TA_CENTER, fontSize=18
    )))
    story.append(Spacer(1, 0.3*cm))

    tanggal_sekarang = datetime.now().strftime("%d %B %Y")
    no_surat         = datetime.now().strftime("SJ/%Y%m%d/%H%M")

    # ─── INFO PENGIRIMAN ──────────────────────────────────────
    tujuan_unik = df_manifest["Tujuan"].unique()
    tujuan_str  = ", ".join(tujuan_unik)

    info_data = [
        ["No. Surat", f": {no_surat}",      "Tanggal", f": {tanggal_sekarang}"],
        ["Pengirim",  f": {nama_pengirim}",  "Tujuan",  f": {tujuan_str}"],
    ]
    info_table = Table(info_data, colWidths=[3*cm, 6.5*cm, 2.5*cm, 6.5*cm])
    info_table.setStyle(TableStyle([
        ("FONTSIZE",      (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5*cm))

    # ─── TABEL MANIFEST ───────────────────────────────────────
    rekap = (
        df_manifest
        .groupby(["ID Barang", "Nama Barang", "Tujuan"], sort=False)
        .agg(Qty=("Kode Muat", "count"))
        .reset_index()
    )

    header = [["No.", "ID Barang", "Nama Barang", "Tujuan", "Qty (Bal)"]]
    rows   = [
        [str(i+1), row["ID Barang"], row["Nama Barang"], row["Tujuan"], str(row["Qty"])]
        for i, row in rekap.iterrows()
    ]
    total_qty = rekap["Qty"].sum()
    footer    = [["", "", "TOTAL", str(total_qty)]]
    table_data = header + rows + footer

    col_widths = [1.0*cm, 3*cm, 5*cm, 5*cm, 2.5*cm]
    manifest_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    manifest_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0),  (-1, 0),  colors.HexColor("#2c3e50")),
        ("TEXTCOLOR",     (0, 0),  (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0),  (-1, 0),  "Helvetica-Bold"),
        ("ALIGN",         (0, 0),  (-1, 0),  "CENTER"),
        ("FONTSIZE",      (0, 0),  (-1, 0),  10),
        ("FONTSIZE",      (0, 1),  (-1, -2), 9),
        ("ALIGN",         (0, 1),  (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS",(0, 1),  (-1, -2), [colors.white, colors.HexColor("#f2f2f2")]),
        ("TOPPADDING",    (0, 1),  (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1),  (-1, -1), 5),
        ("BACKGROUND",    (0, -1), (-1, -1), colors.HexColor("#ecf0f1")),
        ("FONTNAME",      (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, -1), (-1, -1), 10),
        ("GRID",          (0, 0),  (-1, -1), 0.5, colors.grey),
        ("BOX",           (0, 0),  (-1, -1), 1,   colors.black),
    ]))
    story.append(manifest_table)
    story.append(Spacer(1, 0.8*cm))

    # ─── VISUALISASI 3D (6 TAMPAK) ────────────────────────────
    if images_3d:
        story.append(Paragraph(
            "<b>Visualisasi 3D Susunan Muatan</b>",
            ParagraphStyle("sub", parent=styles["Normal"],
                           fontSize=11, spaceAfter=8)
        ))

        # Tampilkan 2 gambar per baris (3 baris = 6 gambar)
        img_width  = 8.5 * cm
        img_height = 6.5 * cm

        for i in range(0, len(images_3d), 2):
            row_cells = []
            for label, img_bytes in images_3d[i:i+2]:
                img_buf = io.BytesIO(img_bytes)
                rl_img  = RLImage(img_buf, width=img_width, height=img_height)
                cell    = [
                    Paragraph(f"<b>{label}</b>",
                              ParagraphStyle("cap", parent=styles["Normal"],
                                             fontSize=8, alignment=TA_CENTER)),
                    rl_img
                ]
                row_cells.append(cell)

            # Jika hanya 1 gambar di baris terakhir, tambah sel kosong
            if len(row_cells) == 1:
                row_cells.append([""])

            img_table = Table(
                [[row_cells[0], row_cells[1]]],
                colWidths=[9*cm, 9*cm]
            )
            img_table.setStyle(TableStyle([
                ("ALIGN",   (0, 0), (-1, -1), "CENTER"),
                ("VALIGN",  (0, 0), (-1, -1), "MIDDLE"),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(img_table)
            story.append(Spacer(1, 0.3*cm))

        story.append(Spacer(1, 0.5*cm))

    # ─── TANDA TANGAN ─────────────────────────────────────────
    ttd_data = [
        ["Disiapkan Oleh,", "", "Diterima Oleh,"],
        ["\n\n\n\n",        "", "\n\n\n\n"],
        ["( ________________ )", "", "( ________________ )"],
        ["Admin Gudang",    "", "Penerima"],
    ]
    ttd_table = Table(ttd_data, colWidths=[6*cm, 5.5*cm, 6*cm])
    ttd_table.setStyle(TableStyle([
        ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("TOPPADDING",  (0, 0), (-1, -1), 2),
    ]))
    story.append(ttd_table)

    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        "<i>* Dokumen ini digenerate secara otomatis oleh Sistem Logistik 3D-BPP.</i>",
        ParagraphStyle("note", parent=styles["Normal"],
                       fontSize=7, textColor=colors.grey)
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()