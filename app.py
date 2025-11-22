import streamlit as st
import pandas as pd
import numpy as np

# Sayfa Ayarları: Geniş ekran kullanımı
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
    """
    Adım adım optimizasyon algoritması.
    """
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
st.markdown("Excel dosyanızı yükleyin, sol taraftan soruları seçin ve sağ taraftan metin sütunlarını kontrol edin.")

uploaded_file = st.file_uploader("Excel Dosyasını Yükle (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        df_raw = pd.read_excel(uploaded_file)
        
        # --- Veriyi Türlerine Göre Ayır ---
        numeric_df = df_raw.select_dtypes(include=[np.number])
        text_df = df_raw.select_dtypes(exclude=[np.number])
        
        numeric_cols = numeric_df.columns.tolist()
        text_cols = text_df.columns.tolist()

        if not numeric_cols:
            st.error("Yüklenen dosyada sayısal sütun bulunamadı!")
            st.stop()

        st.divider()

        # --- EKRANI İKİYE BÖL (SOL: SAYISAL, SAĞ: METİN) ---
        col_left, col_right = st.columns([2, 1]) # Sol taraf biraz daha geniş olsun
        
        # --- SOL TARAFI AYARLA (SEÇİLEBİLİR ALAN) ---
        with col_left:
            st.subheader("1. Analize Dahil Edilecek Sorular")
            st.info("Analiz etmek istediğiniz soruları buradan seçin.")
            
            # Seçim verisi hazırlığı
            selection_data = pd.DataFrame({
                "Seç": [True] * len(numeric_cols),
                "Soru / Sütun Adı": numeric_cols
            })
            
            # Data Editor (Checkbox'lı)
            edited_df = st.data_editor(
                selection_data,
                column_config={
                    "Seç": st.column_config.CheckboxColumn(
                        "Dahil Et",
                        width="small",
                        default=True,
                    ),
                    "Soru / Sütun Adı": st.column_config.TextColumn(
                        "Sütun Adı (Sayısal)",
                        width="large",
                        disabled=True
                    )
                },
                hide_index=True,
                use_container_width=True,
                height=400 # Sabit yükseklik, scroll bar çıkar gerekirse
            )
            
            # Seçilenleri filtrele
            selected_rows = edited_df[edited_df["Seç"] == True]
            selected_columns = selected_rows["Soru / Sütun Adı"].tolist()
            
            st.caption(f"Toplam {len(numeric_cols)} sayısal sütundan {len(selected_columns)} tanesi seçildi.")

        # --- SAĞ TARAFI AYARLA (SADECE GÖRÜNTÜLEME) ---
        with col_right:
            st.subheader("Bilgi Sütunları")
            if text_cols:
                st.warning("Bu sütunlar metin içerdiği için analize dahil edilmez, sadece bilgi amaçlıdır.")
                
                # Sadece görüntüleme amaçlı DataFrame
                text_display_df = pd.DataFrame({"Metin Sütunları": text_cols})
                
                st.dataframe(
                    text_display_df,
                    hide_index=True,
                    use_container_width=True,
                    height=400 # Sol tarafla eşit boyda olsun
                )
            else:
                st.info("Bu dosyada hiç metin sütunu bulunamadı.")

        # --- ANALİZ BUTONU VE SONUÇLAR ---
        st.divider()
        
        # Butonu ortalamak veya genişletmek için container kullanımı
        action_col = st.container()
        
        if action_col.button("🚀 Analizi Başlat", type="primary", use_container_width=True):
            if len(selected_columns) < 2:
                st.error("Lütfen sol taraftan en az 2 sütun seçin.")
            else:
                df_selected = df_raw[selected_columns]
                
                with st.spinner('Optimizasyon hesaplanıyor...'):
                    history, target_scenario, max_scenario = optimize_scale(df_selected)
                    initial_alpha = history[0]['alpha']
                
                # SONUÇ ALANI
                st.subheader("2. Analiz Sonuçları")
                
                # Metrikler yan yana
                m1, m2, m3 = st.columns(3)
                m1.metric("Mevcut Cronbach's Alpha", f"{initial_alpha:.4f}")
                m2.metric("Hedef Değer", "0.7000")
                m3.metric("Ulaşılabilir Maksimum", f"{max_scenario['alpha']:.4f}", 
                          delta=f"{max_scenario['alpha'] - initial_alpha:.4f}")

                st.write("") # Boşluk

                # Senaryolar
                col_res1, col_res2 = st.columns(2)
                
                with col_res1:
                    st.markdown("### 🎯 0.70 Hedef Analizi")
                    if initial_alpha >= 0.70:
                        st.success("✅ Veri seti zaten güvenilir. Madde çıkarmaya gerek yok.")
                    elif target_scenario:
                        st.warning(f"0.70'i geçmek için **{target_scenario['step']}** madde çıkarılmalı.")
                        st.markdown("**Sırasıyla Çıkarılacaklar:**")
                        
                        removed_items = [h['removed_item'] for h in history[1:target_scenario['step']+1]]
                        for item in removed_items:
                            st.text(f"❌ {item}")
                        
                        st.success(f"Yeni Alpha: **{target_scenario['alpha']:.4f}**")
                    else:
                        st.error("❌ Veri seti ne yapılırsa yapılsın 0.70 barajını geçemiyor.")

                with col_res2:
                    st.markdown("### 📈 Maksimum Performans Analizi")
                    st.info(f"Maksimum değere ({max_scenario['alpha']:.4f}) ulaşmak için toplam **{max_scenario['step']}** madde çıkarılmalı.")
                    
                    with st.expander("Maksimum için çıkarılan tüm listeyi gör"):
                        all_removed = [h['removed_item'] for h in history[1:max_scenario['step']+1]]
                        st.write(all_removed)

                # Detay Tablosu
                st.divider()
                with st.expander("🔍 Detaylı Adım Adım Hesaplama Tablosu"):
                    st.dataframe(pd.DataFrame(history)[['step', 'removed_item', 'alpha']], use_container_width=True)

    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")
