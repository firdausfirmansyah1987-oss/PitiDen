import streamlit as st
import pandas as pd
import requests
import uuid
from datetime import datetime

# --- KONFIGURASI JSONBIN ---
# Nanti kita akan menyembunyikan API Key ini di Streamlit Secrets
BIN_ID = st.secrets["BIN_ID"]
API_KEY = st.secrets["API_KEY"]
URL = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
HEADERS = {
    'X-Master-Key': API_KEY,
    'Content-Type': 'application/json'
}

# --- FUNGSI FORMAT RUPIAH ---
def format_rupiah(angka):
    # Mengubah angka menjadi format ribuan dengan titik (contoh: 3.500.000)
    return f"Rp {angka:,.0f}".replace(',', '.')

# --- FUNGSI DATABASE ---
def load_data():
    try:
        req = requests.get(URL, headers=HEADERS)
        data = req.json()
        return data['record'].get('transaksi', [])
    except:
        return []

def save_data(data):
    payload = {"transaksi": data}
    requests.put(URL, json=payload, headers=HEADERS)

# --- PENGATURAN HALAMAN ---
st.set_page_config(page_title="DompetKu", page_icon="💳", layout="centered")

# Inisialisasi Data di Session State agar aplikasi lebih cepat
if 'data' not in st.session_state:
    st.session_state.data = load_data()

data_transaksi = st.session_state.data

# --- HITUNG SALDO UNTUK DASHBOARD ---
total_masuk = sum(t['nominal'] for t in data_transaksi if t['jenis'] == 'Masuk')
total_keluar = sum(t['nominal'] for t in data_transaksi if t['jenis'] == 'Keluar')
saldo_sekarang = total_masuk - total_keluar

# --- TAMPILAN DASHBOARD (Ala E-Wallet) ---
st.title("💳 DompetKu")
st.write("---")

# Membuat Card Metric
col1, col2, col3 = st.columns(3)
col1.metric(label="💰 Total Saldo", value=format_rupiah(saldo_sekarang))
col2.metric(label="📈 Pemasukan", value=format_rupiah(total_masuk))
col3.metric(label="📉 Pengeluaran", value=format_rupiah(total_keluar))

st.write("---")

# --- MENU APLIKASI ---
tab1, tab2, tab3 = st.tabs(["📝 Catat Transaksi", "📊 Riwayat & Hapus", "📈 Statistik"])

# TAB 1: CATAT TRANSAKSI
with tab1:
    st.subheader("Tambah Transaksi Baru")
    # Menambahkan clear_on_submit=True agar form otomatis kosong setelah disimpan
    with st.form("form_transaksi", clear_on_submit=True):
        jenis = st.radio("Jenis Transaksi", ["Masuk", "Keluar"], horizontal=True)
        
        # Opsi Kategori Dinamis
        if jenis == "Masuk":
            kategori_opsi = ["Gaji", "Usaha", "Proyek", "Honor", "Lainnya"]
        else:
            kategori_opsi = ["Tagihan Rutin (SPP, Listrik, Air)", "Kebutuhan Pokok", "Transportasi", "Kesehatan", "Hiburan", "Sosial", "Lainnya"]
            
        kategori = st.selectbox("Kategori", kategori_opsi)
        
        # Tanggal otomatis hari ini, tapi bisa diganti
        tanggal = st.date_input("Tanggal Transaksi", datetime.today())
        
        nominal = st.number_input("Nominal (Rp)", min_value=0, step=5000)
        keterangan = st.text_input("Keterangan Tambahan")
        
        submit = st.form_submit_button("Simpan Transaksi")
        
        if submit:
            if nominal > 0:
                transaksi_baru = {
                    "id": str(uuid.uuid4())[:8],
                    "tanggal": tanggal.strftime("%Y-%m-%d"),
                    "jenis": jenis,
                    "kategori": kategori,
                    "nominal": nominal,
                    "keterangan": keterangan
                }
                st.session_state.data.append(transaksi_baru)
                save_data(st.session_state.data)
                st.success("Berhasil dicatat!")
                st.rerun()
            else:
                st.error("Nominal tidak boleh kosong!")

# TAB 2: RIWAYAT & HAPUS
with tab2:
    st.subheader("Riwayat Transaksi")
    if len(st.session_state.data) == 0:
        st.info("Belum ada transaksi dicatat.")
    else:
        # Ubah ke DataFrame Pandas agar mudah diurutkan
        df = pd.DataFrame(st.session_state.data)
        # Urutkan dari yang terbaru
        df = df.sort_values(by="tanggal", ascending=False).reset_index(drop=True)
        
        # --- MEMBUAT TABEL CUSTOM DENGAN TOMBOL HAPUS ---
        # Header Tabel
        col_h1, col_h2, col_h3, col_h4, col_h5, col_h6 = st.columns([2, 1.5, 2.5, 2, 2.5, 1.5])
        col_h1.markdown("**Tanggal**")
        col_h2.markdown("**Jenis**")
        col_h3.markdown("**Kategori**")
        col_h4.markdown("**Nominal**")
        col_h5.markdown("**Keterangan**")
        col_h6.markdown("**Aksi**")
        st.write("---")
        
        # Isi Tabel (Looping tiap baris data)
        for index, row in df.iterrows():
            col1, col2, col3, col4, col5, col6 = st.columns([2, 1.5, 2.5, 2, 2.5, 1.5])
            
            col1.write(row['tanggal'])
            
            # Beri warna teks untuk membedakan Masuk (Hijau) & Keluar (Merah)
            if row['jenis'] == 'Masuk':
                col2.markdown("🟢 Masuk")
            else:
                col2.markdown("🔴 Keluar")
                
            col3.write(row['kategori'])
            col4.write(format_rupiah(row['nominal'])) # Menggunakan pemisah ribuan
            col5.write(row['keterangan'] if row['keterangan'] else "-")
            
            # Tombol hapus langsung di setiap baris
            if col6.button("❌ Hapus", key=f"hapus_{row['id']}"):
                # Hapus dari session state
                st.session_state.data = [t for t in st.session_state.data if t['id'] != row['id']]
                # Simpan ulang ke JSONBin
                save_data(st.session_state.data)
                # Refresh halaman
                st.rerun()

# TAB 3: STATISTIK SEDERHANA
with tab3:
    st.subheader("Grafik Pengeluaran")
    if len(st.session_state.data) > 0:
        df_keluar = pd.DataFrame([t for t in st.session_state.data if t['jenis'] == 'Keluar'])
        if not df_keluar.empty:
            pengeluaran_grup = df_keluar.groupby("kategori")["nominal"].sum()
            st.bar_chart(pengeluaran_grup)
        else:
            st.info("Belum ada data pengeluaran.")
