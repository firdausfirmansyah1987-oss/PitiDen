import streamlit as st
import pandas as pd
import requests
import uuid
import time
from datetime import datetime
import plotly.express as px

# --- PENGATURAN HALAMAN (Harus di baris paling atas) ---
st.set_page_config(page_title="PitiDen", page_icon="💳", layout="centered")

# --- KUSTOMISASI TAMPILAN (CSS UNTUK FANCY FONT & MOBILE) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Pacifico&family=Quicksand:wght@400;600;700&display=swap');

/* Menerapkan font Quicksand untuk seluruh teks */
html, body, [class*="css"] {
    font-family: 'Quicksand', sans-serif !important;
}

/* Menerapkan font Fancy (Pacifico) untuk judul dan header */
h1, h2, h3 {
    font-family: 'Pacifico', cursive !important;
    color: #2c3e50;
    text-align: center;
}

/* Memperbesar ukuran teks dan ikon di opsi Radio (Masuk/Keluar) */
.stRadio > div {
    gap: 20px;
}
.stRadio p {
    font-size: 20px !important;
    font-weight: 600 !important;
}

/* Menyesuaikan padding agar pas dan lebar di layar HP Portrait */
.block-container {
    padding-top: 2rem !important;
    padding-bottom: 2rem !important;
    max-width: 100% !important;
}

