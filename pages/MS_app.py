import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os, tempfile, subprocess, io

try:
    from rdkit import Chem
    RDKIT_READY = True
except ImportError:
    RDKIT_READY = False

# --- ПЪТЯТ ДО FIORA ---
FIORA_SCRIPT = r"C:\Users\skank\AppData\Local\Programs\Python\Python313\Scripts\fiora-predict"

def check_fiora():
    return os.path.exists(FIORA_SCRIPT)

def draw_mirror_plot(exp_df, sim_df, ion_mode):
    fig = go.Figure()
    
    for _, row in exp_df.iterrows():
        fig.add_trace(go.Scatter(x=[row['m/z'], row['m/z']], y=[0, row['Rel_Int']], mode='lines', line=dict(color='royalblue', width=2), showlegend=False))
    
    if not sim_df.empty:
        max_sim = sim_df['Intensity'].max()
        for _, row in sim_df.iterrows():
            rel_sim = -(row['Intensity'] / max_sim) * 100
            fig.add_trace(go.Scatter(x=[row['m/z'], row['m/z']], y=[0, rel_sim], mode='lines', line=dict(color='firebrick', width=2), showlegend=False))
    
    fig.update_layout(title=f"Mirror Plot: Експеримент vs FIORA ({ion_mode} Mode)", xaxis_title="m/z", yaxis_title="Относителен интензитет (%)", template="plotly_white", height=500)
    fig.add_hline(y=0, line_color="black")
    return fig

st.set_page_config(page_title="FIORA Advanced Pro", layout="wide")
st.title("🔬 FIORA: Пълен Мас-анализ (Mnova Ready)")

if not check_fiora():
    st.error(f"❌ Проблем с пътя: {FIORA_SCRIPT}")
else:
    st.sidebar.success("✅ FIORA е готова!")

st.sidebar.header("1️⃣ Структура (ChemDraw)")
mol_file = st.sidebar.file_uploader("Качи .mol файл (опционално):", type=["mol"])

default_smiles = "Oc1cc(O)c2c(c1)oc(c(O)c2=O)-c3ccc(O)c(O)c3" 
if mol_file and RDKIT_READY:
    mol_text = mol_file.getvalue().decode("utf-8")
    mol = Chem.MolFromMolBlock(mol_text)
    if mol: default_smiles = Chem.MolToSmiles(mol)

smiles = st.sidebar.text_input("SMILES за симулация:", default_smiles)

st.sidebar.header("2️⃣ Спектрални Данни")
uploaded_file = st.sidebar.file_uploader("Качи спектър (Excel, CSV, TXT):", type=["xlsx", "xls", "csv", "txt"])
noise_threshold = st.sidebar.slider("Скрий пикове под (% интензитет):", 0.0, 10.0, 0.5, step=0.1)

st.sidebar.header("3️⃣ Настройки на Симулацията")
ion_mode_ui = st.sidebar.radio("Метод на йонизация:", ["Положителна (+)", "Отрицателна (-)"])
ion_mode = "POSITIVE" if "Положителна" in ion_mode_ui else "NEGATIVE"
adduct = "[M+H]+" if "Положителна" in ion_mode_ui else "[M-H]-"

ce = st.sidebar.slider("Collision Energy (CE):", 10, 100, 30)
ppm_tolerance = st.sidebar.number_input("Толеранс за съвпадение (ppm):", min_value=1.0, max_value=50.0, value=15.0)

