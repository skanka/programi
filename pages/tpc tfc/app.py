import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
import io
import os
import tempfile
from fpdf import FPDF

st.set_page_config(page_title="Спектрофотометричен Анализ", layout="wide")

# --- ИНИЦИАЛИЗАЦИЯ НА БУТОНИТЕ "ИЗЧИСТИ" ---
if 'calib_key' not in st.session_state: st.session_state.calib_key = 0
if 'params_key' not in st.session_state: st.session_state.params_key = 0
if 'samples_key' not in st.session_state: st.session_state.samples_key = 0

def clear_calib(): st.session_state.calib_key += 1
def clear_params(): st.session_state.params_key += 1
def clear_samples(): st.session_state.samples_key += 1

st.title("🧪 Спектрофотометричен Анализ: Феноли и Флавоноиди")
st.write("Пълно изчисляване на проби и повторения (А1, А2, А3), статистика и детайлен експорт с висока резолюция.")

# --- 1. ИЗБОР НА АНАЛИЗ И МЕРНИ ЕДИНИЦИ ---
st.header("1. Тип на анализа и Мерни единици")
col_t1, col_t2 = st.columns([1, 2])
with col_t1:
    analysis_type = st.radio("Какво ще изчисляваме?", ["Общи феноли (TPC)", "Общи флавоноиди (TFC)"])
    std_name = "GAE" if "феноли" in analysis_type else "QE"

with col_t2:
    st.write("Изберете вашите мерни единици:")
    u_c1, u_c2, u_c3, u_c4 = st.columns(4)
    with u_c1: conc_unit = st.selectbox("Концентрация (Крива):", ["mg/L", "µg/mL", "ppm", "mg/mL"])
    with u_c2: vol_unit = st.selectbox("Обем разтворител:", ["mL", "L"])
    with u_c3: mass_unit = st.selectbox("Маса на билката:", ["g", "mg"])
    with u_c4: target_unit = st.selectbox("КРАЕН РЕЗУЛТАТ:", [f"mg {std_name}/g", f"µg {std_name}/g", f"mg {std_name}/100g"])

# --- 2. ДАННИ ЗА ЕКСТРАКЦИЯТА И ОБЩА ПРАЗНА ПРОБА ---
st.header("2. Параметри на екстракцията и Обща празна проба")
col_e1, col_e2, col_e3, col_e4, col_e5 = st.columns([2, 2, 2, 2, 1])
with col_e1: extract_vol = st.number_input(f"Обем ({vol_unit}):", min_value=0.001, value=10.0, format="%.3f", key=f"v_{st.session_state.params_key}")
with col_e2: herb_mass = st.number_input(f"Маса ({mass_unit}):", min_value=0.001, value=1.00, format="%.3f", key=f"m_{st.session_state.params_key}")
with col_e3: dilution = st.number_input("Разреждане (пъти):", min_value=1.0, value=1.0, format="%.1f", key=f"d_{st.session_state.params_key}")
with col_e4: blank_abs = st.number_input("Общ Blank (за кривата):", value=0.000, format="%.3f", key=f"b_{st.session_state.params_key}")
with col_e5: 
    st.write("")
    st.button("🧹 Изчисти", on_click=clear_params)

# --- 3. КАЛИБРАЦИОННА КРИВА ---
st.header("3. Калибрационно уравнение и Обхват")
eq_method = st.radio("Метод:", ["Построяване на нова крива", "Въвеждане на готово уравнение"])

m, c, min_abs, max_abs = 0.0, 0.0, 0.0, 0.0

if "готово" in eq_method:
    c1, c2, c3, c4 = st.columns(4)
    with c1: m = st.number_input("Наклон (m):", value=0.0050, format="%.5f")
    with c2: c = st.number_input("Отрез (c):", value=0.0100, format="%.5f")
    with c3: min_abs = st.number_input("Мин. Абсорбция на кривата:", value=0.000, format="%.3f")
    with c4: max_abs = st.number_input("Макс. Абсорбция на кривата:", value=1.000, format="%.3f")
    st.info(f"**y = {m:.5f}x + {c:.5f}** | Линеен обхват: Abs от {min_abs} до {max_abs}")

