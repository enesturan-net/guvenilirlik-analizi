import streamlit as st
import pandas as pd
import numpy as np

# Sayfa Ayarları
st.set_page_config(page_title="Cronbach's Alpha Optimizer", layout="wide")

def calculate_cronbach_alpha(df):
    """
    Verilen DataFrame için Cronbach's Alpha değerini hesaplar.
    Formül: (N / (N-1)) * (1 - (Toplam(Varyans_i) / Varyans_Toplam))
    """
    # Eksik verileri (NaN) satır bazlı temizleyelim
    df_clean = df.dropna()
    
    # Sütun sayısı (Item count)
    item_count = df_clean.shape[1]
    
    if item_count < 2:
        return 0.0
    
    # Varyans hesaplamaları (ddof=1 örneklem varyansı için)
    item_variances = df_clean.var(axis=0, ddof=1)
    total_score_variance = df_clean.sum(axis=1).var(ddof=1)
    
    if total_score_variance == 0:
        return 0.0
    
    alpha = (item_count / (item_count - 1)) * (1 - (item_variances.sum() / total_score_variance))
    return alpha

def optimize_scale(df, target=0.70):
    """
    Adım adım en kötü maddeyi çıkararak 0.70 hedefini ve maximum alpha'yı arar.
    """
    history = []
    current_cols = list(df.columns)
    
    # Başlangıç durumu
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

    # Eğer zaten hedef üzerindeysek
    if initial_alpha >= target:
        target_reached_scenario = history[0]

    # İteratif çıkarma döngüsü (En az 2 madde kalana kadar)
    step = 1
    while len(current_cols) > 2:
        item_scores = {}
        
        # Hangi madde çıkarsa Alpha ne oluyor? (Alpha if item deleted)
        for col in current_cols:
            temp_cols = [c for c in current_cols if c != col]
            score = calculate_cronbach_alpha(df[temp_cols])
            item_scores[col] = score
        
        # En yüksek Alpha'yı sağlayan (yani çıkarılması en mantıklı) maddeyi bul
        best_item_to_remove = max(item_scores, key=item_scores.get)
        new_alpha = item_scores[best_item_to_remove]
        
        # Listeden çıkar
        current_cols.remove(best_item_to_remove)
        
        scenario = {
            "step": step,
            "removed_item": best_item_to_remove,
            "alpha": new_alpha,
            "remaining_items": current_cols.copy()
        }
        history.append(scenario)
        
        # Max Alpha takibi
        if new_alpha > best_alpha:
            best_alpha = new_alpha
            max_alpha_scenario = scenario
            
        # Target (0.70) takibi (İlk kez geçtiği anı yakala)
        if target_reached_scenario is None and new_alpha >= target:
            target_reached_scenario = scenario
            
        step += 1
        
    return history, target_reached_scenario, max_alpha_scenario

# --- ARAYÜZ (UI) ---

st.title("📊 Cronbach's Alpha Optimizer")
st.markdown("""
Bu araç, ölçek güvenilirliğini (Cronbach's Alpha) hesaplar ve 
eğer değer **0.70**'in altındaysa, hangi maddelerin çıkarılması gerektiğini önerir.
""")

uploaded_file = st.file_uploader("Excel Dosyasını Yükle (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        df_raw = pd.read_excel(uploaded_file)
        st.success("Dosya başarıyla yüklendi.")
        
        # Sadece sayısal sütunları al
        numeric_cols = df_raw.select_dtypes(include=[np.number]).columns.tolist()
        
        st.subheader("1. Analize Dahil Edilecek Sütunları Seçin")
        selected_columns = st.multiselect(
            "Maddeleri (Soruları) Seçin:", 
            numeric_cols, 
            default=numeric_cols
        )
        
        if len(selected_columns) < 2:
            st.warning("Lütfen hesaplama için en az 2 sütun seçin.")
        else:
            if st.button("Analizi Başlat"):
                df_selected = df_raw[selected_columns]
                
                # Hesaplamaları Yap
                history, target_scenario, max_scenario = optimize_scale(df_selected)
                initial_alpha = history[0]['alpha']
                
                st.divider()
                
                # 1. MEVCUT DURUM
                st.subheader("2. Mevcut Durum")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Seçili Sütun Sayısı", len(selected_columns))
                with col2:
                    delta_color = "normal"
                    if initial_alpha >= 0.70:
                        delta_color = "normal"  # Yeşil olması için normal metric delta kullanabiliriz ama basit tutalım.
                        st.success(f"**Cronbach's Alpha: {initial_alpha:.4f}** (Güvenilir)")
                    else:
                        st.error(f"**Cronbach's Alpha: {initial_alpha:.4f}** (Düşük Güvenilirlik)")

                # 2. HEDEF (0.70) ANALİZİ
                st.divider()
                st.subheader("3. Optimizasyon Önerileri")
                
                if initial_alpha >= 0.70:
                    st.info("Mevcut veri seti zaten 0.70 barajının üzerinde. Madde çıkarmaya gerek yok.")
                else:
                    if target_scenario:
                        st.markdown(f"### 🎯 Hedefe Ulaşmak İçin (Alpha > 0.70)")
                        st.write(f"0.70 barajını geçmek için en az **{target_scenario['step']}** adet veriyi (sütunu) çıkarmanız gerekiyor.")
                        
                        # Çıkarılması gerekenleri bul
                        removed_so_far = []
                        for h in history[1:target_scenario['step']+1]:
                            removed_so_far.append(h['removed_item'])
                            
                        st.warning(f"**Sırasıyla çıkarılması gereken maddeler:** {', '.join(removed_so_far)}")
                        st.success(f"**Yeni Cronbach's Alpha Değeri:** {target_scenario['alpha']:.4f}")
                    else:
                        st.error("Ne kadar madde çıkarılırsa çıkarılsın 0.70 barajına ulaşılamıyor. Veri seti uyumsuz olabilir.")

                # 3. MAKSİMUM POTANSİYEL
                st.divider()
                st.subheader("4. Maksimum Potansiyel")
                st.markdown(f"Bu veri seti ile ulaşabileceğiniz **Maksimum Cronbach's Alpha: {max_scenario['alpha']:.4f}**")
                
                if max_scenario['step'] > 0:
                    all_removed_for_max = []
                    for h in history[1:max_scenario['step']+1]:
                        all_removed_for_max.append(h['removed_item'])
                    
                    with st.expander("Maksimum değere ulaşmak için çıkarılan maddeleri gör"):
                         st.write(f"Çıkarılanlar: {', '.join(all_removed_for_max)}")
                         st.write(f"Kalan Maddeler: {', '.join(max_scenario['remaining_items'])}")

                # 4. DETAYLI TABLO
                st.divider()
                with st.expander("Detaylı Hesaplama Geçmişini Gör"):
                    st.write("Algoritmanın her adımda çıkardığı madde ve elde edilen Alpha değeri:")
                    history_df = pd.DataFrame(history)
                    history_df = history_df[['step', 'removed_item', 'alpha']]
                    st.dataframe(history_df)

    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")