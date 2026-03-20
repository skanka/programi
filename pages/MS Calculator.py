import streamlit as st
import pandas as pd
import plotly.express as px
import re

# ==========================================
# 1. КОНСТАНТИ И ТОЧНИ МАСИ
# ==========================================
MASS_C = 12.000000
MASS_H = 1.007825
MASS_O = 15.994915
MASS_PROTON = 1.007276   
MASS_ELECTRON = 0.0005485 

IONIZATION_MODES = {
    "[M+H]+": MASS_PROTON,                
    "[M+Na]+": 22.989222 - MASS_ELECTRON, 
    "[M-H]-": -MASS_PROTON,               
    "Fragment+": -MASS_ELECTRON           
}

# Речник с имена на често срещани отцепвания, за по-лесно четене
KNOWN_LOSS_NAMES = {
    "H2O": "Вода",
    "CO": "Въглероден оксид",
    "CO2": "Въглероден диоксид",
    "CH3": "Метилов радикал",
    "CH4": "Метан",
    "OH": "Хидроксилна група",
    "C2H4": "Етилен",
    "C2H2O": "Кетен (Ацетат)",
    "CH4O": "Метанол",
    "CH2O2": "Мравчена киселина",
    "C3H4O": "Акролеин / Пръстен",
    "C3H6": "Пропилен"
}

# ==========================================
# 2. ПОМОЩНИ ФУНКЦИИ И АЛГОРИТМИ
# ==========================================
def get_dbe_hint(dbe):
    """Дава структурна подсказка базирана на DBE."""
    if dbe == 0: return "Алифатна (наситена) верига."
    elif dbe == 1: return "1 двойна връзка (C=C или C=O) ИЛИ 1 пръстен."
    elif dbe == 2: return "2 двойни връзки, 2 пръстена ИЛИ 1 пръстен + 1 двойна връзка."
    elif dbe >= 4:
        hint = "Възможен АРОМАТЕН ПРЪСТЕН (мин. DBE 4: 1 пръстен + 3 двойни връзки)."
        if dbe > 4: hint += f" + още {dbe-4} степени на ненаситеност."
        return hint
    return f"{dbe} пръстена/двойни връзки."

def calculate_formula_mass(formula_str):
    """Смята точната маса на въведена ръчно формула"""
    c_match = re.search(r'C(\d+)', formula_str)
    h_match = re.search(r'H(\d+)', formula_str)
    o_match = re.search(r'O(\d+)', formula_str)
    
    c_count = int(c_match.group(1)) if c_match else (1 if 'C' in formula_str and not re.search(r'C\d+', formula_str) else 0)
    h_count = int(h_match.group(1)) if h_match else (1 if 'H' in formula_str and not re.search(r'H\d+', formula_str) else 0)
    o_count = int(o_match.group(1)) if o_match else (1 if 'O' in formula_str and not re.search(r'O\d+', formula_str) else 0)
    return (c_count * MASS_C) + (h_count * MASS_H) + (o_count * MASS_O)

def get_formulas(target_mz, tolerance_ppm, mode="[M+H]+", max_c=30, max_h=60, max_o=10):
    """Изчислява възможни формули за даден йон."""
    results = []
    adduct_mass = IONIZATION_MODES.get(mode, MASS_PROTON)
    target_neutral_mass = target_mz - adduct_mass

    for c in range(1, max_c + 1):
        for o in range(0, max_o + 1):
            for h in range(1, max_h + 1):
                calc_neutral_mass = (c * MASS_C) + (h * MASS_H) + (o * MASS_O)
                calc_mz = calc_neutral_mass + adduct_mass
                error_ppm = (abs(calc_mz - target_mz) / target_mz) * 1_000_000
                
                if error_ppm <= tolerance_ppm:
                    dbe = c + 1 - (h / 2)
                    if dbe >= 0 and dbe.is_integer():
                        neutral_formula = f"C{c}H{h}" + (f"O{o}" if o > 0 else "")
                        ion_formula = f"C{c}H{h+1}" + (f"O{o}+" if o > 0 else "+") if mode == "[M+H]+" else (f"C{c}H{h}" + (f"O{o}+" if o > 0 else "+") if mode == "Fragment+" else neutral_formula + " + адукт")
                            
                        results.append({
                            "Целево m/z": target_mz,
                            "Йонна Формула": ion_formula,
                            "Неутрална Формула": neutral_formula,
                            "Грешка (ppm)": round(error_ppm, 2),
                            "DBE": int(dbe),
                            "Структурна подсказка": get_dbe_hint(int(dbe))
                        })
    return results