else:
    col_c1, col_c2 = st.columns([4, 1])
    with col_c2: 
        st.write("")
        st.button("🧹 Изчисти таблицата", on_click=clear_calib)
    
    with col_c1:
        default_calib = pd.DataFrame({
            f"Конц. ({conc_unit})": [0.0, 20.0, 40.0, 60.0, 80.0, 100.0],
            "Сурова Абсорбция (Abs)": [0.000, 0.120, 0.235, 0.350, 0.480, 0.590]
        })
        calib_df = st.data_editor(default_calib, num_rows="dynamic", use_container_width=True, key=f"c_table_{st.session_state.calib_key}")
    
    if st.button("📈 Построй кривата"):
        X = calib_df.iloc[:, 0].values.reshape(-1, 1)
        Y_raw = calib_df.iloc[:, 1].values
        Y_corrected = Y_raw - blank_abs
        
        model = LinearRegression().fit(X, Y_corrected)
        st.session_state['m'], st.session_state['c'] = model.coef_[0], model.intercept_
        st.session_state['min_abs'], st.session_state['max_abs'] = min(Y_corrected), max(Y_corrected)
        
        st.success(f"**y = {model.coef_[0]:.5f}x + {model.intercept_:.5f}** | R² = {model.score(X, Y_corrected):.4f}")
        
        fig_calib = px.scatter(x=X.flatten(), y=Y_corrected, title=f"Калибрационна крива (След изваждане на Общ Blank)")
        fig_calib.add_trace(go.Scatter(x=X.flatten(), y=model.predict(X), mode='lines', name='Trendline'))
        fig_calib.update_layout(font=dict(color='black'))
        st.plotly_chart(fig_calib)

if "нова" in eq_method and 'm' in st.session_state:
    m, c = st.session_state['m'], st.session_state['c']
    min_abs, max_abs = st.session_state['min_abs'], st.session_state['max_abs']

# --- 4. ПРОБИ И ИЗЧИСЛЕНИЯ ---
st.header("4. Въвеждане на пробите")
blank_type = st.radio("Каква празна проба ще използвате за неизвестните?", ["Обща (от Раздел 2)", "Индивидуална (въвежда се в таблицата за всяка проба)"])

col_s1, col_s2 = st.columns([4, 1])
with col_s2: 
    st.write("")
    st.button("🧹 Изчисти пробите", on_click=clear_samples)

with col_s1:
    default_samples = pd.DataFrame({
        "Име на пробата": ["Екстракт Вода", "Екстракт ДЕС", "Екстракт Етанол"], 
        "Abs 1 (Сурова)": [0.250, 0.720, 0.005],
        "Abs 2 (Сурова)": [0.255, 0.710, 0.006],
        "Abs 3 (Сурова)": [0.248, 0.730, 0.004]
    })
    
    if "Индивидуална" in blank_type:
        default_samples.insert(1, "Индив. Blank", [0.000, 0.000, 0.000])
        
    s_key = f"s_table_{st.session_state.samples_key}_{'ind' if 'Индивидуална' in blank_type else 'glob'}"
    samples_df = st.data_editor(default_samples, num_rows="dynamic", use_container_width=True, key=s_key)

