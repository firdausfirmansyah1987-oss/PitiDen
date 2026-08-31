import streamlit as st
import pandas as pd
import requests
import uuid
import time
from datetime import datetime

# --- KONFIGURASI JSONBIN ---
BIN_ID = st.secrets["BIN_ID"]
API_KEY = st.secrets["API_KEY"]
URL = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
HEADERS = {
    'X-Master-Key': API_KEY,
    'Content-Type': 'application/json'
}

# --- FUNGSI FORMAT RUPIAH ---
def format_rupiah(angka):
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

if 'data' not in st.session_state:
    st.session_state.data = load_data()

data_transaksi = st.session_state.data

# --- HITUNG SALDO ---
total_masuk = sum(t['nominal'] for t in data_transaksi if t['jenis'] == 'Masuk')
total_keluar = sum(t['nominal'] for t in data_transaksi if t['jenis'] == 'Keluar')
saldo_sekarang = total_masuk - total_keluar

# --- TAMPILAN DASHBOARD ---
st.title("💳 DompetKu - Catatan Keuangan")
st.write("---")

col1, col2, col3 = st.columns(3)
col1.metric(label="💰 Total Saldo", value=format_rupiah(saldo_sekarang))
col2.metric(label="📈 Pemasukan", value=format_rupiah(total_masuk))
col3.metric(label="📉 Pengeluaran", value=format_rupiah(total_keluar))

st.write("---")

# --- MENU APLIKASI (Dengan Ikon Baru) ---
tab1, tab2, tab3 = st.tabs(["💸 Catat Transaksi", "🧾 Riwayat & Hapus", "⚖️ Bandingkan"])

# TAB 1: CATAT TRANSAKSI
with tab1:
    st.subheader("📥 Tambah Transaksi Baru")
    with st.form("form_transaksi", clear_on_submit=True):
        jenis = st.radio("🏷️ Jenis Transaksi", ["Masuk", "Keluar"], horizontal=True)
        
        if jenis == "Masuk":
            kategori_opsi = ["Gaji", "Usaha", "Proyek", "Honor", "Lainnya"]
        else:
            kategori_opsi = ["Tagihan Rutin (SPP, Listrik, Air)", "Kebutuhan Pokok", "Transportasi", "Kesehatan", "Hiburan", "Sosial", "Lainnya"]
            
        kategori = st.selectbox("📂 Kategori", kategori_opsi)
        tanggal = st.date_input("📅 Tanggal Transaksi", datetime.today())
        nominal = st.number_input("💵 Nominal (Rp)", min_value=0, step=5000)
        keterangan = st.text_input("📝 Keterangan Tambahan")
        
        submit = st.form_submit_button("💾 Simpan Transaksi")
        
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
                
                # Menampilkan notifikasi sukses berwarna hijau
                st.success("✅ Yey! Transaksi berhasil disimpan ke database.")
                
                # Memberi jeda 1 detik agar notifikasi terbaca sebelum halaman diperbarui
                time.sleep(1)
                st.rerun()
            else:
                st.error("⚠️ Nominal tidak boleh kosong atau nol!")

# TAB 2: RIWAYAT & HAPUS
with tab2:
    st.subheader("📜 Riwayat Transaksi Anda")
    if len(st.session_state.data) == 0:
        st.info("💡 Belum ada transaksi yang dicatat.")
    else:
        df = pd.DataFrame(st.session_state.data)
        df = df.sort_values(by="tanggal", ascending=False).reset_index(drop=True)
        
        col_h1, col_h2, col_h3, col_h4, col_h5, col_h6 = st.columns([2, 1.5, 2.5, 2, 2.5, 1.5])
        col_h1.markdown("**📅 Tanggal**")
        col_h2.markdown("**🏷️ Jenis**")
        col_h3.markdown("**📂 Kategori**")
        col_h4.markdown("**💵 Nominal**")
        col_h5.markdown("**📝 Keterangan**")
        col_h6.markdown("**⚙️ Aksi**")
        st.write("---")
        
        for index, row in df.iterrows():
            col1, col2, col3, col4, col5, col6 = st.columns([2, 1.5, 2.5, 2, 2.5, 1.5])
            col1.write(row['tanggal'])
            if row['jenis'] == 'Masuk':
                col2.markdown("🟢 Masuk")
            else:
                col2.markdown("🔴 Keluar")
            col3.write(row['kategori'])
            col4.write(format_rupiah(row['nominal']))
            col5.write(row['keterangan'] if row['keterangan'] else "-")
            
            if col6.button("❌ Hapus", key=f"hapus_{row['id']}"):
                st.session_state.data = [t for t in st.session_state.data if t['id'] != row['id']]
                save_data(st.session_state.data)
                st.rerun()

# TAB 3: STATISTIK PERBANDINGAN
with tab3:
    st.subheader("⚖️ Perbandingan Pemasukan & Pengeluaran")
    
    if total_masuk > 0 or total_keluar > 0:
        # Menyiapkan data untuk grafik
        df_chart = pd.DataFrame({
            "Jenis": ["Masuk", "Keluar"],
            "Nominal": [total_masuk, total_keluar]
        })
        
        # Jadikan 'Jenis' sebagai index agar label grafiknya rapi di Streamlit
        df_chart.set_index("Jenis", inplace=True)
        
        # Menampilkan grafik batang
        st.bar_chart(df_chart)
        
        # Tambahan Analisis Sederhana
        st.write("---")
        if total_masuk > total_keluar:
            st.success(f"🥳 Keren! Pemasukanmu lebih besar dari pengeluaran. Ada sisa uang sebesar **{format_rupiah(saldo_sekarang)}** yang bisa ditabung.")
        elif total_keluar > total_masuk:
            st.error(f"⚠️ Hati-hati! Pengeluaranmu lebih besar **{format_rupiah(total_keluar - total_masuk)}** dari pemasukan. Coba cek ulang riwayat belanjamu.")
        else:
            st.warning("⚖️ Pemasukan dan pengeluaranmu persis sama (Impasse/Nol).")
    else:
        st.info("💡 Belum ada data keuangan untuk dibandingkan.")