# --- ОСНОВНА ЛОГИКА ---
if uploaded_file and check_fiora():
    try:
        if uploaded_file.name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(uploaded_file)
        else:
            content = uploaded_file.getvalue().decode('utf-8')
            def safe_read(sep_char):
                try:
                    return pd.read_csv(io.StringIO(content), sep=sep_char, engine='python', on_bad_lines='skip')
                except TypeError:
                    return pd.read_csv(io.StringIO(content), sep=sep_char, engine='python', error_bad_lines=False)

            if '\t' in content: df = safe_read('\t')
            elif ';' in content: df = safe_read(';')
            else: df = safe_read(',')
        
        # 💡 ИНТЕЛИГЕНТНО ИЗВЛИЧАНЕ НА КОЛОНИТЕ (Решава проблема с дублиращите се имена)
        # 1. Почистваме имената от интервали
        df.columns = [str(col).strip() for col in df.columns]
        
        # 2. Търсим точно една колона за m/z
        mz_col = next((c for c in df.columns if c.lower() in ['m/z', 'mass', 'mz']), None)
        
        # 3. Търсим точно една колона за Интензитет (приоритет: Intensity > Abundance > Height)
        int_col = None
        for name in ['intensity', 'abundance', 'height', 'rel. abundance']:
            for c in df.columns:
                if c.lower() == name:
                    int_col = c
                    break
            if int_col: break
            
        if not mz_col or not int_col:
            st.error(f"Грешка: Не мога да намеря подходящи колони за маса и интензитет. Намерени са: {list(df.columns)}")
        else:
            # Създаваме нова чиста таблица САМО с тези две колони
            clean_data = pd.DataFrame()
            
            # Вече сме сигурни, че подаваме само 1D Array (Series)
            clean_data['m/z'] = pd.to_numeric(df[mz_col], errors='coerce')
            clean_data['Intensity'] = pd.to_numeric(df[int_col], errors='coerce')
            
            # Махаме редовете с текст (ако Mnova е сложила букви при числата)
            clean_data = clean_data.dropna(subset=['m/z', 'Intensity'])
            
            clean_data['Rel_Int'] = (clean_data['Intensity'] / clean_data['Intensity'].max()) * 100
            final_df = clean_data[clean_data['Rel_Int'] >= noise_threshold] 
            
            auto_mz = float(final_df['m/z'].max()) if not final_df.empty else 100.0
            
            st.subheader("📊 Твоят експериментален спектър")
            
            col_mz, col_info = st.columns([1, 2])
            with col_mz:
                target_mz = st.number_input("🎯 Въведи точния Прекурсорен йон (m/z):", value=auto_mz, format="%.4f")
            with col_info:
                st.info(f"Адукт: **{adduct}**. Този m/z ще бъде подаден на FIORA за фрагментиране.")

            fig_exp = go.Figure()
            for _, row in final_df.iterrows():
                fig_exp.add_trace(go.Scatter(x=[row['m/z'], row['m/z']], y=[0, row['Rel_Int']], mode='lines', line=dict(color='royalblue', width=2), showlegend=False))
            fig_exp.update_layout(xaxis_title="m/z", yaxis_title="Относителен интензитет (%)", template="plotly_white", height=300)
            st.plotly_chart(fig_exp, use_container_width=True)

            st.write("---")

            if st.button("🚀 СТАРТИРАЙ FIORA СИМУЛАЦИЯ"):
                with st.spinner(f"FIORA симулира фрагментация на m/z {target_mz:.4f}..."):
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
                        tmp.write("Name,SMILES,precursor_mz,CE,Instrument_type,Ion_mode,Precursor_type,Adduct\n")
                        tmp.write(f"Sample,{smiles},{target_mz},{ce},Orbitrap,{ion_mode},{adduct},{adduct}\n")
                        in_f = tmp.name
                    
                    out_f = in_f.replace('.csv', '.mgf')
                    fiora_cmd = f'python "{FIORA_SCRIPT}" -i "{in_f}" -o "{out_f}"'
                    
                    try:
                        subprocess.run(fiora_cmd, shell=True, check=True, capture_output=True, text=True)
                        
                        if os.path.exists(out_f):
                            mzs, ints = [], []
                            with open(out_f, 'r') as f:
                                for line in f:
                                    if line.strip() and line[0].isdigit():
                                        parts = line.split()
                                        mzs.append(float(parts[0]))
                                        ints.append(float(parts[1]))
                            
                            sim_df = pd.DataFrame({'m/z': mzs, 'Intensity': ints})
                            
                            if not sim_df.empty:
                                sim_df['Rel_Int'] = (sim_df['Intensity'] / sim_df['Intensity'].max()) * 100
                                
                                st.subheader("🪞 Сравнение: Твоят спектър срещу симулацията")
                                st.plotly_chart(draw_mirror_plot(final_df, sim_df, ion_mode), use_container_width=True)
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.subheader("📋 Всички фрагменти (FIORA)")
                                    fiora_display = sim_df[['m/z', 'Rel_Int']].copy()
                                    fiora_display.columns = ['FIORA m/z', 'Интензитет (%)']
                                    st.dataframe(fiora_display.sort_values(by='Интензитет (%)', ascending=False), height=350)
                                
                                with col2:
                                    st.subheader(f"🎯 Потвърдени съвпадения (≤ {ppm_tolerance} ppm)")
                                    matches = []
                                    for _, e_row in final_df.iterrows():
                                        e_mz = e_row['m/z']
                                        closest_idx = (sim_df['m/z'] - e_mz).abs().idxmin()
                                        s_mz = sim_df.loc[closest_idx, 'm/z']
                                        ppm_error = abs(e_mz - s_mz) / s_mz * 1e6
                                        
                                        if ppm_error <= ppm_tolerance:
                                            matches.append({
                                                "Експ. m/z": round(e_mz, 4),
                                                "FIORA m/z": round(s_mz, 4),
                                                "Грешка (ppm)": round(ppm_error, 2),
                                                "Експ. Инт (%)": round(e_row['Rel_Int'], 1)
                                            })
                                    
                                    if matches:
                                        st.dataframe(pd.DataFrame(matches).sort_values(by='Грешка (ppm)'), height=350)
                                    else:
                                        st.warning("Няма съвпадения в рамките на този толеранс.")
                            else:
                                st.warning("FIORA не генерира фрагменти за тази молекула/настройки.")
                    except Exception as e:
                        st.error(f"Грешка при изпълнението: {e}")
    except Exception as e:
        st.error(f"Грешка при четене на файла: {e}")