import streamlit as st
import pandas as pd
import requests
import uuid
import time
from datetime import datetime
import plotly.express as px # Tambahan untuk grafik Donat

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
st.set_page_config(page_title="PitiDen", page_icon="💳", layout="centered")

if 'data' not in st.session_state:
    st.session_state.data = load_data()

data_transaksi = st.session_state.data

# --- HITUNG SALDO ---
total_masuk = sum(t['nominal'] for t in data_transaksi if t['jenis'] == 'Masuk')
total_keluar = sum(t['nominal'] for t in data_transaksi if t['jenis'] == 'Keluar')
saldo_sekarang = total_masuk - total_keluar

# --- TAMPILAN DASHBOARD ---
st.title("💳 PitiDen")
st.write("---")

col1, col2, col3 = st.columns(3)
col1.metric(label="💰 Total Saldo", value=format_rupiah(saldo_sekarang))
col2.metric(label="📈 Pemasukan", value=format_rupiah(total_masuk))
col3.metric(label="📉 Pengeluaran", value=format_rupiah(total_keluar))

st.write("---")

# --- MENU APLIKASI ---
tab1, tab2, tab3 = st.tabs(["💸 Catat Transaksi", "🧾 Riwayat & Hapus", "⚖️ Bandingkan"])

# TAB 1: CATAT TRANSAKSI
with tab1:
    st.subheader("📥 Tambah Transaksi Baru")
    with st.form("form_transaksi", clear_on_submit=True):
        
        # Pilihan dinamis dengan format warna Icon (Nilai aslinya tetap 'Masuk' atau 'Keluar')
        jenis = st.radio(
            "🏷️ Jenis Transaksi", 
            options=["Masuk", "Keluar"], 
            format_func=lambda x: "🟢 Uang Masuk" if x == "Masuk" else "🔴 Uang Keluar",
            horizontal=True
        )
        
        # Opsi Kategori otomatis berganti menyesuaikan pilihan Radio Button di atas
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
                
                st.success("✅ Yey! Transaksi berhasil disimpan ke database.")
                time.sleep(1.2) # Jeda lebih lama sedikit agar nyaman dibaca
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

# TAB 3: STATISTIK PERBANDINGAN (DIAGRAM DONAT)
with tab3:
    st.subheader("⚖️ Perbandingan Pemasukan & Pengeluaran")
    
    if total_masuk > 0 or total_keluar > 0:
        # Menyiapkan data untuk Plotly
        df_chart = pd.DataFrame({
            "Jenis": ["Pemasukan", "Pengeluaran"],
            "Nominal": [total_masuk, total_keluar],
            # Membuat kolom teks khusus agar format nominalnya menggunakan titik ala Indonesia
            "Teks": [format_rupiah(total_masuk), format_rupiah(total_keluar)] 
        })
        
        # Filter nilai 0 agar tidak merusak tampilan donat
        df_chart = df_chart[df_chart["Nominal"] > 0]
        
        # Membuat Grafik Donat
        fig = px.pie(
            df_chart, 
            values='Nominal', 
            names='Jenis', 
            hole=0.5, # Membuat lubang di tengah (Donat)
            color='Jenis',
            color_discrete_map={'Pemasukan': '#2ecc71', 'Pengeluaran': '#e74c3c'} # Hijau & Merah
        )
        
        # Konfigurasi Teks di dalam Donat (% dan Nominal)
        fig.update_traces(
            textinfo='percent+label',
            texttemplate='<b>%{label}</b><br>%{percent}<br>%{customdata[0]}',
            customdata=df_chart[['Teks']],
            textposition='inside',
            insidetextorientation='horizontal'
        )
        
        # Tampilkan ke Streamlit
        st.plotly_chart(fig, use_container_width=True)
        
        # Analisis Sederhana
        st.write("---")
        if total_masuk > total_keluar:
            st.success(f"🥳 Keren! Pemasukan lebih besar. Ada sisa uang **{format_rupiah(saldo_sekarang)}**.")
        elif total_keluar > total_masuk:
            st.error(f"⚠️ Hati-hati! Pengeluaran lebih besar **{format_rupiah(total_keluar - total_masuk)}** dari pemasukan.")
        else:
            st.warning("⚖️ Pemasukan dan pengeluaran persis sama (Nol).")
    else:
        st.info("💡 Belum ada data keuangan untuk dibandingkan.")
