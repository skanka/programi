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

st.set_page_config(page_title="Повърхностно Напрежение на Течности", layout="wide")

if 'clear_key' not in st.session_state: st.session_state.clear_key = 0
def clear_data(): st.session_state.clear_key += 1

st.title("💧 Определяне на Повърхностно Напрежение на Течности")
st.write("Метод на OWRK: Изчисляване на повърхностното напрежение на неизвестна течност чрез измерване на контактния ѝ ъгъл върху референтни твърди повърхности.")

# --- 1. ПАРАМЕТРИ НА РЕФЕРЕНТНИТЕ ПОВЪРХНОСТИ ---
st.header("1. Референтни твърди повърхности (Константи)")
st.write("Това са вашите стандартни повърхности с предварително известно повърхностно напрежение ($mJ/m^2$).")

col_ref1, col_ref2 = st.columns([3, 1])
with col_ref1:
    default_solids = pd.DataFrame({
        "Твърда Повърхност": ["Medical Steel", "Glass", "Polymer"],
        "Полярна част (γ_s^p)": [25.86, 23.38, 0.30],
        "Дисперсна част (γ_s^d)": [17.79, 31.17, 36.19]
    })
    solids_df = st.data_editor(default_solids, use_container_width=True, hide_index=True)

solids_dict = {row['Твърда Повърхност']: {'p': row['Полярна част (γ_s^p)'], 'd': row['Дисперсна част (γ_s^d)']} for index, row in solids_df.iterrows()}
surf_names = list(solids_dict.keys())

# --- 2. ВЪВЕЖДАНЕ НА КОНТАКТНИ ЪГЛИ ЗА ТЕЧНОСТТА ---
st.header("2. Контактни ъгли на Изследваната Течност")

# Текстово поле за името на течността (извън таблицата)
liquid_name = st.text_input("🧪 Въведете име на изследваната течност:", value="DES 013008")

st.write("Въведете отчетените ъгли (ляв и десен). Ако нямате 10 повторения, просто оставете излишните редове празни!")

col_a1, col_a2 = st.columns([5, 1])
with col_a2:
    st.write("")
    st.button("🧹 Изчисти таблицата", on_click=clear_data)

with col_a1:
    # Генерираме таблица с ПРАЗНИ клетки (NaN)
    default_angles = pd.DataFrame({
        "Капка (Повторение)": [f"Капка {i+1}" for i in range(10)],
        f"{surf_names[0]} (L)": np.full(10, np.nan),
        f"{surf_names[0]} (R)": np.full(10, np.nan),
        f"{surf_names[1]} (L)": np.full(10, np.nan),
        f"{surf_names[1]} (R)": np.full(10, np.nan),
        f"{surf_names[2]} (L)": np.full(10, np.nan),
        f"{surf_names[2]} (R)": np.full(10, np.nan)
    })
    
    s_key = f"angles_{st.session_state.clear_key}"
    angles_df = st.data_editor(default_angles, num_rows="dynamic", use_container_width=True, key=s_key, hide_index=True)

# Автоматично изчисляване на средните ъгли В РЕАЛНО ВРЕМЕ
avg_angles_df = angles_df[["Капка (Повторение)"]].copy()
for surf in surf_names:
    avg_col_name = f"{surf} (Ср. Ъгъл)"
    # Изчислява средното, като игнорира празни клетки
    avg_angles_df[avg_col_name] = angles_df[[f"{surf} (L)", f"{surf} (R)"]].mean(axis=1)
    angles_df[avg_col_name] = avg_angles_df[avg_col_name]

# Показваме само редовете, които имат поне една въведена стойност, за да не стои грозно с NaN
display_avg_df = avg_angles_df.dropna(how='all', subset=[f"{surf} (Ср. Ъгъл)" for surf in surf_names])

st.markdown("##### 📌 Изчислени Средни Ъгли (θ avg) за всяка повърхност:")
if display_avg_df.empty:
    st.info("Таблицата е празна. Въведете данни по-горе, за да видите средните ъгли.")
