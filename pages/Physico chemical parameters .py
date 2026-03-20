import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import math
import io
import os
import tempfile
from fpdf import FPDF

st.set_page_config(page_title="Термодинамика на ДЕС", layout="wide")

st.title("🧪 Термодинамични и Оптични Свойства на ДЕС и Водни Разтвори")
st.write("Автоматизирано изчисляване на $V_m$, **$V^E$ (Излишъчен обем)**, $R_m$, $f_m$, $\delta$ и $P_{int}$ с вградена база данни и опция за хидратация.")

# --- 0. БАЗА ДАННИ (АКЦЕПТОРИ И ДОНОРИ) ---
st.header("🗄️ База Данни: Компоненти")
st.write("За да се изчисли Излишъчният моларен обем ($V^E$), програмата се нуждае от плътността на чистите компоненти.")

col_db1, col_db2 = st.columns(2)

with col_db1:
    st.subheader("Акцептори (HBA)")
    default_acc = pd.DataFrame({
        "Име на Акцептор": ["Urea", "Choline Chloride"],
        "MW (g/mol)": [60.06, 139.62],
        "ρ чист (g/cm3)": [1.320, 1.100]
    })
    acc_df = st.data_editor(default_acc, num_rows="dynamic", use_container_width=True, key="acc_db")
    # Речник с вложени стойности за маса и плътност
    acc_dict = {row["Име на Акцептор"]: {"MW": row["MW (g/mol)"], "rho": row["ρ чист (g/cm3)"]} 
                for _, row in acc_df.iterrows() if pd.notnull(row["Име на Акцептор"]) and str(row["Име на Акцептор"]).strip() != ""}

with col_db2:
    st.subheader("Донори (HBD)")
    default_don = pd.DataFrame({
        "Име на Донор": ["Glycerol", "Xylose", "Fructose", "Malonic acid", "Water"],
        "MW (g/mol)": [92.0938, 150.13, 180.156, 104.01, 18.015],
        "ρ чист (g/cm3)": [1.261, 1.525, 1.690, 1.619, 0.997]
    })
    don_df = st.data_editor(default_don, num_rows="dynamic", use_container_width=True, key="don_db")
    don_dict = {row["Име на Донор"]: {"MW": row["MW (g/mol)"], "rho": row["ρ чист (g/cm3)"]} 
                for _, row in don_df.iterrows() if pd.notnull(row["Име на Донор"]) and str(row["Име на Донор"]).strip() != ""}

acc_names = list(acc_dict.keys())
don_names = list(don_dict.keys())

st.divider()

# --- 1. ГЛАВНА ТАБЛИЦА ЗА ВЪВЕЖДАНЕ ---
st.header("1. Въвеждане на Данни за ДЕС")
st.write("Избери компонентите. Въведи съотношенията, плътността на сместа, рефракционния индекс и **процента добавена вода**.")

default_main = pd.DataFrame({
    "DES Име": ["DES8 (Чист)", "DES8 (30% Вода)"],
    "Акцептор (A)": ["Urea", "Urea"],
    "n_A": [1.0, 1.0],
    "Донор 1 (D1)": ["Glycerol", "Glycerol"],
    "n_D1": [6.0, 6.0],
    "Донор 2 (D2)": ["Xylose", "Xylose"],
    "n_D2": [1.0, 1.0],
    "% Вода (wt%)": [0.0, 30.0],
    "ρ (g/cm3)": [1.3321, 1.2150],
    "nD": [1.484, 1.410]
})

column_config = {
    "Акцептор (A)": st.column_config.SelectboxColumn("Акцептор (A)", options=acc_names, required=True),
    "Донор 1 (D1)": st.column_config.SelectboxColumn("Донор 1 (D1)", options=don_names, required=True),
    "Донор 2 (D2)": st.column_config.SelectboxColumn("Донор 2 (D2)", options=[""] + don_names),
    "% Вода (wt%)": st.column_config.NumberColumn("% Вода (wt%)", min_value=0.0, max_value=99.9, step=0.1, format="%.1f")
}

