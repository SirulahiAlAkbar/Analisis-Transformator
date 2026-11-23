"""
Kalkulator Analisis Rugi-Rugi Daya dan Efisiensi Transformator Distribusi
=========================================================================
Tugas kelompok Pemrograman Dasar.

Cara menjalankan (di terminal VS Code):
    pip install -r requirements.txt
    streamlit run aplikasi_transformator.py

Susunan file ini (dari atas ke bawah):
    1. Konstanta dan data bawaan
    2. Fungsi perhitungan      -> murni Python, tidak bergantung pada Streamlit
    3. Fungsi validasi input
    4. Fungsi grafik (Matplotlib)
    5. Fungsi tampilan (Streamlit)
"""

import html
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # backend tanpa jendela, aman dipakai oleh Streamlit
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------------
# 1. KONSTANTA DAN DATA BAWAAN
# ----------------------------------------------------------------------------
FILE_DATA = Path(__file__).parent / "data_transformator.csv"

# Warna tema teknik elektro
NAVY = "#0B2A4A"
BIRU = "#1F5C99"
BIRU_MUDA = "#8FB3D9"
ABU_MUDA = "#EEF2F6"
ABU_TUA = "#5B6B7C"
AMBER = "#F5A524"

SUMBER_KATALOG = "https://www.sintra.co.id/assets/docs/sintra-distribution-transformers.pdf"
SUMBER_HALAMAN = "https://www.sintra.co.id/product-profiles/distribution-transformers"

# Nama kunci input -> dipakai di st.session_state dan di dictionary data
KUNCI_INPUT = [
    "kode", "jenis", "kva", "vp", "vs", "ip", "isek",
    "cosp", "coss", "rp", "rs", "pcore",
]

# Kolom CSV -> kunci input
PETA_KOLOM = {
    "kode": "kode",
    "jenis": "jenis",
    "kapasitas_kva": "kva",
    "tegangan_primer_v": "vp",
    "tegangan_sekunder_v": "vs",
    "arus_primer_a": "ip",
    "arus_sekunder_a": "isek",
    "cos_phi_primer": "cosp",
    "cos_phi_sekunder": "coss",
    "resistansi_primer_ohm": "rp",
    "resistansi_sekunder_ohm": "rs",
    "rugi_inti_w": "pcore",
}

KETERANGAN_STATUS = (
    "DATASHEET: kapasitas, tegangan, rugi tanpa beban (rugi inti), rugi beban @75 C, "
    "impedansi, efisiensi PF 1,0. "
    "TURUNAN: arus nominal = S/V; resistansi primer/sekunder dihitung dari rugi beban datasheet "
    "dengan asumsi rugi tembaga terbagi sama (50:50) antara primer dan sekunder. "
    "SIMULASI: beban 100% dengan cos phi sekunder 0,85 dan cos phi primer hasil skenario simulasi; "
    "BUKAN data pengukuran."
)

# Data bawaan. Nilai yang sama disimpan di data_transformator.csv.
# Program memakai CSV jika ada; jika CSV tidak ditemukan, program memakai data ini.
DATA_BAWAAN = [
    {
        "id": "SINTRA-1F-50KVA",
        "kode": "SINTRA 1 fasa 50 kVA (SPLN D3.002-2:2008)",
        "jenis": "1 fasa",
        "kapasitas_kva": 50.0,
        "tegangan_primer_v": 11547.0,
        "tegangan_sekunder_v": 231.0,
        "arus_primer_a": 4.3301,
        "arus_sekunder_a": 216.4502,
        "cos_phi_primer": 0.864,
        "cos_phi_sekunder": 0.85,
        "resistansi_primer_ohm": 15.6002,
        "resistansi_sekunder_ohm": 0.006243,
        "rugi_inti_w": 120.0,
        "rugi_beban_75c_w": 585.0,
        "impedansi_persen": 2.85,
        "efisiensi_datasheet_pf1_persen": 98.61,
        "status_data": KETERANGAN_STATUS,
        "sumber": SUMBER_KATALOG,
    },
    {
        "id": "SINTRA-1F-25KVA",
        "kode": "SINTRA 1 fasa 25 kVA (SPLN D3.002-2:2008)",
        "jenis": "1 fasa",
        "kapasitas_kva": 25.0,
        "tegangan_primer_v": 11547.0,
        "tegangan_sekunder_v": 231.0,
        "arus_primer_a": 2.1651,
        "arus_sekunder_a": 108.2251,
        "cos_phi_primer": 0.868,
        "cos_phi_sekunder": 0.85,
        "resistansi_primer_ohm": 39.4653,
        "resistansi_sekunder_ohm": 0.015795,
        "rugi_inti_w": 70.0,
        "rugi_beban_75c_w": 370.0,
        "impedansi_persen": 2.50,
        "efisiensi_datasheet_pf1_persen": 98.27,
        "status_data": KETERANGAN_STATUS,
        "sumber": SUMBER_KATALOG,
    },
]


def muat_dataframe():
    """Membaca data_transformator.csv. Jika file tidak ada, pakai DATA_BAWAAN."""
    if FILE_DATA.exists():
        try:
            return pd.read_csv(FILE_DATA, encoding="utf-8-sig")
        except Exception:
            pass
    return pd.DataFrame(DATA_BAWAAN)


# ----------------------------------------------------------------------------
# 2. FUNGSI PERHITUNGAN
# ----------------------------------------------------------------------------
def fmt(x, desimal=2):
    """Format angka gaya Indonesia: 1.234,56"""
    teks = f"{x:,.{desimal}f}"
    return teks.replace(",", "#").replace(".", ",").replace("#", ".")


