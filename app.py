import streamlit as st
import pandas as pd
import numpy as np

# Sayfa Ayarları
st.set_page_config(page_title="Cronbach's Alpha Optimizer", layout="wide")

def calculate_cronbach_alpha(df):
    """
    Verilen DataFrame için Cronbach's Alpha değerini hesaplar.
    """
    df_clean = df.dropna()
    item_count = df_clean.shape[1]
    
    if item_count < 2:
        return 0.0
    
    item_variances = df_clean.var(axis=0, ddof=1)
    total_score_variance = df_clean.sum(axis=1).var(ddof=1)
    
    if total_score_variance == 0:
        return 0.0
    
    alpha = (item_count / (item_count - 1)) * (1 - (item_variances.sum() / total_score_variance))
    return alpha

def optimize_scale(df, target=0.70):
    history = []
    current_cols = list(df.columns)
    
    initial_alpha = calculate_cronbach_alpha(df[current_cols])
    history.append({
        "step": 0,
        "removed_item": None,
        "alpha": initial_alpha,
        "remaining_items": current_cols.copy()
    })
    
    best_alpha = initial_alpha
    max_alpha_scenario = history[0]
    target_reached_scenario = None

    if initial_alpha >= target:
        target_reached_scenario = history[0]

    step = 1
    # En az 2 madde kalana kadar döngü
    while len(current_cols) > 2:
        item_scores = {}
        
        for col in current_cols:
            temp_cols = [c for c in current_cols if c != col]
            score = calculate_cronbach_alpha(df[temp_cols])
            item_scores[col] = score
        
        best_item_to_remove = max(item_scores, key=item_scores.get)
        new_alpha = item_scores[best_item_to_remove]
        
        current_cols.remove(best_item_to_remove)
        
        scenario = {
            "step": step,
            "removed_item": best_item_to_remove,
            "alpha": new_alpha,
            "remaining_items": current_cols.copy()
        }
        history.append(scenario)
        
        if new_alpha > best_alpha:
            best_alpha = new_alpha
            max_alpha_scenario = scenario
            
        if target_reached_scenario is None and new_alpha >= target:
            target_reached_scenario = scenario
            
        step += 1
        
    return history, target_reached_scenario, max_alpha_scenario

# --- ARAYÜZ (UI) ---

st.title("📊 Cronbach's Alpha Optimizer")
st.markdown("Excel dosyanızı yükleyin, sayısal verileri otomatik ayıralım ve ölçeğinizi optimize edelim.")

uploaded_file = st.file_uploader("Excel Dosyasını Yükle (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        # Excel'i yükle
        df_raw = pd.read_excel(uploaded_file)
        
        # --- OTOMATİK AYRIŞTIRMA (Sayısal vs Metin) ---
        numeric_df = df_raw.select_dtypes(include=[np.number])
        text_df = df_raw.select_dtypes(exclude=[np.number])
        
        numeric_cols = numeric_df.columns.tolist()
        text_cols = text_df.columns.tolist()

        st.success(f"Dosya Analiz Edildi: Toplam {len(numeric_cols)} sayısal sütun, {len(text_cols)} metin sütunu bulundu.")
        
        # Veri Önizleme (Sütun adlarını net görmek için)
        with st.expander("📄 Yüklenen Veriyi Önizle (İlk 5 Satır)"):
            st.dataframe(df_raw.head())
            if text_cols:
                st.caption(f"⚠️ Şu sütunlar metin içerdiği için analize dahil edilmeyecek: {', '.join(text_cols)}")

        st.divider()

        # --- SÜTUN SEÇİM EKRANI ---
        st.subheader("1. Analiz Edilecek Soruları Seçin")
        
        col1, col2 = st.columns([3, 1])
        
        with col2:
            # Tümünü Seç / Kaldır butonları
            st.write("") # Boşluk bırakmak için
            st.write("") 
            if st.button("Tümünü Seç"):
                st.session_state['selected_cols'] = numeric_cols
            if st.button("Temizle"):
                st.session_state['selected_cols'] = []
        
        with col1:
            # Session state kontrolü (Seçimlerin hafızada kalması için)
            if 'selected_cols' not in st.session_state:
                st.session_state['selected_cols'] = numeric_cols
            
            selected_columns = st.multiselect(
                "Analize dahil edilecek sayısal sütunlar:",
                options=numeric_cols,
                default=st.session_state['selected_cols'],
                key='col_selector' # Unique key
            )
            
            st.caption(f"Şu an {len(selected_columns)} adet sütun seçildi.")

        # --- ANALİZ BUTONU ---
        analyze_btn = st.button("🚀 Analizi Başlat", type="primary", use_container_width=True)

        if analyze_btn:
            if len(selected_columns) < 2:
                st.error("Lütfen hesaplama yapabilmek için en az 2 sütun seçin.")
            else:
                df_selected = df_raw[selected_columns]
                
                with st.spinner('Optimizasyon hesaplanıyor...'):
                    history, target_scenario, max_scenario = optimize_scale(df_selected)
                    initial_alpha = history[0]['alpha']
                
                st.divider()
                
                # SONUÇLAR
                st.subheader("2. Sonuçlar")
                
                # Metrikler
                m_col1, m_col2, m_col3 = st.columns(3)
                m_col1.metric("Başlangıç Alpha", f"{initial_alpha:.4f}")
                m_col2.metric("Hedef Alpha", "0.7000")
                m_col3.metric("Max Ulaşılabilir Alpha", f"{max_scenario['alpha']:.4f}", 
                              delta=f"{max_scenario['alpha'] - initial_alpha:.4f}")

                # Yorumlama
                st.subheader("3. Öneriler")
                
                if initial_alpha >= 0.70:
                    st.success("✅ Mevcut veri seti zaten güvenilir (Alpha > 0.70). Madde çıkarmaya gerek yok.")
                
                elif target_scenario:
                    st.warning(f"⚠️ Hedefe (0.70) ulaşmak için {target_scenario['step']} madde çıkarılmalı.")
                    
                    # Çıkarılacaklar listesi
                    removed_items = [h['removed_item'] for h in history[1:target_scenario['step']+1]]
                    
                    st.info("**Sırasıyla çıkarılacak maddeler:**")
                    for i, item in enumerate(removed_items, 1):
                        st.markdown(f"{i}. **{item}** (Bunu çıkarınca Alpha yükseliyor)")
                        
                    st.success(f"Bu işlem sonunda ulaşılacak Alpha: **{target_scenario['alpha']:.4f}**")
                else:
                    st.error("❌ Ne kadar madde çıkarılırsa çıkarılsın 0.70 barajına ulaşılamıyor.")

                # Detay Tablosu
                with st.expander("Detaylı Adım Adım Tabloyu Gör"):
                    history_df = pd.DataFrame(history)[['step', 'removed_item', 'alpha']]
                    st.dataframe(history_df, use_container_width=True)

    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")