/* Memperbesar ikon metrik Dashboard */
[data-testid="stMetricValue"] {
    font-size: 28px !important;
}
</style>
""", unsafe_allow_html=True)

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

# Inisialisasi Data di Session State
if 'data' not in st.session_state:
    st.session_state.data = load_data()

# Inisialisasi Kunci (Keys) untuk mengosongkan input form
if 'input_nominal' not in st.session_state: st.session_state.input_nominal = 0
if 'input_keterangan' not in st.session_state: st.session_state.input_keterangan = ""

data_transaksi = st.session_state.data

# --- HITUNG SALDO ---
total_masuk = sum(t['nominal'] for t in data_transaksi if t['jenis'] == 'Masuk')
total_keluar = sum(t['nominal'] for t in data_transaksi if t['jenis'] == 'Keluar')
saldo_sekarang = total_masuk - total_keluar

# --- TAMPILAN DASHBOARD ---
st.markdown("<h1>💳 PitiDen</h1>", unsafe_allow_html=True)
st.write("---")

col1, col2, col3 = st.columns(3)
col1.metric(label="💰 Total Saldo", value=format_rupiah(saldo_sekarang))
col2.metric(label="📈 Pemasukan", value=format_rupiah(total_masuk))
col3.metric(label="📉 Pengeluaran", value=format_rupiah(total_keluar))

st.write("---")

# --- MENU APLIKASI ---
tab1, tab2, tab3 = st.tabs(["💸 Catat Transaksi", "🧾 Riwayat & Hapus", "⚖️ Bandingkan"])

# TAB 1: CATAT TRANSAKSI (Tanpa st.form agar Kategori dinamis real-time)
with tab1:
    st.markdown("<h3>📥 Tambah Transaksi</h3>", unsafe_allow_html=True)
    
    # Opsi dinamis dengan ikon visual besar
    jenis = st.radio(
        "Pilih Jenis Uang", 
        options=["Masuk", "Keluar"], 
        format_func=lambda x: "🟢 Uang Masuk" if x == "Masuk" else "🔴 Uang Keluar",
        horizontal=True
    )
    
    # Kategori otomatis berubah (karena kita tidak pakai st.form)
    if jenis == "Masuk":
        kategori_opsi = ["Gaji", "Usaha", "Proyek", "Honor", "Lainnya"]
    else:
        kategori_opsi = ["Tagihan Rutin (SPP, Listrik, Air)", "Kebutuhan Pokok", "Transportasi", "Kesehatan", "Hiburan", "Sosial", "Lainnya"]
        
    kategori = st.selectbox("📂 Kategori", kategori_opsi)
    tanggal = st.date_input("📅 Tanggal Transaksi", datetime.today())
    
    # Menghubungkan input dengan session_state keys agar bisa di-reset
    nominal = st.number_input("💵 Nominal (Rp)", min_value=0, step=5000, key="input_nominal")
    keterangan = st.text_input("📝 Keterangan Tambahan", key="input_keterangan")
    
    # Tombol simpan
    if st.button("💾 Simpan Transaksi", use_container_width=True):
        if st.session_state.input_nominal > 0:
            transaksi_baru = {
                "id": str(uuid.uuid4())[:8],
                "tanggal": tanggal.strftime("%Y-%m-%d"),
                "jenis": jenis,
                "kategori": kategori,
                "nominal": st.session_state.input_nominal,
                "keterangan": st.session_state.input_keterangan
            }
            st.session_state.data.append(transaksi_baru)
            save_data(st.session_state.data)
            
            st.success("✅ Yey! Transaksi berhasil disimpan.")
            time.sleep(1.2)
            
            # Reset form input
            st.session_state.input_nominal = 0
            st.session_state.input_keterangan = ""
            st.rerun()
        else:
            st.error("⚠️ Nominal tidak boleh kosong atau nol!")

# TAB 2: RIWAYAT & HAPUS (Desain Card UI untuk Layar HP)
with tab2:
    st.markdown("<h3>📜 Riwayat Transaksi Anda</h3>", unsafe_allow_html=True)
    if len(st.session_state.data) == 0:
        st.info("💡 Belum ada transaksi yang dicatat.")
    else:
        df = pd.DataFrame(st.session_state.data)
        df = df.sort_values(by="tanggal", ascending=False).reset_index(drop=True)
        
        # Desain Card Tumpuk Bawah (Sangat Ramah Mobile)
        for index, row in df.iterrows():
            with st.container():
                c1, c2 = st.columns([3, 1.5])
                
                with c1:
                    ikon_status = "🟢" if row['jenis'] == 'Masuk' else "🔴"
                    # Kategori sebagai Header Card
                    st.markdown(f"**{ikon_status} {row['kategori']}**")
                    # Detail Keterangan dan Tanggal (Mengecil)
                    st.caption(f"📅 {row['tanggal']} | 📝 {row['keterangan'] if row['keterangan'] else '-'}")
                
                with c2:
                    # Nominal rata kanan (tergantung layout, dibuat tebal)
                    warna_teks = "green" if row['jenis'] == 'Masuk' else "red"
                    st.markdown(f"<p style='color:{warna_teks}; font-weight:bold; font-size:18px; margin:0;'>{format_rupiah(row['nominal'])}</p>", unsafe_allow_html=True)
                    
                    # Tombol hapus pas di bawah nominal
                    if st.button("🗑️ Hapus", key=f"hapus_{row['id']}", use_container_width=True):
                        st.session_state.data = [t for t in st.session_state.data if t['id'] != row['id']]
                        save_data(st.session_state.data)
                        st.rerun()
            st.divider() # Garis pemisah antar kartu

# TAB 3: STATISTIK PERBANDINGAN (DIAGRAM DONAT)
with tab3:
    st.markdown("<h3>⚖️ Analisis Keuangan</h3>", unsafe_allow_html=True)
    
    if total_masuk > 0 or total_keluar > 0:
        df_chart = pd.DataFrame({
            "Jenis": ["Pemasukan", "Pengeluaran"],
            "Nominal": [total_masuk, total_keluar],
            "Teks": [format_rupiah(total_masuk), format_rupiah(total_keluar)] 
        })
        
        df_chart = df_chart[df_chart["Nominal"] > 0]
        
        fig = px.pie(
            df_chart, 
            values='Nominal', 
            names='Jenis', 
            hole=0.5, 
            color='Jenis',
            color_discrete_map={'Pemasukan': '#2ecc71', 'Pengeluaran': '#e74c3c'}
        )
        
        fig.update_traces(
            textinfo='percent+label',
            texttemplate='<b>%{label}</b><br>%{percent}<br>%{customdata[0]}',
            customdata=df_chart[['Teks']],
            textfont_size=14,
            textposition='inside',
            insidetextorientation='horizontal'
        )
        
        # Sembunyikan legenda samping agar pas di HP (fokus ke tulisan dalam donat)
        fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.write("---")
        if total_masuk > total_keluar:
            st.success(f"🥳 Keren! Ada sisa uang **{format_rupiah(saldo_sekarang)}** yang bisa ditabung.")
        elif total_keluar > total_masuk:
            st.error(f"⚠️ Hati-hati! Pengeluaranmu meluap **{format_rupiah(total_keluar - total_masuk)}** dari pemasukan.")
        else:
            st.warning("⚖️ Pemasukan dan pengeluaran persis sama.")
    else:
        st.info("💡 Belum ada data keuangan untuk dibandingkan.")
