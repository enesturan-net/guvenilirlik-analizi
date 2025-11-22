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
st.markdown("Excel dosyanızı yükleyin, listeden soruları seçin ve ölçeğinizi optimize edin.")

uploaded_file = st.file_uploader("Excel Dosyasını Yükle (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        df_raw = pd.read_excel(uploaded_file)
        
        # --- Sadece Sayısal Sütunları Al ---
        numeric_df = df_raw.select_dtypes(include=[np.number])
        text_df = df_raw.select_dtypes(exclude=[np.number])
        
        numeric_cols = numeric_df.columns.tolist()
        text_cols = text_df.columns.tolist()

        if not numeric_cols:
            st.error("Yüklenen dosyada sayısal sütun bulunamadı!")
            st.stop()

        st.success(f"Dosya Analiz Edildi: {len(numeric_cols)} adet sayısal sütun (soru) bulundu.")

        st.divider()

        # --- YENİ SÜTUN SEÇİM EKRANI (EXCEL TARZI LİSTE) ---
        st.subheader("1. Analiz Edilecek Soruları Seçin")
        st.info("Aşağıdaki listeden analize dahil etmek istediğiniz soruların yanındaki kutucuğu işaretleyin.")

        # Seçim için geçici bir DataFrame oluşturalım
        # Varsayılan olarak hepsi seçili gelsin (True)
        selection_data = pd.DataFrame({
            "Analize Dahil Et": [True] * len(numeric_cols),
            "Soru / Sütun Adı": numeric_cols
        })

        # Data Editor: Kullanıcının kutucukları işaretleyebileceği tablo
        edited_df = st.data_editor(
            selection_data,
            column_config={
                "Analize Dahil Et": st.column_config.CheckboxColumn(
                    "Seçim",
                    help="Analize dahil etmek için işaretleyin",
                    default=True,
                ),
                "Soru / Sütun Adı": st.column_config.TextColumn(
                    "Sütun Adı",
                    width="large", # Genişlik ayarı: Sütun adları tam okunsun
                    disabled=True   # Sütun adlarını değiştiremesin, sadece okusun
                )
            },
            hide_index=True, # Satır numaralarını gizle
            use_container_width=True, # Ekranın tamamını kapla
            height=300 # Yükseklik (kaydırma çubuğu çıkar çok sütun varsa)
        )

        # Tablodan seçili olanları filtrele
        selected_rows = edited_df[edited_df["Analize Dahil Et"] == True]
        selected_columns = selected_rows["Soru / Sütun Adı"].tolist()

        st.write(f"**Seçilen Sütun Sayısı:** {len(selected_columns)}")

        # --- ANALİZ BUTONU ---
        st.write("")
        analyze_btn = st.button("🚀 Analizi Başlat", type="primary", use_container_width=True)

        if analyze_btn:
            if len(selected_columns) < 2:
                st.error("Lütfen hesaplama yapabilmek için tablodan en az 2 sütun seçin.")
            else:
                df_selected = df_raw[selected_columns]
                
                with st.spinner('Optimizasyon hesaplanıyor...'):
                    history, target_scenario, max_scenario = optimize_scale(df_selected)
                    initial_alpha = history[0]['alpha']
                
                st.divider()
                
                # SONUÇLAR
                st.subheader("2. Sonuçlar")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Mevcut Alpha", f"{initial_alpha:.4f}")
                col2.metric("Hedef", "0.7000")
                col3.metric("Potansiyel Max Alpha", f"{max_scenario['alpha']:.4f}",
                            delta=f"{max_scenario['alpha'] - initial_alpha:.4f}")

                st.subheader("3. Öneriler")
                
                if initial_alpha >= 0.70:
                    st.success("✅ Mevcut veri seti zaten güvenilir (Alpha > 0.70).")
                
                elif target_scenario:
                    st.warning(f"⚠️ Hedefe (0.70) ulaşmak için **{target_scenario['step']}** adet en 'uyumsuz' madde çıkarılmalı.")
                    
                    removed_items = [h['removed_item'] for h in history[1:target_scenario['step']+1]]
                    
                    st.markdown("#### Çıkarılması Gerekenler:")
                    for i, item in enumerate(removed_items, 1):
                        st.markdown(f"- **{i}. Adım:** `{item}` çıkarılmalı.")
                        
                    st.success(f"Bu işlem sonunda Alpha: **{target_scenario['alpha']:.4f}** olacaktır.")
                else:
                    st.error("❌ 0.70 barajına ulaşılamıyor.")

                with st.expander("Detaylı Hesaplama Geçmişi"):
                    st.dataframe(pd.DataFrame(history)[['step', 'removed_item', 'alpha']], use_container_width=True)

    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")
