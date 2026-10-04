from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
import requests
import streamlit as st

st.set_page_config(
    page_title="PUSDALOPS PB PAPUA - Generator Laporan", layout="wide"
)

# 1. WAKTU OTOMATIS WIT (UTC+9)
WIT = timezone(timedelta(hours=9))
now_wit = datetime.now(WIT)

HARI = {
    "Monday": "Senin",
    "Tuesday": "Selasa",
    "Wednesday": "Rabu",
    "Thursday": "Kamis",
    "Friday": "Jumat",
    "Saturday": "Sabtu",
    "Sunday": "Minggu",
}
BULAN = {
    1: "Januari",
    2: "Februari",
    3: "Maret",
    4: "April",
    5: "Mei",
    6: "Juni",
    7: "Juli",
    8: "Agustus",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Desember",
}

nama_hari = HARI.get(now_wit.strftime("%A"), now_wit.strftime("%A"))
nama_bulan = BULAN.get(now_wit.month, "")
waktu_teks = f"{nama_hari}, {now_wit.day} {nama_bulan} {now_wit.year} | {now_wit.strftime('%H.%M')} WIT"

st.title("🛡️ Generator Laporan Periodik PUSDALOPS PB BPBD PAPUA")
col1, col2 = st.columns([3, 1])
with col1:
    st.caption(f"🕒 Waktu Pemantauan Otomatis: **{waktu_teks}**")
with col2:
    if st.button("🔄 Tarik Data Tabel BMKG"):
        st.cache_data.clear()
        st.rerun()

# 2. FUNGSI AMBIL ANGIN KHUSUS KOTA JAYAPURA (API BMKG)
def get_angin_jayapura():
    """Mengambil kecepatan (km/jam) dan arah angin terkini Kota Jayapura"""
    url = "https://api.bmkg.go.id/publik/prakiraan-cuaca?adm2=91.71"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            data = res.json()
            items = data.get("data", [])
            if items:
                cuaca_list = items[0].get("cuaca", [])
                if cuaca_list:
                    c = cuaca_list[0][0] if isinstance(cuaca_list[0], list) else cuaca_list[0]
                    ws = c.get("ws", "10")
                    wd = c.get("wd", "Timur")
                    # Format: 10 km/jam dari Timur
                    if wd:
                        return f"({ws} km/jam dari {wd})"
                    return f"({ws} km/jam)"
    except Exception:
        pass
    return "(10 km/jam dari Timur)"


# 3. FUNGSI SCRAPING TABEL HTML BMKG PROVINSI
@st.cache_data(ttl=300)
def scrape_bmkg_table():
    url = "https://www.bmkg.go.id/cuaca/prakiraan-cuaca/91"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    jpr_data = {
        "kondisi": "Berawan",
        "suhu": "24-27",
        "kelembapan": "78-97",
        "angin": "(10 km/jam dari Timur)",
    }
    dinamika = {
        "Cerah": [],
        "Cerah Berawan": [],
        "Berawan": [],
        "Hujan Ringan": [],
        "Hujan Sedang": [],
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            tbody = soup.find("tbody")

            if tbody:
                rows = tbody.find_all("tr")
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) >= 2:
                        # Kolom 0: Nama Kabupaten/Kota
                        nama_wilayah = cols[0].text.strip()

                        # Rapikan penamaan standar Pusdalops
                        if nama_wilayah == "Jayapura":
                            nama_wilayah = "Kab. Jayapura"
                        elif nama_wilayah == "Waropen":
                            nama_wilayah = "Kab. Waropen"

                        # Kolom 1: Cuaca Hari Ini (Kondisi, Suhu, Kelembapan)
                        p_tags = cols[1].find_all("p")
                        if len(p_tags) >= 3:
                            kondisi = p_tags[0].text.strip()
                            suhu = p_tags[1].text.replace("°C", "").strip()
                            kelembapan = p_tags[2].text.replace("%", "").strip()

                            # Ekstrak khusus Kota Jayapura
                            if nama_wilayah == "Kota Jayapura":
                                jpr_data["kondisi"] = kondisi
                                jpr_data["suhu"] = suhu
                                jpr_data["kelembapan"] = kelembapan

                            # Masukkan ke Dinamika Cuaca
                            matched = False
                            for key in dinamika.keys():
                                if key.lower() == kondisi.lower():
                                    dinamika[key].append(nama_wilayah)
                                    matched = True
                                    break

                            if not matched:
                                if kondisi not in dinamika:
                                    dinamika[kondisi] = []
                                dinamika[kondisi].append(nama_wilayah)
    except Exception as e:
        st.error(f"Gagal mengambil tabel data: {e}")

    # Ambil data angin & arah angin Jayapura
    jpr_data["angin"] = get_angin_jayapura()

    return jpr_data, dinamika