def hitung_analisis(d):
    """
    Menghitung daya, rugi-rugi, dan efisiensi dari dictionary input `d`.

    Metode A (ESTIMASI, dipakai untuk efisiensi):
        P_loss_total = P_cu + P_core
        eta = P_out / (P_out + P_loss_total) x 100%
    Metode B (PEMERIKSAAN, dari selisih daya terukur):
        P_loss_measured = P_in - P_out
    Kedua metode TIDAK dicampur.
    """
    tiga_fasa = d["jenis"] == "3 fasa"
    k = math.sqrt(3) if tiga_fasa else 1.0   # faktor daya untuk 3 fasa
    n = 3 if tiga_fasa else 1                # jumlah fasa pada rugi tembaga

    p_in = k * d["vp"] * d["ip"] * d["cosp"]
    p_out = k * d["vs"] * d["isek"] * d["coss"]
    p_cu = n * (d["ip"] ** 2 * d["rp"] + d["isek"] ** 2 * d["rs"])
    p_core = d["pcore"]
    p_loss = p_cu + p_core
    eta = p_out / (p_out + p_loss) * 100.0

    p_loss_terukur = p_in - p_out
    s_out = k * d["vs"] * d["isek"]          # daya semu keluaran (VA)
    beban_persen = s_out / (d["kva"] * 1000.0) * 100.0

    return {
        "p_in": p_in,
        "p_out": p_out,
        "p_cu": p_cu,
        "p_core": p_core,
        "p_loss": p_loss,
        "eta": eta,
        "p_loss_terukur": p_loss_terukur,
        "selisih_metode": p_loss_terukur - p_loss,
        "s_out": s_out,
        "beban_persen": beban_persen,
    }


def buat_interpretasi(d, h):
    """Kalimat penjelasan otomatis (tanpa menilai baik/buruk)."""
    porsi_cu = h["p_cu"] / h["p_loss"] * 100 if h["p_loss"] > 0 else 0.0
    porsi_core = 100 - porsi_cu if h["p_loss"] > 0 else 0.0
    return (
        f"Transformator {d['kode']} memiliki efisiensi sebesar {fmt(h['eta'], 2)}%. "
        f"Rugi-rugi daya total berdasarkan estimasi adalah {fmt(h['p_loss'], 2)} Watt, "
        f"terdiri dari rugi tembaga {fmt(h['p_cu'], 2)} Watt ({fmt(porsi_cu, 1)}%) dan "
        f"rugi inti {fmt(h['p_core'], 2)} Watt ({fmt(porsi_core, 1)}%). "
        f"Pada data ini, daya semu keluaran setara {fmt(h['beban_persen'], 1)}% dari kapasitas nominal. "
        "Nilai efisiensi hanya berlaku untuk beban dan faktor daya yang diinput; "
        "program tidak memberi label baik/buruk karena tidak ada kriteria pembanding yang ditetapkan."
    )


# ----------------------------------------------------------------------------
# 3. VALIDASI INPUT
# ----------------------------------------------------------------------------
def validasi_input(d):
    """Mengembalikan (daftar_galat, daftar_peringatan). Perhitungan hanya jika galat kosong."""
    galat, peringatan = [], []

    if not str(d.get("kode", "")).strip():
        galat.append("Nama/kode transformator tidak boleh kosong.")
    if d.get("jenis") not in ("1 fasa", "3 fasa"):
        galat.append("Jenis transformator harus 1 fasa atau 3 fasa.")

    harus_positif = [
        ("kva", "Kapasitas (kVA)"),
        ("vp", "Tegangan primer (V)"),
        ("vs", "Tegangan sekunder (V)"),
        ("ip", "Arus primer (A)"),
        ("isek", "Arus sekunder (A)"),
    ]
    for kunci, label in harus_positif:
        nilai = d.get(kunci)
        if nilai is None or not nilai > 0:
            galat.append(f"{label} harus lebih besar dari 0.")

    for kunci, label in [("cosp", "Faktor daya primer"), ("coss", "Faktor daya sekunder")]:
        nilai = d.get(kunci)
        if nilai is None or not (0 < nilai <= 1):
            galat.append(f"{label} harus di antara 0 dan 1 (lebih besar dari 0, maksimum 1).")

    for kunci, label in [
        ("rp", "Resistansi primer (Ohm)"),
        ("rs", "Resistansi sekunder (Ohm)"),
        ("pcore", "Rugi inti (Watt)"),
    ]:
        nilai = d.get(kunci)
        if nilai is None or nilai < 0:
            galat.append(f"{label} tidak boleh negatif.")

    if galat:
        return galat, peringatan

    # Pemeriksaan konsistensi (hanya jika semua input dasar valid)
    h = hitung_analisis(d)
    if h["p_out"] > h["p_in"]:
        galat.append(
            "Daya keluaran lebih besar dari daya masukan. Hal ini tidak mungkin secara fisik; "
            "periksa kembali tegangan, arus, dan faktor daya."
        )
        return galat, peringatan

    if h["beban_persen"] > 100:
        peringatan.append(
            f"Daya semu keluaran ({fmt(h['beban_persen'], 1)}% dari kapasitas) melebihi kapasitas nominal."
        )
    rasio_v = d["vp"] / d["vs"]
    rasio_i = d["isek"] / d["ip"]
    if abs(rasio_v - rasio_i) / rasio_v > 0.10:
        peringatan.append(
            f"Rasio tegangan Vp/Vs = {fmt(rasio_v, 2)} berbeda lebih dari 10% dari rasio arus Is/Ip = "
            f"{fmt(rasio_i, 2)}. Periksa apakah data arus dan tegangan sudah konsisten."
        )
    if h["p_loss"] > 0 and abs(h["selisih_metode"]) > 0.5 * h["p_loss"]:
        peringatan.append(
            "Rugi-rugi estimasi dan selisih daya masukan-keluaran berbeda cukup jauh (>50%). "
            "Periksa kembali data resistansi, rugi inti, dan faktor daya."
        )
    return galat, peringatan


# ----------------------------------------------------------------------------
# 4. GRAFIK (MATPLOTLIB)
# ----------------------------------------------------------------------------
GRAFIK_GELAP = False   # diatur oleh main() sesuai pilihan tema


def _utama():
    """Warna batang utama: navy di tema terang, biru cerah di tema gelap."""
    return "#3D8FD6" if GRAFIK_GELAP else NAVY


def _teks():
    return "#E8F0FA" if GRAFIK_GELAP else NAVY


