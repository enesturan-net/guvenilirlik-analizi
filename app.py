import streamlit as st
import pandas as pd
import numpy as np

# Sayfa Ayarları
st.set_page_config(page_title="Cronbach's Alpha Optimizer", layout="wide")

def calculate_cronbach_alpha(df):
    """
    Verilen DataFrame için Cronbach's Alpha değerini hesaplar.
    """
    # Tamamen boş olan satırları çıkar
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
st.markdown("Excel dosyanızı yükleyin, verilerinizi kontrol edin ve ölçeğinizi optimize edin.")

uploaded_file = st.file_uploader("Excel Dosyasını Yükle (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        df_raw = pd.read_excel(uploaded_file)
        
        # --- YENİ ÖZELLİK: İLK 5 SATIR ÖNİZLEME ---
        st.subheader("🔍 Veri Önizleme (İlk 5 Satır)")
        st.dataframe(df_raw.head(), use_container_width=True)
        
        st.divider()

        # --- AKILLI TÜR DÖNÜŞÜMÜ ---
        # Pandas bazen sayıları 'Object' olarak okur. Bunu düzeltelim.
        df_processed = df_raw.copy()
        numeric_cols = []
        text_cols = []

        for col in df_processed.columns:
            # Sütunu zorla sayıya çevirmeyi dene (Hatalı veriler NaN olur)
            converted_col = pd.to_numeric(df_processed[col], errors='coerce')
            
            # Eğer sütunun tamamı NaN olmadıysa (yani içinde sayılar varsa) bunu sayısal kabul et
            # Ve o sütunu temizlenmiş haliyle güncelle
            if converted_col.notna().sum() > 0:
                df_processed[col] = converted_col
                numeric_cols.append(col)
            else:
                text_cols.append(col)

        if not numeric_cols:
            st.error("Yüklenen dosyada sayısal veriye dönüştürülebilecek sütun bulunamadı!")
            st.stop()

        # --- EKRAN BÖLÜMÜ (SOL / SAĞ) ---
        col_left, col_right = st.columns([2, 1]) 
        
        with col_left:
            st.subheader("1. Analize Dahil Edilecek Sorular")
            st.info("Soruları seçin. (Listedeki veriler sayısal formata zorlanmıştır)")
            
            selection_data = pd.DataFrame({
                "Seç": [True] * len(numeric_cols),
                "Soru / Sütun Adı": numeric_cols
            })
            
            edited_df = st.data_editor(
                selection_data,
                column_config={
                    "Seç": st.column_config.CheckboxColumn("Dahil Et", width="small", default=True),
                    "Soru / Sütun Adı": st.column_config.TextColumn("Sütun Adı (Sayısal)", width="large", disabled=True)
                },
                hide_index=True,
                use_container_width=True,
                height=400
            )
            
            selected_rows = edited_df[edited_df["Seç"] == True]
            selected_columns = selected_rows["Soru / Sütun Adı"].tolist()
            
            st.caption(f"Seçilen Sütun: {len(selected_columns)}")

        with col_right:
            st.subheader("Metin Sütunları")
            if text_cols:
                st.warning("Bu sütunlar sayısal veri içermediği için ayrılmıştır.")
                text_display_df = pd.DataFrame({"Metin / Diğer": text_cols})
                st.dataframe(text_display_df, hide_index=True, use_container_width=True, height=400)
            else:
                st.info("Metin sütunu bulunamadı.")

        # --- ANALİZ BUTONU ---
        st.divider()
        action_col = st.container()
        
        if action_col.button("🚀 Analizi Başlat", type="primary", use_container_width=True):
            if len(selected_columns) < 2:
                st.error("En az 2 sütun seçmelisiniz.")
            else:
                # İşlenmiş (sayıya çevrilmiş) DataFrame'i kullanıyoruz
                df_selected = df_processed[selected_columns]
                
                with st.spinner('Optimizasyon hesaplanıyor...'):
                    history, target_scenario, max_scenario = optimize_scale(df_selected)
                    initial_alpha = history[0]['alpha']
                
                # SONUÇLAR
                st.subheader("2. Analiz Sonuçları")
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Mevcut Alpha", f"{initial_alpha:.4f}")
                m2.metric("Hedef", "0.7000")
                m3.metric("Max Potansiyel", f"{max_scenario['alpha']:.4f}", 
                          delta=f"{max_scenario['alpha'] - initial_alpha:.4f}")

                col_res1, col_res2 = st.columns(2)
                
                with col_res1:
                    st.markdown("### 🎯 0.70 Hedef Durumu")
                    if initial_alpha >= 0.70:
                        st.success("✅ Veri zaten 0.70 üzerinde.")
                    elif target_scenario:
                        st.warning(f"Hedef için **{target_scenario['step']}** madde çıkarılmalı.")
                        st.markdown("**Çıkarılacaklar:**")
                        removed_items = [h['removed_item'] for h in history[1:target_scenario['step']+1]]
                        for item in removed_items:
                            st.text(f"❌ {item}")
                        st.success(f"Yeni Alpha: **{target_scenario['alpha']:.4f}**")
                    else:
                        st.error("❌ 0.70 hedefine ulaşılamıyor.")

                with col_res2:
                    st.markdown("### 📈 Maksimum Alpha Durumu")
                    st.info(f"Max Alpha ({max_scenario['alpha']:.4f}) için **{max_scenario['step']}** madde çıkarılmalı.")
                    with st.expander("Detaylı Liste"):
                        all_removed = [h['removed_item'] for h in history[1:max_scenario['step']+1]]
                        st.write(all_removed)

                st.divider()
                with st.expander("🔍 Hesaplama Geçmişi Tablosu"):
                    st.dataframe(pd.DataFrame(history)[['step', 'removed_item', 'alpha']], use_container_width=True)

    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")
