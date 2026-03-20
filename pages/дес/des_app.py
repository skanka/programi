import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from rdkit import Chem
from rdkit.Chem import Draw
from rdkit.Chem import rdMolDescriptors

def get_molecule_properties(smiles):
    """Изчислява свойствата на молекулата по зададен SMILES."""
    mol = Chem.MolFromSmiles(smiles)
    if mol:
        mol = Chem.AddHs(mol) # Добавяме водороди за по-точно броене
        mw = rdMolDescriptors.CalcExactMolWt(mol)
        hbd = rdMolDescriptors.CalcNumHBD(mol)
        hba = rdMolDescriptors.CalcNumHBA(mol)
        return mol, mw, hbd, hba
    return None, 0, 0, 0

st.set_page_config(page_title="Custom DES Designer", layout="wide")
st.title("🧪 Персонализиран Дизайнер на DES (Двойни и Тройни)")

# --- ИЗБОР НА ТИП СИСТЕМА ---
des_mode = st.radio("Изберете тип на евтектичната система:", 
                    ["Двоен DES (1 Акцептор + 1 Донор)", "Троен DES (1 Акцептор + 2 Различни Донора)"])

st.divider()

# --- ВЪВЕЖДАНЕ НА КОМПОНЕНТИ ---
st.header("1. Въвеждане на молекули (Чрез SMILES)")

# Създаваме колони според избора
if des_mode == "Двоен DES (1 Акцептор + 1 Донор)":
    cols = st.columns(2)
else:
    cols = st.columns(3)

components = []

# Колона 1: HBA
with cols[0]:
    st.subheader("Акцептор (HBA)")
    name_hba = st.text_input("Име на HBA:", value="Choline Chloride")
    smiles_hba = st.text_input("SMILES на HBA:", value="C[N+](C)(C)CCO.[Cl-]")
    ratio_hba = st.number_input("Молно съотношение (HBA):", min_value=0.1, value=1.0, step=0.5)
    components.append({"role": "HBA", "name": name_hba, "smiles": smiles_hba, "ratio": ratio_hba})

# Колона 2: HBD 1
with cols[1]:
    st.subheader("Донор 1 (HBD 1)")
    name_hbd1 = st.text_input("Име на HBD 1:", value="Urea")
    smiles_hbd1 = st.text_input("SMILES на HBD 1:", value="NC(=O)N")
    ratio_hbd1 = st.number_input("Молно съотношение (HBD 1):", min_value=0.1, value=1.0, step=0.5)
    components.append({"role": "HBD 1", "name": name_hbd1, "smiles": smiles_hbd1, "ratio": ratio_hbd1})

# Колона 3: HBD 2 (Ако е избран Троен DES)
if des_mode == "Троен DES (1 Акцептор + 2 Различни Донора)":
    with cols[2]:
        st.subheader("Донор 2 (HBD 2)")
        name_hbd2 = st.text_input("Име на HBD 2:", value="Glycerol")
        smiles_hbd2 = st.text_input("SMILES на HBD 2:", value="OCC(O)CO")
        ratio_hbd2 = st.number_input("Молно съотношение (HBD 2):", min_value=0.1, value=1.0, step=0.5)
        components.append({"role": "HBD 2", "name": name_hbd2, "smiles": smiles_hbd2, "ratio": ratio_hbd2})

st.divider()

# --- АНАЛИЗ И КАЛКУЛАТОР ---
st.header("2. Структурен Анализ и Лабораторна Рецепта")
target_mass = st.number_input("Желана обща маса на готовия DES (грамове):", min_value=1.0, value=50.0, step=5.0)

valid_structures = True
total_mass_ratio = 0
results = []

# Показваме структурите и смятаме масите
view_cols = st.columns(len(components))