if st.button("🚀 Изчисли статистика и съдържание"):
    if m == 0.0:
        st.error("Задайте валидно калибрационно уравнение или постройте крива!")
    else:
        results = samples_df.copy()
        
        if "Индивидуална" in blank_type:
            current_blank = results['Индив. Blank']
        else:
            current_blank = blank_abs
            
        # 1. Изчисляваме коригираната абсорбция
        for i in [1, 2, 3]:
            results[f'Abs {i} (Кор.)'] = results[f'Abs {i} (Сурова)'] - current_blank

        results['Ср. Abs (Кор.)'] = results[['Abs 1 (Кор.)', 'Abs 2 (Кор.)', 'Abs 3 (Кор.)']].mean(axis=1)
        
        def check_range(val):
            if val < min_abs: return "⚠️ Под минимума"
            elif val > max_abs: return "⚠️ Над максимума"
            else: return "✅ В обхвата"
            
        results['Статус (Обхват)'] = results['Ср. Abs (Кор.)'].apply(check_range)

        mult_c = 1000 if conc_unit == "mg/mL" else 1
        mult_v = 1 if vol_unit == "L" else 0.001
        mult_m = 1 if mass_unit == "g" else 0.001
        
        # 2. Детайлни изчисления за КОНЦЕНТРАЦИЯ и СЪДЪРЖАНИЕ
        for i in [1, 2, 3]:
            conc = (results[f'Abs {i} (Кор.)'] - c) / m
            results[f'Конц. {i} ({conc_unit})'] = conc.apply(lambda x: max(x, 0))
            
            total_mg = (results[f'Конц. {i} ({conc_unit})'] * mult_c) * (extract_vol * mult_v) * dilution
            content = total_mg / (herb_mass * mult_m)
            
            if "µg" in target_unit: content *= 1000
            elif "100g" in target_unit: content *= 100
            
            results[f'Съдържание {i} ({target_unit})'] = content

        # 3. Пълна Статистика (Концентрации и Съдържания)
        conc_cols = [f'Конц. 1 ({conc_unit})', f'Конц. 2 ({conc_unit})', f'Конц. 3 ({conc_unit})']
        results[f'Средно Конц. ({conc_unit})'] = results[conc_cols].mean(axis=1)
        results['SD Конц.'] = results[conc_cols].std(axis=1)
        results['RSD Конц. (%)'] = np.where(results[f'Средно Конц. ({conc_unit})'] == 0, 0, (results['SD Конц.'] / results[f'Средно Конц. ({conc_unit})']) * 100)

        content_cols = [f'Съдържание 1 ({target_unit})', f'Съдържание 2 ({target_unit})', f'Съдържание 3 ({target_unit})']
        results[f'Средно Съдърж. ({target_unit})'] = results[content_cols].mean(axis=1)
        results['SD Съдърж.'] = results[content_cols].std(axis=1)
        results['RSD Съдърж. (%)'] = np.where(results[f'Средно Съдърж. ({target_unit})'] == 0, 0, (results['SD Съдърж.'] / results[f'Средно Съдърж. ({target_unit})']) * 100)

        # --- ПОКАЗВАНЕ НА ОБОБЩЕНАТА ТАБЛИЦА ---
        st.subheader("Обобщени Резултати")
        display_cols = [
            'Име на пробата', 'Ср. Abs (Кор.)', 'Статус (Обхват)', 
            f'Средно Конц. ({conc_unit})', 'SD Конц.', 'RSD Конц. (%)',
            f'Средно Съдърж. ({target_unit})', 'SD Съдърж.', 'RSD Съдърж. (%)'
        ]
        if "Индивидуална" in blank_type: display_cols.insert(1, 'Индив. Blank')
        
        def highlight_extrapol(val):
            if 'Над максимума' in str(val): return 'background-color: #ffcccc; color: black;'
            elif 'Под минимума' in str(val): return 'background-color: #ffe6cc; color: black;'
            return 'background-color: #ccffcc; color: black;'
        st.dataframe(results[display_cols].round(4).style.map(highlight_extrapol, subset=['Статус (Обхват)']), use_container_width=True)
        
        # --- ПОКАЗВАНЕ НА ДЕТАЙЛНАТА ТАБЛИЦА С НОВАТА ПОДРЕДБА ---
        st.subheader("Детайлни Резултати и Статистика (Концентрации и Съдържания)")
        detailed_display_cols = [
            'Име на пробата',
            f'Конц. 1 ({conc_unit})', f'Конц. 2 ({conc_unit})', f'Конц. 3 ({conc_unit})',
            f'Съдържание 1 ({target_unit})', f'Съдържание 2 ({target_unit})', f'Съдържание 3 ({target_unit})',
            f'Средно Конц. ({conc_unit})', 'SD Конц.', 'RSD Конц. (%)',
            f'Средно Съдърж. ({target_unit})', 'SD Съдърж.', 'RSD Съдърж. (%)'
        ]
        st.dataframe(results[detailed_display_cols].round(4), use_container_width=True)

        # --- ГРАФИКА ---
        st.subheader("📊 Графично представяне")
        fig_res = px.bar(
            results, x='Име на пробата', y=f'Средно Съдърж. ({target_unit})', error_y='SD Съдърж.', 
            color='Статус (Обхват)', text_auto='.2f', title=f"Съдържание ± SD ({target_unit})",
            color_discrete_map={"✅ В обхвата": "#2ca02c", "⚠️ Над максимума": "#d62728", "⚠️ Под минимума": "#ff7f0e"}
        )
        # Настройки за по-тънки барове и черен шрифт
        fig_res.update_traces(width=0.4, textfont=dict(color='black'))
        fig_res.update_layout(font=dict(color='black'))
        
        st.plotly_chart(fig_res, use_container_width=True)

        # --- ЗАПАЗВАНЕ НА ГРАФИКАТА С ВИСОКА РЕЗОЛЮЦИЯ (За PDF) ---
        chart_img_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                chart_img_path = temp_file.name
            fig_res.write_image(chart_img_path, width=1200, height=700, scale=3)
        except Exception as e:
            st.warning("⚠️ Инсталирайте `kaleido` (pip install -U kaleido), за да се вижда графиката в PDF доклада.")

        # --- ГЕНЕРИРАНЕ НА PDF ДОКЛАД ---
        def create_pdf(df, chart_path):
            pdf = FPDF()
            pdf.add_page()
            
            font_regular = r"C:\Windows\Fonts\arial.ttf"
            font_bold = r"C:\Windows\Fonts\arialbd.ttf"
            try:
                pdf.add_font('ArialUnicode', '', font_regular)
                pdf.add_font('ArialUnicode', 'B', font_bold)
                pdf.set_font('ArialUnicode', 'B', 14)
            except:
                pdf.set_font('Arial', 'B', 14)

            # ЗАГЛАВИЕ
            pdf.cell(190, 10, f"Пълен Аналитичен Доклад: {analysis_type}", ln=True, align='C')
            pdf.ln(5)
            
            try: pdf.set_font('ArialUnicode', '', 10)
            except: pdf.set_font('Arial', '', 10)
            
            pdf.cell(190, 6, f"Калибрационно Уравнение: y = {m:.5f}x + {c:.5f}", ln=True)
            pdf.cell(190, 6, f"Линеен обхват: от Abs {min_abs:.3f} до Abs {max_abs:.3f}", ln=True)
            blank_info = "Индивидуален" if "Индивидуална" in blank_type else f"Общ ({blank_abs:.3f} Abs)"
            pdf.cell(190, 6, f"Параметри: Обем={extract_vol}{vol_unit} | Маса={herb_mass}{mass_unit} | Разреждане={dilution}x | Blank={blank_info}", ln=True)
            pdf.ln(5)
            
            # ТАБЛИЦА 1 (ОБОБЩЕНА С ВЕЧЕ ДОБАВЕНАТА КОНЦЕНТРАЦИЯ)
            try: pdf.set_font('ArialUnicode', 'B', 8)
            except: pdf.set_font('Arial', 'B', 8)
            pdf.cell(190, 8, "Таблица 1: Обобщени резултати", ln=True)
            
            # Разпределяме 190mm ширина на страницата
            pdf.cell(40, 8, "Проба", border=1, align='C')
            pdf.cell(15, 8, "Abs", border=1, align='C')
            pdf.cell(40, 8, f"Конц.({conc_unit})", border=1, align='C')
            pdf.cell(15, 8, "RSD%", border=1, align='C')
            pdf.cell(45, 8, f"Съдърж.({target_unit})", border=1, align='C')
            pdf.cell(15, 8, "RSD%", border=1, align='C')
            pdf.cell(20, 8, "Статус", border=1, align='C')
            pdf.ln()
            
            try: pdf.set_font('ArialUnicode', '', 8)
            except: pdf.set_font('Arial', '', 8)
            
            for index, row in df.iterrows():
                status_text = str(row['Статус (Обхват)']).replace("⚠️ ", "").replace("✅ ", "")
                conc_str = f"{row[f'Средно Конц. ({conc_unit})']:.3f} ± {row['SD Конц.']:.3f}"
                content_str = f"{row[f'Средно Съдърж. ({target_unit})']:.3f} ± {row['SD Съдърж.']:.3f}"
                
                pdf.cell(40, 7, str(row['Име на пробата'])[:20], border=1) 
                pdf.cell(15, 7, f"{row['Ср. Abs (Кор.)']:.3f}", border=1, align='C') 
                pdf.cell(40, 7, conc_str, border=1, align='C') 
                pdf.cell(15, 7, f"{row['RSD Конц. (%)']:.1f}%", border=1, align='C') 
                pdf.cell(45, 7, content_str, border=1, align='C') 
                pdf.cell(15, 7, f"{row['RSD Съдърж. (%)']:.1f}%", border=1, align='C') 
                pdf.cell(20, 7, status_text[:8], border=1, align='C') 
                pdf.ln()
            
            # ГРАФИКА
            if chart_path and os.path.exists(chart_path):
                pdf.ln(5)
                pdf.image(chart_path, x=20, w=170)

            # ТАБЛИЦА 2: ДЕТАЙЛНА СЪС СТАТИСТИКА
            pdf.add_page()
            try: pdf.set_font('ArialUnicode', 'B', 9)
            except: pdf.set_font('Arial', 'B', 9)
            pdf.cell(190, 8, "Таблица 2: Детайлни изчисления и Статистика (Концентрации и Съдържания)", ln=True)
            
            pdf.cell(60, 8, "Проба / Показател", border=1, align='C')
            pdf.cell(65, 8, f"Концентрация ({conc_unit})", border=1, align='C')
            pdf.cell(65, 8, f"Съдържание ({target_unit})", border=1, align='C')
            pdf.ln()
            
            for index, row in df.iterrows():
                name = str(row['Име на пробата'])[:25]
                
                try: pdf.set_font('ArialUnicode', '', 8)
                except: pdf.set_font('Arial', '', 8)
                
                for i in [1, 2, 3]:
                    c_val = row[f'Конц. {i} ({conc_unit})']
                    t_val = row[f'Съдържание {i} ({target_unit})']
                    pdf.cell(60, 6, f"{name} (Повт. {i})", border=1)
                    pdf.cell(65, 6, f"{c_val:.4f}", border=1, align='C')
                    pdf.cell(65, 6, f"{t_val:.4f}", border=1, align='C')
                    pdf.ln()
                
                try: pdf.set_font('ArialUnicode', 'B', 8)
                except: pdf.set_font('Arial', 'B', 8)
                
                mean_c, sd_c = row[f'Средно Конц. ({conc_unit})'], row['SD Конц.']
                mean_t, sd_t = row[f'Средно Съдърж. ({target_unit})'], row['SD Съдърж.']
                pdf.cell(60, 6, "Средно ± SD", border=1, align='R')
                pdf.cell(65, 6, f"{mean_c:.4f} ± {sd_c:.4f}", border=1, align='C', fill=False)
                pdf.cell(65, 6, f"{mean_t:.4f} ± {sd_t:.4f}", border=1, align='C', fill=False)
                pdf.ln()
                
                rsd_c, rsd_t = row['RSD Конц. (%)'], row['RSD Съдърж. (%)']
                pdf.cell(60, 6, "RSD (%)", border=1, align='R')
                pdf.cell(65, 6, f"{rsd_c:.2f}%", border=1, align='C', fill=False)
                pdf.cell(65, 6, f"{rsd_t:.2f}%", border=1, align='C', fill=False)
                pdf.ln()
                
                pdf.cell(190, 3, "", border=0, ln=True)
                
            return bytes(pdf.output())

        pdf_bytes = create_pdf(results, chart_img_path)
        
        if chart_img_path and os.path.exists(chart_img_path):
            try:
                os.remove(chart_img_path)
            except Exception:
                pass 
        
        # --- СТРУКТУРИРАН EXCEL ЕКСПОРТ (Нова Подредба) ---
        excel_cols = ['Име на пробата']
        if "Индивидуална" in blank_type: excel_cols.append('Индив. Blank')
        
        excel_cols.extend([
            'Abs 1 (Сурова)', 'Abs 1 (Кор.)', 'Abs 2 (Сурова)', 'Abs 2 (Кор.)', 'Abs 3 (Сурова)', 'Abs 3 (Кор.)', 'Ср. Abs (Кор.)', 'Статус (Обхват)',
            f'Конц. 1 ({conc_unit})', f'Конц. 2 ({conc_unit})', f'Конц. 3 ({conc_unit})',
            f'Съдържание 1 ({target_unit})', f'Съдържание 2 ({target_unit})', f'Съдържание 3 ({target_unit})',
            f'Средно Конц. ({conc_unit})', 'SD Конц.', 'RSD Конц. (%)',
            f'Средно Съдърж. ({target_unit})', 'SD Съдърж.', 'RSD Съдърж. (%)'
        ])
        excel_df = results[excel_cols]

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                excel_df.to_excel(writer, index=False, sheet_name='Детайлен Анализ')
                
                workbook = writer.book
                worksheet = writer.sheets['Детайлен Анализ']
                header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
                
                for col_num, value in enumerate(excel_df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                    
                worksheet.set_column('A:A', 25) 
                worksheet.set_column('B:I', 14) 
                worksheet.set_column('J:P', 16) 
                worksheet.set_column('Q:V', 18) 
                
            st.download_button("📊 Изтегли Детайлен Excel", data=output.getvalue(), file_name=f"{analysis_type}_Detailed.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        with col_d2:
            st.download_button("📄 Изтегли PDF Доклад (с графика)", data=pdf_bytes, file_name=f"{analysis_type}_Report.pdf", mime="application/pdf")