def calculate_loss_formula(mass_diff, tolerance_da):
    """Изчислява брутната формула на загубена маса (разлика между два фрагмента)."""
    best_formula = "Неизвестна"
    best_error = float('inf')
    
    # Търсим възможни комбинации до 15 C, 30 H, 8 O за загуби
    for c in range(0, 16):
        for o in range(0, 9):
            for h in range(0, 31):
                if c == 0 and h == 0 and o == 0: continue
                
                calc_mass = (c * MASS_C) + (h * MASS_H) + (o * MASS_O)
                error = abs(calc_mass - mass_diff)
                
                if error <= tolerance_da:
                    if error < best_error:
                        best_error = error
                        parts = []
                        if c > 0: parts.append(f"C{c}" if c > 1 else "C")
                        if h > 0: parts.append(f"H{h}" if h > 1 else "H")
                        if o > 0: parts.append(f"O{o}" if o > 1 else "O")
                        best_formula = "".join(parts)
                        
    name = KNOWN_LOSS_NAMES.get(best_formula, "")
    return best_formula, best_error, name

def find_all_losses(mzs, tolerance_da=0.015, max_loss=150):
    """Намира всички загуби между всички възможни двойки пикове."""
    losses_results = []
    mzs = sorted(mzs, reverse=True) # От най-големия към най-малкия
    
    for i in range(len(mzs)):
        for j in range(i + 1, len(mzs)):
            mz1 = mzs[i]
            mz2 = mzs[j]
            mass_diff = mz1 - mz2
            
            # Изчисляваме формули само за разлики до зададения лимит (напр. 150 Da)
            if mass_diff <= max_loss:
                formula, err, name = calculate_loss_formula(mass_diff, tolerance_da)
                
                desc = f"- {formula}" if formula != "Неизвестна" else "Сложна/Неизвестна загуба"
                if name: desc += f" ({name})"
                
                losses_results.append({
                    "От йон (m/z)": round(mz1, 4),
                    "Към фрагмент (m/z)": round(mz2, 4),
                    "Загуба (\u0394 m/z)": round(mass_diff, 4),
                    "Формула на загубата": formula,
                    "Описание": desc,
                    "Грешка (Da)": round(err, 4) if err != float('inf') else "-"
                })
    return losses_results

# ==========================================
# 3. STREAMLIT ИНТЕРФЕЙС
# ==========================================
st.set_page_config(page_title="Advanced HRMS Analyzer", layout="wide")

# --- СТРАНИЧНА ЛЕНТА: РЪЧЕН КАЛКУЛАТОР И НАСТРОЙКИ ---
with st.sidebar:
    st.header("🧮 Ръчен калкулатор")
    st.info("Бързи сметки за проверка на хипотези.")
    
    calc_formula = st.text_input("Въведи формула (напр. C15H24O5):", value="")
    if calc_formula:
        try:
            em = calculate_formula_mass(calc_formula)
            st.success(f"Точна маса: **{em:.5f} Da**")
        except:
            st.error("Невалиден формат.")
            
    st.divider()
    st.markdown("**Разлика между две маси:**")
    m1 = st.number_input("Маса 1 (m/z):", value=0.0, format="%.4f")
    m2 = st.number_input("Маса 2 (m/z):", value=0.0, format="%.4f")
    if m1 > 0 and m2 > 0:
        diff = abs(m1 - m2)
        st.info(f"Разлика (\u0394 m/z): **{diff:.4f} Da**")
        # Автоматично изчислява какво е това!
        f, e, n = calculate_loss_formula(diff, 0.015)
        if f != "Неизвестна":
            st.success(f"Това най-вероятно е отцепване на: **{f}** {f'({n})' if n else ''} (Грешка: {e:.4f} Da)")

    st.divider()
    st.header("⚙️ Настройки за анализа")
    tolerance_ppm = st.number_input("Толеранс формули (ppm)", min_value=0.1, max_value=50.0, value=5.0, step=0.5)
    tolerance_loss = st.number_input("Толеранс загуби (Da)", min_value=0.001, max_value=0.1, value=0.015, step=0.001)
    max_loss_da = st.number_input("Макс. маса на загуба (Da)", min_value=50, max_value=500, value=150, step=10, help="Ще смята формули за отцепвания до тази маса.")
    ionization_mode = st.selectbox("Йонизация (за Прекурсора)", list(IONIZATION_MODES.keys()), index=0)
    min_abundance = st.slider("Мин. Rel. Abundance (%) за фрагменти", 0.0, 100.0, 2.0, step=0.5)