for idx, comp in enumerate(components):
    with view_cols[idx]:
        mol, mw, hbd, hba = get_molecule_properties(comp["smiles"])
        if mol is None:
            st.error(f"Невалиден SMILES за {comp['name']}!")
            valid_structures = False
        else:
            img = Draw.MolToImage(mol, size=(200, 200))
            st.image(img)
            st.markdown(f"**{comp['name']} ({comp['role']})**")
            st.write(f"Маса: {mw:.2f} g/mol")
            st.info(f"Донори (HBD): {hbd} | Акцептори (HBA): {hba}")
            
            # Изчисляване на тегловното участие
            mass_part = comp["ratio"] * mw
            total_mass_ratio += mass_part
            results.append({
                "name": comp["name"],
                "role": comp["role"],
                "ratio": comp["ratio"],
                "mass_part": mass_part
            })

if valid_structures:
    st.success("✅ Всички структури са валидни! Ето вашата рецепта:")
    
    recipe_data = []
    total_hbd_network = 0
    total_hba_network = 0
    
    for res in results:
        # Изчисляване на финалните грамове
        grams_to_weigh = (res["mass_part"] / total_mass_ratio) * target_mass
        recipe_data.append({
            "Компонент": f"{res['name']} ({res['role']})",
            "Молове (Съотношение)": res["ratio"],
            "За претегляне (g)": f"{grams_to_weigh:.2f} g"
        })
        
    df_recipe = pd.DataFrame(recipe_data)
    st.table(df_recipe)
    
    # Кратък съвет за водородната мрежа
    st.caption("💡 Съвет: Колкото повече общи HBD (донори) и HBA (акцептори) има в сместа, толкова по-силна е мрежата от водородни връзки и по-нисък ще е вискозитетът на разтворителя.")

st.divider()

# --- ТЕРМОДИНАМИКА (САМО ЗА ДВОЙНИ) ---
if des_mode == "Двоен DES (1 Акцептор + 1 Донор)" and valid_structures:
    st.header("3. Термодинамика (Идеална Фазова Диаграма)")
    st.markdown("За да начертаем кривата на топене, въведете литературните данни за чистите вещества.")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        tm_hba = st.number_input(f"Темп. на топене на {components[0]['name']} (°C):", value=302.0)
        dh_hba = st.number_input(f"Енталпия на топене (J/mol) [Оставете 43000 ако не знаете]:", value=43000)
    with col_t2:
        tm_hbd = st.number_input(f"Темп. на топене на {components[1]['name']} (°C):", value=133.0)
        dh_hbd = st.number_input(f"Енталпия на топене (J/mol) [Оставете 14600 ако не знаете]:", value=14600)

    if st.button("Начертай фазова диаграма"):
        R_GAS = 8.314
        
        def calc_ideal_t(x, tm_c, dh):
            tm_k = tm_c + 273.15
            if x <= 0.001: return 0
            if x >= 0.999: return tm_k
            num = dh / R_GAS
            den = (dh / (R_GAS * tm_k)) - np.log(x)
            return (num / den) - 273.15 # Връща в Целзий

        x_hba = np.linspace(0.001, 0.999, 100)
        t_mix = []
        for x in x_hba:
            t1 = calc_ideal_t(x, tm_hba, dh_hba)
            t2 = calc_ideal_t(1-x, tm_hbd, dh_hbd)
            t_mix.append(max(t1, t2))
            
        eutectic_temp = min(t_mix)
        eutectic_x = x_hba[np.argmin(t_mix)]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x_hba, y=t_mix, mode='lines', name='Крива на топене', line=dict(color='blue', width=3)))
        fig.add_trace(go.Scatter(x=[eutectic_x], y=[eutectic_temp], mode='markers+text', 
                                 text=[f"{eutectic_temp:.1f} °C"], textposition="bottom center",
                                 marker=dict(color='red', size=12, symbol='star'), name='Евтектична точка'))
        
        fig.update_layout(title="Идеална граница Твърдо-Течно", xaxis_title=f"Молна част на {components[0]['name']}", yaxis_title="Температура (°C)", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)