def _selaraskan(fig):
    """Mewarnai latar, sumbu, dan teks grafik untuk tema gelap. Di tema terang tidak mengubah apa pun."""
    if not GRAFIK_GELAP:
        return fig
    fig.patch.set_facecolor("#122339")
    for ax in fig.axes:
        ax.set_facecolor("#122339")
        ax.tick_params(colors="#C5D3E3")
        ax.xaxis.label.set_color("#C5D3E3")
        ax.yaxis.label.set_color("#C5D3E3")
        ax.title.set_color("#E8F0FA")
        for sisi in ax.spines.values():
            sisi.set_color("#3A5578")
        leg = ax.get_legend()
        if leg:
            for t in leg.get_texts():
                t.set_color("#E8F0FA")
    return fig


def _beri_nilai(ax, batang, satuan=""):
    for b in batang:
        ax.annotate(
            f"{fmt(b.get_height(), 2)}{satuan}",
            (b.get_x() + b.get_width() / 2, b.get_height()),
            ha="center", va="bottom", fontsize=9, color=_teks(),
            xytext=(0, 3), textcoords="offset points",
        )


def grafik_daya(h):
    """Grafik 1: daya masukan vs daya keluaran."""
    fig, ax = plt.subplots(figsize=(5.6, 4.0))
    batang = [
        ax.bar("Daya masukan", h["p_in"], color=_utama(), label="Daya masukan (P_in)")[0],
        ax.bar("Daya keluaran", h["p_out"], color=BIRU_MUDA, label="Daya keluaran (P_out)")[0],
    ]
    _beri_nilai(ax, batang, " W")
    ax.set_title("Perbandingan Daya Masukan dan Daya Keluaran", fontsize=11, color=_teks())
    ax.set_ylabel("Daya (Watt)")
    ax.set_ylim(0, max(h["p_in"], h["p_out"]) * 1.3)
    ax.legend(loc="upper center", ncol=2, fontsize=8, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return _selaraskan(fig)


def grafik_rugi(h):
    """Grafik 2: rugi tembaga vs rugi inti."""
    fig, ax = plt.subplots(figsize=(5.6, 4.0))
    batang = [
        ax.bar("Rugi tembaga", h["p_cu"], color=AMBER, label="Rugi tembaga (P_cu)")[0],
        ax.bar("Rugi inti", h["p_core"], color=BIRU, label="Rugi inti (P_core)")[0],
    ]
    _beri_nilai(ax, batang, " W")
    ax.set_title("Perbandingan Rugi Tembaga dan Rugi Inti", fontsize=11, color=_teks())
    ax.set_ylabel("Rugi-rugi daya (Watt)")
    ax.set_ylim(0, max(h["p_cu"], h["p_core"], 1) * 1.2)
    ax.legend(loc="upper right", fontsize=8, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return _selaraskan(fig)


def grafik_efisiensi(h):
    """Grafik 3: persentase efisiensi terhadap rugi-rugi (estimasi)."""
    eta = h["eta"]
    rugi = 100 - eta
    fig, ax = plt.subplots(figsize=(5.6, 4.0))
    ax.barh(["Transformator"], [eta], color=_utama(), label=f"Efisiensi ({fmt(eta, 2)}%)")
    ax.barh(["Transformator"], [rugi], left=[eta], color=AMBER,
            label=f"Rugi-rugi ({fmt(rugi, 2)}%)")
    ax.set_xlim(0, 100)
    ax.set_xlabel("Persentase dari P_out + P_loss (%)")
    ax.set_title("Persentase Efisiensi Transformator", fontsize=11, color=_teks())
    ax.text(eta / 2, 0, f"{fmt(eta, 2)}%", ha="center", va="center", color="white",
            fontsize=13, fontweight="bold")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.25), ncol=2, fontsize=8, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return _selaraskan(fig)


def tabel_ringkasan(d, h):
    """Tabel ringkasan data input dan hasil (dipakai di layar dan untuk CSV)."""
    baris = [
        ("Kode transformator", d["kode"], "-", "Input"),
        ("Jenis", d["jenis"], "-", "Input"),
        ("Kapasitas", d["kva"], "kVA", "Input"),
        ("Tegangan primer", d["vp"], "V", "Input"),
        ("Tegangan sekunder", d["vs"], "V", "Input"),
        ("Arus primer", d["ip"], "A", "Input"),
        ("Arus sekunder", d["isek"], "A", "Input"),
        ("Faktor daya primer", d["cosp"], "-", "Input"),
        ("Faktor daya sekunder", d["coss"], "-", "Input"),
        ("Resistansi primer per fasa", d["rp"], "Ohm", "Input"),
        ("Resistansi sekunder per fasa", d["rs"], "Ohm", "Input"),
        ("Rugi inti (core loss)", d["pcore"], "W", "Input"),
        ("Daya masukan (P_in)", round(h["p_in"], 4), "W", "Hasil"),
        ("Daya keluaran (P_out)", round(h["p_out"], 4), "W", "Hasil"),
        ("Rugi tembaga (P_cu)", round(h["p_cu"], 4), "W", "Hasil (estimasi)"),
        ("Rugi inti (P_core)", round(h["p_core"], 4), "W", "Hasil (estimasi)"),
        ("Total rugi-rugi estimasi (P_loss)", round(h["p_loss"], 4), "W", "Hasil (estimasi)"),
        ("Efisiensi (estimasi)", round(h["eta"], 4), "%", "Hasil (estimasi)"),
        ("Selisih daya P_in - P_out", round(h["p_loss_terukur"], 4), "W", "Pemeriksaan"),
        ("Beda metode (selisih - estimasi)", round(h["selisih_metode"], 4), "W", "Pemeriksaan"),
    ]
    df = pd.DataFrame(baris, columns=["Parameter", "Nilai", "Satuan", "Kategori"])
    df["Nilai"] = df["Nilai"].astype(str)
    return df


# ----------------------------------------------------------------------------
# 5. TAMPILAN STREAMLIT
# ----------------------------------------------------------------------------
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root {
    --navy: #0B2A4A; --navy2: #14477A; --biru: #1F6FB2; --langit: #5FB0F0; --amber: #F5A524;
    /* variabel tema (nilai tema TERANG; tema gelap menimpanya lewat CSS_GELAP) */
    --teks: #0B2A4A; --teks-redup: #5B6B7C; --garis: #DCE5F0; --kartu-bg: rgba(255,255,255,.92);
    --ring-bg: #E3ECF6; --batang-bg: #FBE3BE; --chip-bg: #E6F0FA; --chip-garis: #C9DDF2;
    --tab-hover: #EAF2FB; --btn-bg: #FFFFFF; --input-bg: #FFFFFF;
    --bg1: #D6E8FA; --bg2: #E4EDF8; --bg3: #F4F7FB;
    --info-bg: #E3F0FD; --info-bd: #A9CDF2; --ok-bg: #E1F5E9; --ok-bd: #9ED5B3;
    --warn-bg: #FFF3D4; --warn-bd: #F0CF83; --err-bg: #FDE3E3; --err-bd: #F0A9A9;
}

/* ---------- Animasi dasar ---------- */
@keyframes naikPelan   { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: none; } }
@keyframes gradGerak   { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
@keyframes melayang    { 0%, 100% { transform: translate(0, 0) scale(1); } 50% { transform: translate(18px, -14px) scale(1.08); } }
@keyframes kilat       { 0%, 100% { transform: scale(1) rotate(0); filter: drop-shadow(0 0 0 rgba(245,165,36,0)); }
                         50% { transform: scale(1.12) rotate(-6deg); filter: drop-shadow(0 0 14px rgba(245,165,36,.85)); } }
@keyframes kilauan     { from { transform: translateX(-120%); } to { transform: translateX(220%); } }
@keyframes denyut      { 0% { box-shadow: 0 0 0 0 rgba(31,111,178,.45); } 70% { box-shadow: 0 0 0 12px rgba(31,111,178,0); } 100% { box-shadow: 0 0 0 0 rgba(31,111,178,0); } }
@keyframes isiCincin   { from { stroke-dashoffset: var(--keliling); } to { stroke-dashoffset: var(--sisa); } }
@keyframes isiBatang   { from { width: 0; } to { width: var(--lebar); } }

html, body, [class*="css"], .stApp, button, input, textarea {
    font-family: 'Plus Jakarta Sans', system-ui, -apple-system, 'Segoe UI', sans-serif;
}
.stApp {
    background:
        radial-gradient(900px 420px at 92% -8%, var(--bg1) 0%, transparent 62%),
        radial-gradient(800px 480px at -8% 12%, var(--bg2) 0%, transparent 58%),
        var(--bg3);
}
.block-container { padding-top: 4.5rem; max-width: 1200px; }  /* beri ruang di bawah bilah header Streamlit */
[data-testid="stToggle"], [data-testid="stCheckbox"] { position: relative; z-index: 1000001; }  /* pastikan tombol tema selalu bisa diklik */

/* ---------- Hero ---------- */
.hero {
    position: relative; overflow: hidden; margin-bottom: 22px; padding: 30px 36px; border-radius: 22px;
    background: linear-gradient(120deg, #0B2A4A, #14477A, #1F6FB2, #14477A, #0B2A4A);
    background-size: 300% 300%; animation: gradGerak 14s ease infinite, naikPelan .7s ease both;
    box-shadow: 0 18px 40px -18px rgba(11,42,74,.65);
}
.hero::before, .hero::after { content: ""; position: absolute; border-radius: 50%; pointer-events: none; }
.hero::before { width: 260px; height: 260px; right: -60px; top: -90px; background: rgba(95,176,240,.28); filter: blur(8px); animation: melayang 9s ease-in-out infinite; }
.hero::after  { width: 180px; height: 180px; right: 160px; bottom: -100px; background: rgba(245,165,36,.25); filter: blur(10px); animation: melayang 11s ease-in-out infinite reverse; }
.hero .judul { position: relative; z-index: 1; color: #FFFFFF; font-size: 1.9rem; font-weight: 800; letter-spacing: -.02em; margin: 0; line-height: 1.25; }
.hero .kilat { display: inline-block; animation: kilat 2.6s ease-in-out infinite; margin-right: 6px; }
.hero .sub { position: relative; z-index: 1; color: #D6E6F7; margin: 10px 0 14px 0; font-size: 1rem; max-width: 760px; animation: naikPelan .8s .15s ease both; }
.hero .chip { position: relative; z-index: 1; display: inline-block; margin: 0 8px 4px 0; padding: 4px 14px; border-radius: 999px; font-size: .78rem; font-weight: 600;
              color: #fff; background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.25); backdrop-filter: blur(6px); animation: naikPelan .8s .3s ease both; }

/* ---------- Kartu ---------- */
.kartu {
    position: relative; overflow: hidden; background: var(--kartu-bg); border: 1px solid var(--garis); border-radius: 18px;
    padding: 16px 20px; margin-bottom: 14px; box-shadow: 0 6px 18px -10px rgba(11,42,74,.25);
    animation: naikPelan .6s ease both; transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease;
}
.kartu:hover { transform: translateY(-5px); border-color: #9CC4EA; box-shadow: 0 18px 30px -14px rgba(31,111,178,.45); }
.k-judul { color: var(--teks-redup); font-size: .82rem; font-weight: 600; letter-spacing: .02em; }
.k-nilai { color: var(--teks); font-size: 1.65rem; font-weight: 800; line-height: 1.35; letter-spacing: -.01em; }
.k-satuan { color: var(--teks-redup); font-size: .9rem; font-weight: 600; margin-left: 5px; }
.kartu.utama { background: linear-gradient(135deg, #0B2A4A, #1F6FB2); border-color: transparent; }
.kartu.utama::after { content: ""; position: absolute; top: 0; bottom: 0; width: 38%; left: 0;
                      background: linear-gradient(100deg, transparent, rgba(255,255,255,.22), transparent); animation: kilauan 3.6s ease-in-out infinite; }
.kartu.utama .k-judul { color: #BBD6F0; }
.kartu.utama .k-nilai, .kartu.utama .k-satuan { color: #FFFFFF; }

/* urutan muncul kartu per kolom (bertahap) */
div[data-testid="column"]:nth-child(2) .kartu, div[data-testid="stColumn"]:nth-child(2) .kartu { animation-delay: .08s; }
div[data-testid="column"]:nth-child(3) .kartu, div[data-testid="stColumn"]:nth-child(3) .kartu { animation-delay: .16s; }
div[data-testid="column"]:nth-child(4) .kartu, div[data-testid="stColumn"]:nth-child(4) .kartu { animation-delay: .24s; }

.label-status { display: inline-block; background: var(--chip-bg); color: var(--teks); border: 1px solid var(--chip-garis); border-radius: 999px;
                padding: 3px 14px; font-size: .78rem; font-weight: 600; margin: 0 6px 4px 0; transition: transform .2s, background .2s; }
.label-status:hover { transform: translateY(-2px); filter: brightness(1.12); }

/* ---------- Cincin efisiensi ---------- */
.ring-box { display: flex; align-items: center; gap: 22px; background: var(--kartu-bg); border: 1px solid var(--garis);
            border-radius: 22px; padding: 18px 24px; margin-bottom: 16px; box-shadow: 0 6px 18px -10px rgba(11,42,74,.25); animation: naikPelan .6s ease both; }
.ring-wrap { position: relative; width: 150px; height: 150px; flex: none; }
.ring { width: 150px; height: 150px; transform: rotate(-90deg); }
.ring-bg { fill: none; stroke: var(--ring-bg); stroke-width: 12; }
.ring-fg { fill: none; stroke: url(#gradCincin); stroke-width: 12; stroke-linecap: round;
           stroke-dasharray: var(--keliling); stroke-dashoffset: var(--sisa); animation: isiCincin 1.6s cubic-bezier(.22,.9,.3,1) both; }
.ring-teks { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.ring-nilai { font-size: 1.55rem; font-weight: 800; color: var(--teks); line-height: 1.1; }
.ring-label { font-size: .75rem; color: var(--teks-redup); font-weight: 600; }
.ring-info { flex: 1; min-width: 0; }
.ring-info .judul-kecil { color: var(--teks-redup); font-size: .82rem; font-weight: 600; }
.ring-info .kalimat { color: var(--teks); font-size: 1.02rem; font-weight: 600; margin: 4px 0 12px 0; line-height: 1.5; }
.batang { height: 12px; border-radius: 999px; background: var(--batang-bg); overflow: hidden; }
.batang > span { display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg, #14477A, #5FB0F0);
                 width: var(--lebar); animation: isiBatang 1.6s cubic-bezier(.22,.9,.3,1) both; }
.legenda { display: flex; justify-content: space-between; font-size: .76rem; color: var(--teks-redup); margin-top: 6px; font-weight: 600; }

/* ---------- Tab ---------- */
.stTabs [data-baseweb="tab-list"] { gap: 6px; padding: 6px; background: var(--kartu-bg); border: 1px solid var(--garis); border-radius: 16px; box-shadow: 0 6px 18px -12px rgba(11,42,74,.3); }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }
.stTabs [data-baseweb="tab"] { height: 42px; padding: 0 20px; border-radius: 11px; transition: background .25s, transform .2s; }
.stTabs [data-baseweb="tab"]:hover { background: var(--tab-hover); transform: translateY(-1px); }
.stTabs [data-baseweb="tab"] p { font-weight: 700; font-size: .93rem; }
.stTabs [aria-selected="true"] { background: linear-gradient(135deg, #0B2A4A, #1F6FB2) !important; box-shadow: 0 8px 16px -8px rgba(11,42,74,.7); }
.stTabs [aria-selected="true"] p { color: #FFFFFF !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.2rem; animation: naikPelan .5s ease both; }

/* ---------- Tombol ---------- */
.stButton > button, .stDownloadButton > button {
    border-radius: 12px; font-weight: 700; padding: .55rem 1.3rem; border: 1px solid var(--garis);
    transition: transform .2s ease, box-shadow .2s ease, background .2s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover { transform: translateY(-3px); box-shadow: 0 12px 20px -10px rgba(11,42,74,.45); border-color: #9CC4EA; }
.stButton > button:active, .stDownloadButton > button:active { transform: translateY(0) scale(.97); }
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"] {
    color: #fff; border: none; background: linear-gradient(135deg, #14477A, #1F6FB2, #3B93DA); background-size: 200% 200%;
    animation: gradGerak 6s ease infinite, denyut 2.4s ease-out infinite;
}
.stButton > button[kind="primary"]:hover { box-shadow: 0 14px 24px -10px rgba(31,111,178,.8); }

/* ---------- Input & komponen ---------- */
.stTextInput input, .stNumberInput input { border-radius: 11px; transition: box-shadow .2s ease, border-color .2s ease; }
.stTextInput > div > div:focus-within, .stNumberInput > div > div:focus-within, [data-baseweb="select"] > div:focus-within {
    box-shadow: 0 0 0 3px rgba(31,111,178,.25); border-radius: 11px;
}
[data-baseweb="select"] > div { border-radius: 11px; }
[data-testid="stAlert"] { border-radius: 14px; animation: naikPelan .45s ease both; }
[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; border: 1px solid var(--garis); animation: naikPelan .6s ease both; }
[data-testid="stImage"] img, .stPyplot img, [data-testid="stImage"] { border-radius: 14px; }
h2, h3 { color: var(--teks) !important; font-weight: 800 !important; letter-spacing: -.01em; }


/* ---------- Teks & komponen bawaan Streamlit mengikuti variabel tema ---------- */
.stApp { color: var(--teks) !important; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label { color: var(--teks); }
[data-testid="stCaptionContainer"] { color: var(--teks-redup) !important; }
.stButton > button:not([kind="primary"]):not([data-testid="stBaseButton-primary"]), .stDownloadButton > button { background: var(--btn-bg); color: var(--teks); }
.stTextInput input, .stNumberInput input { background: var(--input-bg); color: var(--teks); }
.toggle-tema { text-align: right; }

/* ---------- Kotak peringatan (info/sukses/peringatan/galat): warna diatur penuh oleh tema aplikasi ---------- */
[data-testid="stAlert"], [data-testid="stAlert"] > div { background: var(--info-bg) !important; }
[data-testid="stAlert"] { border: 1px solid var(--info-bd); border-radius: 14px; }
[data-testid="stAlert"] * { color: var(--teks) !important; }
[data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]), [data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]) > div { background: var(--ok-bg) !important; border-color: var(--ok-bd); }
[data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]), [data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]) > div { background: var(--warn-bg) !important; border-color: var(--warn-bd); }
[data-testid="stAlert"]:has([data-testid="stAlertContentError"]), [data-testid="stAlert"]:has([data-testid="stAlertContentError"]) > div { background: var(--err-bg) !important; border-color: var(--err-bd); }

/* hormati pengguna yang mematikan animasi di sistem */
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
</style>
"""


# CSS tambahan yang hanya dipakai saat "Mode gelap" aktif: menimpa variabel warna dan merapikan widget bawaan Streamlit.
CSS_GELAP = """
<style>
:root {
    --teks: #E8F0FA; --teks-redup: #9FB3C8; --garis: #27425F; --kartu-bg: rgba(18,35,57,.92);
    --ring-bg: #243C5A; --batang-bg: #5A3E12; --chip-bg: #1B3556; --chip-garis: #2F5583;
    --tab-hover: #1B3556; --btn-bg: #14283F; --input-bg: #0F2038;
    --bg1: #123456; --bg2: #0F2B49; --bg3: #08121F;
    --info-bg: #12304F; --info-bd: #2F5583; --ok-bg: #0F3A2A; --ok-bd: #27704F;
    --warn-bg: #45370F; --warn-bd: #8A6D1C; --err-bg: #4A1B1F; --err-bd: #8F3A42;
}
.stApp { color-scheme: dark; }
.kartu:hover { border-color: #3F7FBD; box-shadow: 0 18px 30px -14px rgba(0,0,0,.7); }
.hero { box-shadow: 0 18px 40px -18px rgba(0,0,0,.8); }
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="select"] > div {
    background-color: var(--input-bg) !important; color: var(--teks) !important; border-color: var(--garis) !important;
}
[data-baseweb="input"] input, [data-baseweb="select"] div, [data-baseweb="select"] span { color: var(--teks) !important; }
[data-testid="stNumberInput"] button { background: var(--input-bg) !important; color: var(--teks) !important; }
[data-baseweb="popover"] [data-baseweb="menu"], [data-baseweb="popover"] ul { background: #0F2038 !important; }
[data-baseweb="popover"] li { color: var(--teks) !important; }
[data-baseweb="popover"] li:hover { background: #1B3556 !important; }
/* kotak yang warnanya diatur Streamlit sendiri (peringatan, tabel, kode) dibalik agar gelap tetapi tetap berwarna */
[data-testid="stDataFrame"], [data-testid="stCode"], [data-testid="stTable"] { filter: invert(.9) hue-rotate(180deg); }
</style>
"""


def kartu(judul, nilai, satuan="", utama=False):
    kelas = "kartu utama" if utama else "kartu"
    return (
        f'<div class="{kelas}"><div class="k-judul">{judul}</div>'
        f'<div class="k-nilai">{nilai}<span class="k-satuan">{satuan}</span></div></div>'
    )


def cincin_efisiensi(eta):
    """Cincin animasi efisiensi + batang proporsi daya berguna vs rugi (hanya tampilan, tidak mengubah hitungan)."""
    keliling = 2 * math.pi * 54
    sisa = keliling * (1 - max(0.0, min(eta, 100.0)) / 100)
    rugi = 100 - eta
    return (
        '<div class="ring-box"><div class="ring-wrap">'
        '<svg class="ring" viewBox="0 0 140 140"><defs><linearGradient id="gradCincin" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#5FB0F0"/><stop offset="1" stop-color="#14477A"/></linearGradient></defs>'
        '<circle class="ring-bg" cx="70" cy="70" r="54"/>'
        f'<circle class="ring-fg" cx="70" cy="70" r="54" style="--keliling:{keliling:.2f};--sisa:{sisa:.2f}"/></svg>'
        f'<div class="ring-teks"><div class="ring-nilai">{fmt(eta, 2)}%</div><div class="ring-label">Efisiensi</div></div></div>'
        '<div class="ring-info"><div class="judul-kecil">Proporsi daya (P_out + P_loss)</div>'
        f'<div class="kalimat">Dari setiap 100 W, sekitar {fmt(eta, 2)} W menjadi daya keluaran dan '
        f'{fmt(rugi, 2)} W hilang sebagai rugi-rugi (estimasi).</div>'
        f'<div class="batang" style="--lebar:{eta:.2f}%"><span></span></div>'
        '<div class="legenda"><span>Daya keluaran</span><span>Rugi-rugi</span></div></div></div>'
    )


def ambil_input():
    return {k: st.session_state[k] for k in KUNCI_INPUT}


def isi_dari_baris(baris):
    for kolom, kunci in PETA_KOLOM.items():
        nilai = baris[kolom]
        st.session_state[kunci] = nilai if kunci in ("kode", "jenis") else float(nilai)


def bersihkan_hasil():
    st.session_state["hasil"] = None
    st.session_state["hasil_input"] = None
    st.session_state["galat"] = []
    st.session_state["peringatan"] = []


def inisialisasi_state():
    df = muat_dataframe()
    if "hasil" not in st.session_state:
        bersihkan_hasil()
    if "preset" not in st.session_state:
        st.session_state["preset"] = df.iloc[0]["id"]
    if "kode" not in st.session_state:
        isi_dari_baris(df.iloc[0])


def callback_preset():
    df = muat_dataframe()
    baris = df[df["id"] == st.session_state["preset"]].iloc[0]
    isi_dari_baris(baris)
    bersihkan_hasil()


def callback_reset():
    df = muat_dataframe()
    st.session_state["preset"] = df.iloc[0]["id"]
    isi_dari_baris(df.iloc[0])
    bersihkan_hasil()


def callback_hitung():
    d = ambil_input()
    galat, peringatan = validasi_input(d)
    st.session_state["galat"] = galat
    st.session_state["peringatan"] = peringatan
    if galat:
        st.session_state["hasil"] = None
        st.session_state["hasil_input"] = None
    else:
        st.session_state["hasil"] = hitung_analisis(d)
        st.session_state["hasil_input"] = d


def tab_dashboard():
    d = ambil_input()
    st.subheader("Identitas Transformator")
    c1, c2, c3 = st.columns(3)
    c1.markdown(kartu("Kode / nama", html.escape(str(d["kode"]))), unsafe_allow_html=True)
    c2.markdown(kartu("Jenis", d["jenis"]), unsafe_allow_html=True)
    c3.markdown(kartu("Kapasitas", fmt(d["kva"], 1), "kVA"), unsafe_allow_html=True)
    c4, c5, c6 = st.columns(3)
    c4.markdown(kartu("Tegangan primer", fmt(d["vp"], 0), "V"), unsafe_allow_html=True)
    c5.markdown(kartu("Tegangan sekunder", fmt(d["vs"], 0), "V"), unsafe_allow_html=True)
    c6.markdown(kartu("Rugi inti (input)", fmt(d["pcore"], 1), "W"), unsafe_allow_html=True)

    st.subheader("Ringkasan Hasil Analisis")
    h = st.session_state["hasil"]
    if h is None:
        st.info("Belum ada hasil. Buka tab **Input Data**, lalu klik **Hitung Analisis**.")
    else:
        a, b, c = st.columns(3)
        a.markdown(kartu("Efisiensi", fmt(h["eta"], 2), "%", utama=True), unsafe_allow_html=True)
        b.markdown(kartu("Total rugi-rugi (estimasi)", fmt(h["p_loss"], 2), "W"), unsafe_allow_html=True)
        c.markdown(kartu("Daya keluaran", fmt(h["p_out"], 2), "W"), unsafe_allow_html=True)

    st.markdown(
        '<span class="label-status">Data datasheet SINTRA</span>'
        '<span class="label-status">Turunan</span><span class="label-status">Simulasi</span>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Nilai awal berasal dari katalog SINTRA (lihat tab Rumus & Sumber). "
        "Beban dan faktor daya adalah skenario simulasi, bukan hasil pengukuran."
    )


def tab_input():
    df = muat_dataframe()
    st.subheader("Input Data Transformator")
    st.selectbox(
        "Pilih data awal (opsional, nilainya tetap bisa diubah)",
        options=list(df["id"]),
        format_func=lambda i: df[df["id"] == i].iloc[0]["kode"],
        key="preset",
        on_change=callback_preset,
    )
    st.caption("Semua kolom di bawah bisa diisi sendiri dengan data transformator lain.")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Identitas**")
        st.text_input("Nama / kode transformator", key="kode")
        st.selectbox("Jenis transformator", ["1 fasa", "3 fasa"], key="jenis")
        st.number_input("Kapasitas (kVA)", step=1.0, format="%.2f", key="kva")
        st.number_input("Rugi inti / core loss (Watt)", step=1.0, format="%.2f", key="pcore")
    with c2:
        st.markdown("**Sisi primer**")
        st.number_input("Tegangan primer (Volt)", step=1.0, format="%.2f", key="vp")
        st.number_input("Arus primer (Ampere)", step=0.01, format="%.4f", key="ip")
        st.number_input("Faktor daya primer (cos φ)", step=0.01, format="%.4f", key="cosp")
        st.number_input("Resistansi kumparan primer per fasa (Ohm)", step=0.01, format="%.4f", key="rp")
    with c3:
        st.markdown("**Sisi sekunder**")
        st.number_input("Tegangan sekunder (Volt)", step=1.0, format="%.2f", key="vs")
        st.number_input("Arus sekunder (Ampere)", step=0.01, format="%.4f", key="isek")
        st.number_input("Faktor daya sekunder (cos φ)", step=0.01, format="%.4f", key="coss")
        st.number_input("Resistansi kumparan sekunder per fasa (Ohm)", step=0.0001, format="%.6f", key="rs")

    b1, b2, _ = st.columns([1, 1, 3])
    b1.button("Hitung Analisis", type="primary", on_click=callback_hitung)
    b2.button("Reset input", on_click=callback_reset)

    for pesan in st.session_state["galat"]:
        st.error(pesan)
    for pesan in st.session_state["peringatan"]:
        st.warning(pesan)
    if st.session_state["hasil"] is not None and not st.session_state["galat"]:
        st.success("Perhitungan berhasil. Lihat tab **Hasil & Grafik**.")


def tab_hasil():
    h = st.session_state["hasil"]
    d = st.session_state["hasil_input"]
    st.subheader("Hasil Analisis")
    if h is None:
        st.info("Belum ada hasil perhitungan. Isi data di tab **Input Data**, lalu klik **Hitung Analisis**.")
        return
    if ambil_input() != d:
        st.warning("Input sudah berubah setelah perhitungan terakhir. Klik **Hitung Analisis** lagi untuk memperbarui hasil.")

    st.markdown(cincin_efisiensi(h["eta"]), unsafe_allow_html=True)

    r1 = st.columns(3)
    r1[0].markdown(kartu("Daya masukan (P_in)", fmt(h["p_in"], 2), "W"), unsafe_allow_html=True)
    r1[1].markdown(kartu("Daya keluaran (P_out)", fmt(h["p_out"], 2), "W"), unsafe_allow_html=True)
    r1[2].markdown(kartu("Efisiensi (estimasi)", fmt(h["eta"], 2), "%", utama=True), unsafe_allow_html=True)
    r2 = st.columns(3)
    r2[0].markdown(kartu("Rugi tembaga (P_cu)", fmt(h["p_cu"], 2), "W"), unsafe_allow_html=True)
    r2[1].markdown(kartu("Rugi inti (P_core)", fmt(h["p_core"], 2), "W"), unsafe_allow_html=True)
    r2[2].markdown(kartu("Total rugi-rugi (P_loss)", fmt(h["p_loss"], 2), "W"), unsafe_allow_html=True)

    st.markdown("**Interpretasi otomatis**")
    st.info(buat_interpretasi(d, h))

    st.markdown("**Pemeriksaan terpisah: selisih daya masukan dan keluaran**")
    st.write(
        f"P_loss_measured = P_in − P_out = **{fmt(h['p_loss_terukur'], 2)} W**, "
        f"sedangkan rugi-rugi estimasi = **{fmt(h['p_loss'], 2)} W** "
        f"(beda {fmt(h['selisih_metode'], 2)} W). "
        "Keduanya bisa berbeda karena kondisi pengukuran, pembulatan data, dan asumsi model. "
        "Efisiensi di atas hanya memakai rugi-rugi estimasi."
    )

    st.markdown("**Grafik analisis**")
    g1, g2, g3 = st.columns(3)
    for kolom, fungsi in [(g1, grafik_daya), (g2, grafik_rugi), (g3, grafik_efisiensi)]:
        fig = fungsi(h)
        kolom.pyplot(fig)
        plt.close(fig)

    st.markdown("**Tabel ringkasan**")
    df = tabel_ringkasan(d, h)
    st.dataframe(df, hide_index=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Unduh hasil analisis (CSV)",
        data=csv_bytes,
        file_name="hasil_analisis_transformator.csv",
        mime="text/csv",
    )


def tab_rumus():
    st.subheader("Rumus yang Digunakan")
    st.markdown("**Transformator 1 fasa**")
    st.latex(r"P_{in} = V_p \times I_p \times \cos\varphi_p")
    st.latex(r"P_{out} = V_s \times I_s \times \cos\varphi_s")
    st.latex(r"P_{cu} = I_p^2 R_p + I_s^2 R_s")
    st.markdown("**Transformator 3 fasa** (V = tegangan line-to-line, I = arus saluran, R = resistansi per fasa ekuivalen bintang)")
    st.latex(r"P_{in} = \sqrt{3}\, V_p I_p \cos\varphi_p \qquad P_{out} = \sqrt{3}\, V_s I_s \cos\varphi_s")
    st.latex(r"P_{cu} = 3 I_p^2 R_p + 3 I_s^2 R_s")
    st.markdown("**Rugi-rugi total dan efisiensi (metode estimasi)**")
    st.latex(r"P_{loss,total} = P_{cu} + P_{core}")
    st.latex(r"\eta = \frac{P_{out}}{P_{out} + P_{loss,total}} \times 100\%")
    st.markdown("**Pemeriksaan (metode selisih daya, tidak dicampur dengan metode estimasi)**")
    st.latex(r"P_{loss,measured} = P_{in} - P_{out}")
    st.caption(
        "Nilai P_loss estimasi dan P_loss_measured dapat berbeda karena kondisi pengukuran, "
        "pembulatan, dan asumsi model (misalnya arus magnetisasi dan rugi stray tidak dimodelkan terpisah)."
    )

    st.subheader("Sumber dan Status Data")
    st.markdown(
        f"- Katalog SINTRA Distribution Transformers (PDF, V202408): {SUMBER_KATALOG}\n"
        f"- Halaman produk SINTRA: {SUMBER_HALAMAN}\n"
        "- Tabel acuan 1 fasa: SPLN D3.002-2:2008, tegangan 11,547/0,231 kV (katalog PDF menulis 11,574 kV; "
        "program memakai 20/√3 = 11,547 kV)."
    )
    status = pd.DataFrame(
        [
            ("Data spesifikasi (datasheet)", "Kapasitas, tegangan, rugi tanpa beban (rugi inti), rugi beban @75 °C, impedansi, efisiensi PF 1,0"),
            ("Data turunan (dihitung)", "Arus nominal = S/V; Rp dan Rs dari rugi beban datasheet dengan asumsi pembagian 50:50"),
            ("Data simulasi/asumsi", "Beban 100%, cos φ sekunder 0,85, cos φ primer skenario simulasi"),
            ("Data hasil pengukuran", "Tidak ada. Pengguna dapat mengisi data uji sendiri di tab Input Data"),
        ],
        columns=["Kategori", "Isi"],
    )
    st.dataframe(status, hide_index=True)
    st.subheader("Keterbatasan")
    st.markdown(
        "- Model rugi hanya rugi tembaga dan rugi inti; rugi stray dan dielektrik tidak dihitung terpisah.\n"
        "- Rugi inti dianggap tetap (tidak bergantung beban); resistansi dianggap tetap terhadap suhu.\n"
        "- Resistansi pada data awal diturunkan dari rugi beban datasheet, bukan hasil uji kumparan."
    )


def main():
    st.set_page_config(page_title="Kalkulator Transformator Distribusi", page_icon="⚡", layout="wide")
    global GRAFIK_GELAP
    # Tombol pilih tema (kanan atas). Nilainya disimpan di st.session_state["tema_gelap"].
    _, kolom_tema = st.columns([5, 1])
    gelap = kolom_tema.toggle("🌙 Mode gelap", key="tema_gelap")
    GRAFIK_GELAP = gelap
    st.markdown(CSS + (CSS_GELAP if gelap else ""), unsafe_allow_html=True)
    inisialisasi_state()

    st.markdown(
        '<div class="hero"><p class="judul"><span class="kilat">⚡</span>Analisis Rugi-Rugi Daya dan Efisiensi Transformator Distribusi</p>'
        '<p class="sub">Kalkulator interaktif berbasis Python untuk menghitung rugi tembaga, rugi inti, '
        "total rugi-rugi, dan efisiensi transformator distribusi 1 fasa atau 3 fasa.</p>"
        '<span class="chip">Python</span><span class="chip">Streamlit</span>'
        '<span class="chip">Pandas</span><span class="chip">Matplotlib</span></div>',
        unsafe_allow_html=True,
    )

    t1, t2, t3, t4 = st.tabs(["Dashboard", "Input Data", "Hasil & Grafik", "Rumus & Sumber"])
    with t1:
        tab_dashboard()
    with t2:
        tab_input()
    with t3:
        tab_hasil()
    with t4:
        tab_rumus()


if __name__ == "__main__":
    main()