else:
    st.dataframe(display_avg_df.round(2).style.highlight_max(axis=0, color='#f0f2f6'), use_container_width=True, hide_index=True)


if st.button("🚀 Изчисли Повърхностното Напрежение на Течността"):
    df = angles_df.copy()
    
    # ФИЛТРИРАНЕ: Премахваме редовете (капките), при които липсват данни за някоя от повърхностите
    df_calc = df.dropna(subset=[f"{surf} (Ср. Ъгъл)" for surf in surf_names])
    
    if df_calc.empty:
        st.error("❌ Грешка: Моля, въведете контактни ъгли за поне една капка върху **всичките три** повърхности.")
    else:
        # 2. Математическият модел (Трансформация в линейно уравнение)
        results_list = []
        
        X_vals = []
        for surf in surf_names:
            gamma_sd = solids_dict[surf]['d']
            gamma_sp = solids_dict[surf]['p']
            x = np.sqrt(gamma_sd / gamma_sp)
            X_vals.append(x)
            
        X_array = np.array(X_vals).reshape(-1, 1)

        for index, row in df_calc.iterrows():
            Y_vals = []
            for surf in surf_names:
                gamma_sp = solids_dict[surf]['p']
                theta_deg = row[f"{surf} (Ср. Ъгъл)"]
                y = (1 + np.cos(np.radians(theta_deg))) / (2 * np.sqrt(gamma_sp))
                Y_vals.append(y)
                
            Y_array = np.array(Y_vals)
            
            # Линейна регресия y = ax + b
            model = LinearRegression().fit(X_array, Y_array)
            a = model.coef_[0]     
            b = model.intercept_   
            r2 = model.score(X_array, Y_array)
            
            # ИЗЧИСЛЯВАНЕ НА ПАРАМЕТРИТЕ НА ТЕЧНОСТТА
            gamma_l = 1 / (a**2 + b**2)
            gamma_ld = (a * gamma_l)**2
            gamma_lp = (b * gamma_l)**2
            
            results_list.append({
                "Капка": row["Капка (Повторение)"],
                "γ_l^d (Дисперсна част)": gamma_ld,
                "γ_l^p (Полярна част)": gamma_lp,
                "γ_l (Общо ПН на Течността)": gamma_l,
                "Полярно съотношение (γ_p/γ_d)": gamma_lp / gamma_ld,
                "R² (Модел)": r2
            })
            
        results_df = pd.DataFrame(results_list)
        
        # 3. Статистика за течността (защита срещу деление на 0 при само 1 капка)
        stats_data = {
            "Показател": ["Средно", "SD", "RSD (%)"],
            "γ_l^d (Дисперсна част)": [results_df["γ_l^d (Дисперсна част)"].mean(), results_df["γ_l^d (Дисперсна част)"].std(), np.nan],
            "γ_l^p (Полярна част)": [results_df["γ_l^p (Полярна част)"].mean(), results_df["γ_l^p (Полярна част)"].std(), np.nan],
            "γ_l (Общо ПН на Течността)": [results_df["γ_l (Общо ПН на Течността)"].mean(), results_df["γ_l (Общо ПН на Течността)"].std(), np.nan],
            "Полярно съотношение": [results_df["Полярно съотношение (γ_p/γ_d)"].mean(), results_df["Полярно съотношение (γ_p/γ_d)"].std(), np.nan]
        }
        
        # Изчисляваме RSD само ако имаме повече от 1 валидна капка
        if len(results_df) > 1:
            stats_data["γ_l^d (Дисперсна част)"][2] = (stats_data["γ_l^d (Дисперсна част)"][1] / stats_data["γ_l^d (Дисперсна част)"][0]) * 100
            stats_data["γ_l^p (Полярна част)"][2] = (stats_data["γ_l^p (Полярна част)"][1] / stats_data["γ_l^p (Полярна част)"][0]) * 100
            stats_data["γ_l (Общо ПН на Течността)"][2] = (stats_data["γ_l (Общо ПН на Течността)"][1] / stats_data["γ_l (Общо ПН на Течността)"][0]) * 100
            stats_data["Полярно съотношение"][2] = (stats_data["Полярно съотношение"][1] / stats_data["Полярно съотношение"][0]) * 100
            
        stats_df = pd.DataFrame(stats_data)

        # --- ВИЗУАЛИЗАЦИЯ ---
        st.subheader(f"📊 Обобщени Резултати за: {liquid_name} (базирани на {len(results_df)} капки)")
        st.dataframe(stats_df.round(4).style.highlight_max(axis=0, color='#e6f2ff'), use_container_width=True, hide_index=True)
        
        st.subheader("Детайлни изчисления за всяка капка")
        st.dataframe(results_df.round(4), use_container_width=True, hide_index=True)

        # --- ГРАФИКА ---
        st.subheader(f"📉 OWRK Линеен Модел за {liquid_name} (по средните ъгли)")
        
        avg_Y_vals = []
        for surf in surf_names:
            gamma_sp = solids_dict[surf]['p']
            avg_theta_deg = df_calc[f"{surf} (Ср. Ъгъл)"].mean() # Взимаме средното само от попълнените редове
            y = (1 + np.cos(np.radians(avg_theta_deg))) / (2 * np.sqrt(gamma_sp))
            avg_Y_vals.append(y)
            
        avg_Y_array = np.array(avg_Y_vals)
        global_model = LinearRegression().fit(X_array, avg_Y_array)
        
        fig_owrk = px.scatter(
            x=X_vals, y=avg_Y_vals, text=surf_names,
            labels={'x': 'x = sqrt(γ_s^d / γ_s^p)', 'y': 'y = (1 + cos(θ)) / (2*sqrt(γ_s^p))'},
            title=f"OWRK Графика за течност '{liquid_name}' (R² = {global_model.score(X_array, avg_Y_array):.4f})"
        )
        fig_owrk.update_traces(textposition="top center", marker=dict(size=12, color='red'), textfont=dict(color='black'))
        
        x_range = np.linspace(min(X_vals)*0.9, max(X_vals)*1.1, 100).reshape(-1, 1)
        fig_owrk.add_trace(go.Scatter(x=x_range.flatten(), y=global_model.predict(x_range), mode='lines', name='Linear Fit', line=dict(color='blue', dash='dash')))
        fig_owrk.update_layout(font=dict(color='black'))
        
        st.plotly_chart(fig_owrk, use_container_width=True)

        # --- ЗАПАЗВАНЕ НА ГРАФИКАТА ---
        chart_img_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                chart_img_path = temp_file.name
            fig_owrk.write_image(chart_img_path, width=1200, height=700, scale=3)
        except: pass

        # --- ГЕНЕРИРАНЕ НА PDF ДОКЛАД ---
        def create_pdf(results_table, stats_table, chart_path):
            pdf = FPDF()
            pdf.add_page()
            try:
                pdf.add_font('ArialUnicode', '', r"C:\Windows\Fonts\arial.ttf")
                pdf.add_font('ArialUnicode', 'B', r"C:\Windows\Fonts\arialbd.ttf")
                pdf.set_font('ArialUnicode', 'B', 14)
            except: pdf.set_font('Arial', 'B', 14)

            pdf.cell(190, 10, f"Доклад: Повърхностно напрежение на '{liquid_name}'", ln=True, align='C')
            pdf.ln(5)
            
            try: pdf.set_font('ArialUnicode', 'B', 10)
            except: pdf.set_font('Arial', 'B', 10)
            pdf.cell(190, 8, f"Таблица 1: Обобщена Статистика (базирана на {len(results_table)} капки)", ln=True)
            
            cols = stats_table.columns.tolist()
            pdf.cell(30, 8, "Показател", border=1, align='C')
            pdf.cell(35, 8, "Дисперсна (γ_l^d)", border=1, align='C')
            pdf.cell(35, 8, "Полярна (γ_l^p)", border=1, align='C')
            pdf.cell(45, 8, "Общо ПН (γ_l)", border=1, align='C')
            pdf.cell(45, 8, "Ratio (γ_p/γ_d)", border=1, align='C')
            pdf.ln()
            
            try: pdf.set_font('ArialUnicode', '', 9)
            except: pdf.set_font('Arial', '', 9)
            for _, row in stats_table.iterrows():
                pdf.cell(30, 7, str(row[cols[0]]), border=1)
                pdf.cell(35, 7, f"{row[cols[1]]:.4f}", border=1, align='C')
                pdf.cell(35, 7, f"{row[cols[2]]:.4f}", border=1, align='C')
                pdf.cell(45, 7, f"{row[cols[3]]:.4f}", border=1, align='C')
                pdf.cell(45, 7, f"{row[cols[4]]:.4f}", border=1, align='C')
                pdf.ln()

            if chart_path and os.path.exists(chart_path):
                pdf.ln(5)
                pdf.image(chart_path, x=20, w=170)

            pdf.add_page()
            try: pdf.set_font('ArialUnicode', 'B', 10)
            except: pdf.set_font('Arial', 'B', 10)
            pdf.cell(190, 8, f"Таблица 2: Детайлни резултати за всяка капка от '{liquid_name}'", ln=True)
            
            pdf.cell(30, 8, "Капка", border=1, align='C')
            pdf.cell(35, 8, "Дисперсна (γ_l^d)", border=1, align='C')
            pdf.cell(35, 8, "Полярна (γ_l^p)", border=1, align='C')
            pdf.cell(45, 8, "Общо ПН (γ_l)", border=1, align='C')
            pdf.cell(25, 8, "R² (Модел)", border=1, align='C')
            pdf.ln()
            
            try: pdf.set_font('ArialUnicode', '', 9)
            except: pdf.set_font('Arial', '', 9)
            for _, row in results_table.iterrows():
                pdf.cell(30, 6, str(row["Капка"]), border=1)
                pdf.cell(35, 6, f"{row['γ_l^d (Дисперсна част)']:.4f}", border=1, align='C')
                pdf.cell(35, 6, f"{row['γ_l^p (Полярна част)']:.4f}", border=1, align='C')
                pdf.cell(45, 6, f"{row['γ_l (Общо ПН на Течността)']:.4f}", border=1, align='C')
                pdf.cell(25, 6, f"{row['R² (Модел)']:.4f}", border=1, align='C')
                pdf.ln()
                
            return bytes(pdf.output())

        pdf_bytes = create_pdf(results_df, stats_df, chart_img_path)
        if chart_img_path and os.path.exists(chart_img_path):
            try: os.remove(chart_img_path)
            except: pass

        # --- ЕКСПОРТ EXCEL ---
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # В Ексела запазваме САМО попълнените редове
                df_calc.to_excel(writer, index=False, sheet_name='Сурови и Средни Ъгли')
                results_df.to_excel(writer, index=False, sheet_name=f'ПН на {liquid_name}')
                stats_df.to_excel(writer, index=False, sheet_name='Статистика')
                
                for sheet in writer.sheets:
                    writer.sheets[sheet].set_column('A:A', 20)
                    writer.sheets[sheet].set_column('B:Z', 22)
                    
            safe_name = liquid_name.replace(" ", "_").replace("/", "_")
            st.download_button("📊 Изтегли пълен Excel", data=output.getvalue(), file_name=f"Surface_Tension_{safe_name}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        with col_d2:
            st.download_button("📄 Изтегли PDF Доклад (с графика)", data=pdf_bytes, file_name=f"Surface_Tension_Report_{safe_name}.pdf", mime="application/pdf")