with st.spinner("Membaca data cuaca & angin dari BMKG..."):
    cuaca_jpr, dinamika_cuaca = scrape_bmkg_table()

# 4. SUSUN TEKS DINAMIKA
kategori_utama = ["Cerah", "Cerah Berawan", "Berawan", "Hujan Ringan", "Hujan Sedang"]
baris_dinamika = []

for kat in kategori_utama:
    wilayah_list = dinamika_cuaca.get(kat, [])
    baris_dinamika.append(
        f"🔸 {kat} : {', '.join(wilayah_list) if wilayah_list else '-'}"
    )

for kat, wilayah_list in dinamika_cuaca.items():
    if kat not in kategori_utama and wilayah_list:
        baris_dinamika.append(f"🔸 {kat} : {', '.join(wilayah_list)}")

dinamika_str = "\n".join(baris_dinamika)

# 5. TEMPLATE LAPORAN
laporan_final_text = f"""LAPORAN PERIODIK PUSDALOPS PB BPBD PROVINSI PAPUA
Waktu Pemantauan: {waktu_teks}

Kepada Yth:
1. Kepala BNPB
2. Gubernur Provinsi Papua
3. Sekda Provinsi Papua (Ka. BPBD Ex-Officio)
4. Kalaksa BPBD Provinsi Papua

1. STATUS KEJADIAN BENCANA:
NIHIL (Kondisi Wilayah Aman dan Terkendali)

2. RINGKASAN CUACA (BMKG) Kota Jayapura
🔹 Kondisi Umum: {cuaca_jpr['kondisi']}
🔹 Suhu: {cuaca_jpr['suhu']}°C | Kelembapan: {cuaca_jpr['kelembapan']}% | Kecepatan Angin: {cuaca_jpr['angin']}

   Dinamika Cuaca Wilayah:
{dinamika_str}

3. KEGIATAN OPERASIONAL PUSDALOPS :
▪️ Peringatan Dini: Penyebarluasan informasi cuaca dan potensi bencana via medsos dan radio komunikasi.
▪️ Monitoring Wilayah: Pemantauan intensif di 8 kabupaten dan 1 kota se-Provinsi Papua.
▪️ Administrasi & Logistik: Pengolahan data kebencanaan dan pemeliharaan/pengecekan kesiapan peralatan PB.

4. PETUGAS
▪️ Supervisor: M. Sandy. SE
▪️ Tim Operator: Melkianus Giay. ST, Sultan K. Pitang, Albert F. Unane, Bambang Ayomi

Demikian laporan disampaikan. Pemantauan terus dilakukan dan perkembangan lebih lanjut akan dilaporkan pada kesempatan pertama.

PUSDALOPS PB BPBD PROVINSI PAPUA
Kontak : +62 821-9041-100"""

st.subheader("📝 Laporan Siap Kirim (Bisa Diedit)")
laporan_edit = st.text_area(
    "Edit jika diperlukan:", value=laporan_final_text, height=450
)

st.subheader("📋 Salin Teks ke WhatsApp")
st.code(laporan_edit, language="text")
st.caption(
    "Klik icon 'Copy' di pojok kanan atas blok abu-abu ini untuk menyalin seluruh teks."
)