df_input = st.data_editor(default_main, column_config=column_config, num_rows="dynamic", use_container_width=True)

if st.button("🚀 Изчисли Параметрите и Построй Графиките"):
    R = 8.314462
    T = 298.15
    NA = 6.022e23
    pi = math.pi
    MW_H2O = 18.015 
    RHO_H2O = 0.9970 # Плътност на чистата вода
    
    results = []
    
    for idx, row in df_input.iterrows():
        name = row["DES Име"]
        if pd.isna(name) or str(name).strip() == "":
            continue
            
        try:
            acc_name = row["Акцептор (A)"]
            d1_name = row["Донор 1 (D1)"]
            d2_name = row["Донор 2 (D2)"]
            
            # Извличане на свойства от базата данни
            mA = acc_dict.get(acc_name, {}).get("MW", 0)
            rhoA = acc_dict.get(acc_name, {}).get("rho", 0)
            
            mD1 = don_dict.get(d1_name, {}).get("MW", 0)
            rhoD1 = don_dict.get(d1_name, {}).get("rho", 0)
            
            mD2 = don_dict.get(d2_name, {}).get("MW", 0) if pd.notnull(d2_name) and d2_name != "" else 0
            rhoD2 = don_dict.get(d2_name, {}).get("rho", 0) if pd.notnull(d2_name) and d2_name != "" else 0
            
            nA = float(row['n_A']) if pd.notnull(row['n_A']) else 0
            nD1 = float(row['n_D1']) if pd.notnull(row['n_D1']) else 0
            nD2 = float(row['n_D2']) if pd.notnull(row['n_D2']) else 0
            
            p_water = float(row['% Вода (wt%)']) if pd.notnull(row['% Вода (wt%)']) else 0.0
            rho = float(row['ρ (g/cm3)'])
            nD = float(row['nD'])
            
            n_DES_total = nA + nD1 + nD2
            if n_DES_total == 0 or rho == 0:
                continue
                
            # Маса на чистия ДЕС
            m_DES_total = nA * mA + nD1 * mD1 + nD2 * mD2
            
            # Изчисляване на водата
            if 0 < p_water < 100:
                m_H2O = m_DES_total * (p_water / (100.0 - p_water))
                n_H2O = m_H2O / MW_H2O
            else:
                m_H2O = 0
                n_H2O = 0
                
            total_n = n_DES_total + n_H2O
            
            # 1. Моларен Обем (Vm)
            M_mix = (m_DES_total + m_H2O) / total_n
            Vm = M_mix / rho
            
            # 2. Идеален Моларен Обем (За излишъчния обем VE)
            V_ideal = 0
            if rhoA > 0: V_ideal += (nA / total_n) * (mA / rhoA)
            if rhoD1 > 0: V_ideal += (nD1 / total_n) * (mD1 / rhoD1)
            if nD2 > 0 and rhoD2 > 0: V_ideal += (nD2 / total_n) * (mD2 / rhoD2)
            if n_H2O > 0: V_ideal += (n_H2O / total_n) * (MW_H2O / RHO_H2O)
            
            # Проверка дали всички чисти плътности са налични
            if rhoA > 0 and rhoD1 > 0 and (nD2 == 0 or rhoD2 > 0):
                VE = Vm - V_ideal
            else:
                VE = np.nan # Ако липсва плътност в базата данни, не смятаме VE
            
            # 3. Рефракция, Свободен обем и Поляризуемост
            Rm = ((nD**2 - 1) / (nD**2 + 2)) * Vm
            fm = Vm - Rm
            delta = Rm / ((4/3) * pi * NA)
            
            # 4. Вътрешно Налягане
            r_excel = delta**(1/3)
            num = (2**(1/6)) * R * T
            term1 = (2**(1/6)) * Vm
            term2 = 2 * r_excel * (NA**(1/3)) * (Vm**(2/3))
            Pint = num / (term1 - term2)
            
            results.append({
                "DES Име": name,
                "wt% H2O": p_water,
                "M (g/mol)": M_mix,
                "V_m (cm3/mol)": Vm,
                "V^E (cm3/mol)": VE,
                "R_m (cm3/mol)": Rm,
                "f_m (cm3/mol)": fm,
                "δ (cm3)": delta,
                "P_int (MPa)": Pint,
                "ρ (g/cm3)": rho,
                "nD": nD
            })
        except Exception as e:
            st.warning(f"Грешка при изчисление на ред {idx+1}. Провери дали си въвел всички нужни стойности.")
            
    if results:
        res_df = pd.DataFrame(results)
        
        st.header("2. Изчислени Резултати")
        st.dataframe(res_df.style.format({
            "wt% H2O": "{:.1f}%",
            "M (g/mol)": "{:.3f}",
            "V_m (cm3/mol)": "{:.3f}",
            "V^E (cm3/mol)": "{:.3f}",
            "R_m (cm3/mol)": "{:.3f}",
            "f_m (cm3/mol)": "{:.3f}",
            "δ (cm3)": "{:.4e}",
            "P_int (MPa)": "{:.2f}",
            "ρ (g/cm3)": "{:.4f}",
            "nD": "{:.4f}"
        }), use_container_width=True)
        
        st.header("3. Корелационни Зависимости")
        col_plot1, col_plot2 = st.columns(2)
        
        with col_plot1:
            st.subheader("Матрица на Разсейване")
            fig_scatter = px.scatter_matrix(
                res_df,
                dimensions=['wt% H2O', 'ρ (g/cm3)', 'V_m (cm3/mol)', 'V^E (cm3/mol)', 'P_int (MPa)'],
                hover_name='DES Име',
                color='wt% H2O',
                height=700
            )
            fig_scatter.update_traces(diagonal_visible=False)
            st.plotly_chart(fig_scatter, use_container_width=True)
            
        with col_plot2:
            st.subheader("Корелационна Топлинна Карта")
            corr_cols = ['wt% H2O', 'M (g/mol)', 'V_m (cm3/mol)', 'V^E (cm3/mol)', 'R_m (cm3/mol)', 'f_m (cm3/mol)', 'δ (cm3)', 'P_int (MPa)', 'ρ (g/cm3)', 'nD']
            # Филтрираме колоните, които са изцяло празни (NaN), за да не гърми корелацията
            valid_cols = [c for c in corr_cols if res_df[c].notna().any()]
            corr_matrix = res_df[valid_cols].corr()
            fig_corr = px.imshow(corr_matrix, text_auto=".2f", aspect="auto", color_continuous_scale='RdBu_r', height=700)
            st.plotly_chart(fig_corr, use_container_width=True)

        # --- ЗАПАЗВАНЕ НА ГРАФИКИТЕ ЗА PDF ---
        scatter_img_path = None
        corr_img_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f1:
                scatter_img_path = f1.name
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f2:
                corr_img_path = f2.name
                
            fig_scatter.write_image(scatter_img_path, width=1000, height=800, scale=2)
            fig_corr.write_image(corr_img_path, width=800, height=800, scale=2)
        except Exception as e:
            st.warning("⚠️ Инсталирай `kaleido` (pip install -U kaleido), за да се виждат графиките в PDF доклада.")

        # --- ГЕНЕРИРАНЕ НА PDF ДОКЛАД ---
        def create_pdf(df, scatter_path, corr_path):
            pdf = FPDF(orientation='L')
            pdf.add_page()
            
            try:
                pdf.add_font('ArialUnicode', '', r"C:\Windows\Fonts\arial.ttf")
                pdf.add_font('ArialUnicode', 'B', r"C:\Windows\Fonts\arialbd.ttf")
                pdf.set_font('ArialUnicode', 'B', 14)
            except:
                pdf.set_font('Arial', 'B', 14)

            pdf.cell(270, 10, "Термодинамичен Доклад на ДЕС и Водни Разтвори", ln=True, align='C')
            pdf.ln(5)
            
            try: pdf.set_font('ArialUnicode', 'B', 9)
            except: pdf.set_font('Arial', 'B', 9)
            
            cols = ["DES Име", "H2O(%)", "M", "V_m", "V^E", "R_m", "f_m", "δ", "P_int", "ρ", "nD"]
            widths = [40, 15, 15, 20, 20, 20, 20, 25, 25, 20, 20]
            
            for i, col in enumerate(cols):
                pdf.cell(widths[i], 8, col, border=1, align='C')
            pdf.ln()
            
            try: pdf.set_font('ArialUnicode', '', 9)
            except: pdf.set_font('Arial', '', 9)
            
            for _, row in df.iterrows():
                pdf.cell(widths[0], 6, str(row["DES Име"])[:22], border=1)
                pdf.cell(widths[1], 6, f"{row['wt% H2O']:.1f}", border=1, align='C')
                pdf.cell(widths[2], 6, f"{row['M (g/mol)']:.2f}", border=1, align='C')
                pdf.cell(widths[3], 6, f"{row['V_m (cm3/mol)']:.2f}", border=1, align='C')
                
                # Защита за V^E, ако липсва плътност
                ve_val = f"{row['V^E (cm3/mol)']:.3f}" if pd.notna(row['V^E (cm3/mol)']) else "-"
                pdf.cell(widths[4], 6, ve_val, border=1, align='C')
                
                pdf.cell(widths[5], 6, f"{row['R_m (cm3/mol)']:.2f}", border=1, align='C')
                pdf.cell(widths[6], 6, f"{row['f_m (cm3/mol)']:.2f}", border=1, align='C')
                pdf.cell(widths[7], 6, f"{row['δ (cm3)']:.3e}", border=1, align='C')
                pdf.cell(widths[8], 6, f"{row['P_int (MPa)']:.2f}", border=1, align='C')
                pdf.cell(widths[9], 6, f"{row['ρ (g/cm3)']:.4f}", border=1, align='C')
                pdf.cell(widths[10], 6, f"{row['nD']:.4f}", border=1, align='C')
                pdf.ln()
                
            if scatter_path and os.path.exists(scatter_path):
                pdf.add_page()
                try: pdf.set_font('ArialUnicode', 'B', 12)
                except: pdf.set_font('Arial', 'B', 12)
                pdf.cell(270, 10, "Матрица на Разсейване (Scatter Matrix)", ln=True, align='C')
                pdf.image(scatter_path, x=25, w=230)
                
            if corr_path and os.path.exists(corr_path):
                pdf.add_page()
                try: pdf.set_font('ArialUnicode', 'B', 12)
                except: pdf.set_font('Arial', 'B', 12)
                pdf.cell(270, 10, "Корелационна Топлинна Карта (Pearson Heatmap)", ln=True, align='C')
                pdf.image(corr_path, x=60, w=170)
                
            return bytes(pdf.output())

        pdf_bytes = create_pdf(res_df, scatter_img_path, corr_img_path)
        
        for path in [scatter_img_path, corr_img_path]:
            if path and os.path.exists(path):
                try: os.remove(path)
                except: pass

        # --- ЕКСПОРТ EXCEL ---
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_input.to_excel(writer, index=False, sheet_name='Входни Данни')
                res_df.to_excel(writer, index=False, sheet_name='Изчислени Параметри')
                corr_matrix.to_excel(writer, sheet_name='Корелации')
                
                for sheet in writer.sheets:
                    writer.sheets[sheet].set_column('A:A', 25)
                    writer.sheets[sheet].set_column('B:N', 15)
                    
            st.download_button("📊 Изтегли всички резултати в Excel", data=output.getvalue(), file_name="DES_Aqueous_Thermodynamics.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        with col_d2:
            st.download_button("📄 Изтегли PDF Доклад (с графики)", data=pdf_bytes, file_name="DES_Aqueous_Report.pdf", mime="application/pdf")