# --- ГЛАВЕН ПАНЕЛ ---
st.title("🔬 Пълен MS/MS Анализатор на Фрагментации")
st.markdown("Интерактивен софтуер за пресмятане на елементарен състав, DBE и интелигентно картографиране на отцепванията.")

uploaded_file = st.file_uploader("Качете експортнат файл със спектър (TXT / TSV / CSV)", type=['txt', 'tsv', 'csv'])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, sep='\t', engine='python', on_bad_lines='skip')
        df.columns = df.columns.str.strip()
        
        if 'm/z' in df.columns and 'Rel. Abundance' in df.columns:
            df['m/z'] = pd.to_numeric(df['m/z'], errors='coerce')
            df['Rel. Abundance'] = pd.to_numeric(df['Rel. Abundance'], errors='coerce')
            df = df.dropna(subset=['m/z', 'Rel. Abundance'])
        else:
            st.error("Файлът трябва да съдържа колони 'm/z' и 'Rel. Abundance'.")
            st.stop()

        df_filtered = df[df['Rel. Abundance'] >= min_abundance].copy()
        
        # --- ВИЗУАЛИЗАЦИЯ НА СПЕКТЪРА ---
        st.subheader("📊 Визуализация на Масспектъра")
        fig = px.bar(df_filtered, x='m/z', y='Rel. Abundance', 
                     hover_data=['m/z', 'Rel. Abundance'],
                     labels={'Rel. Abundance': 'Относителен интензитет (%)', 'm/z': 'm/z'},
                     title=f"MS Спектър (Филтриран над {min_abundance}%)")
        fig.update_traces(marker_color='blue', width=1.5)
        fig.update_layout(xaxis_title="m/z", yaxis_title="Rel. Abundance (%)", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

        suggested_precursor = float(df_filtered['m/z'].max())
        col1, col2 = st.columns(2)
        with col1:
            precursor_mz = st.number_input("Избран Прекурсорен йон (m/z):", value=suggested_precursor, format="%.4f")
        with col2:
            st.info(f"Ще анализираме {len(df_filtered)} значими фрагмента.")

        if st.button("🚀 Анализирай всичко", type="primary"):
            st.divider()
            
            tab1, tab2, tab3 = st.tabs(["🟢 Прекурсор & Формули", "🧩 Фрагменти", "📉 Карта на Загубите (Отцепвания)"])
            
            with tab1:
                st.subheader("Резултати за Прекурсорния йон")
                precursor_results = get_formulas(precursor_mz, tolerance_ppm, mode=ionization_mode)
                if precursor_results:
                    st.dataframe(pd.DataFrame(precursor_results), use_container_width=True)
                else:
                    st.warning("Няма намерени формули.")

            with tab2:
                st.subheader("Елементарен състав на Фрагментите")
                fragment_mzs = df_filtered[df_filtered['m/z'] != precursor_mz]['m/z'].tolist()
                all_fragment_results = []
                for frag_mz in fragment_mzs:
                    frag_results = get_formulas(frag_mz, tolerance_ppm, mode="Fragment+")
                    all_fragment_results.extend(frag_results)
                    
                if all_fragment_results:
                    frag_df = pd.DataFrame(all_fragment_results)
                    st.dataframe(frag_df, use_container_width=True)
                else:
                    st.warning("Няма намерени формули.")

            with tab3:
                st.subheader("Изчислени отцепвания между всички пикове")
                st.markdown(f"Програмата изчислява брутната формула на **ВСЯКА** загуба на маса до {max_loss_da} Da между всеки два пика в спектъра.")
                
                all_mzs_for_loss = [precursor_mz] + fragment_mzs
                loss_results = find_all_losses(all_mzs_for_loss, tolerance_da=tolerance_loss, max_loss=max_loss_da)
                
                if loss_results:
                    loss_df = pd.DataFrame(loss_results)
                    loss_df = loss_df.sort_values(by="Загуба (\u0394 m/z)")
                    
                    # Оцветяване: Зелено за разпознати формули, Бяло за неизвестни
                    def highlight_formulas(row):
                        if row['Формула на загубата'] != "Неизвестна":
                            return ['background-color: #e6f9ec'] * len(row) 
                        return [''] * len(row)

                    st.dataframe(loss_df.style.apply(highlight_formulas, axis=1), use_container_width=True)
                else:
                    st.info("Не са намерени загуби в рамките на този толеранс.")

    except Exception as e:
        st.error(f"Грешка: {e}")