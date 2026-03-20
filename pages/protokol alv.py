# app.py
import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
from sklearn.linear_model import LinearRegression
import plotly.graph_objects as go
from scipy.stats import norm
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Spacer, Image as RLImage, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm  # Импортиран е cm за полетата на PDF-а
import matplotlib.pyplot as plt

st.set_page_config(page_title="HPLC Pro Interactive Protocol", layout="wide")

# -----------------------------
# DATABASE INIT
# -----------------------------
conn = sqlite3.connect("hplc_lab.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS results(
sample_name TEXT, analyte TEXT, result REAL, unit TEXT
)
""")

# -----------------------------
# SESSION STATE INIT
# -----------------------------
if 'samples' not in st.session_state:
    st.session_state.samples = {}
if 'standards' not in st.session_state:
    st.session_state.standards = pd.DataFrame()

# -----------------------------
# HEADER
# -----------------------------
st.title("🧪 HPLC Advanced Interactive Protocol")

tabs = st.tabs([
    "1. Method", 
    "2. Standards Prep", 
    "3. Sample Prep", 
    "4. Chromatogram", 
    "5. Calibration", 
    "6. Results & Report"
])

# -----------------------------
# 1. METHOD
# -----------------------------
with tabs[0]:
    st.subheader("HPLC Method Parameters")
    
    col1, col2 = st.columns(2)
    with col1:
        column = st.text_input("Column (e.g., C18 250x4.6mm 5µm)", "C18")
        stationary_phase = st.selectbox("Stationary Phase", ["RP", "NP", "HILIC"])
        flow = st.number_input("Flow rate (ml/min)", value=1.0, step=0.1)
        temperature = st.number_input("Column temperature (°C)", value=30)
        injection = st.number_input("Injection volume (µL)", value=10)
        
    with col2:
        mobile_phase_A = st.text_input("Mobile Phase A", "Water + 0.1% FA")
        mobile_phase_B = st.text_input("Mobile Phase B", "Acetonitrile")
        st.markdown("**Detector (4 Channels)**")
        wl1 = st.number_input("Wavelength 1 (nm)", value=254)
        wl2 = st.number_input("Wavelength 2 (nm)", value=280)
        wl3 = st.number_input("Wavelength 3 (nm)", value=320)
        wl4 = st.number_input("Wavelength 4 (nm)", value=360)

    elution_type = st.radio("Elution Type", ["Isocratic", "Gradient"], horizontal=True)
    
    gradient_df = pd.DataFrame()
    if elution_type == "Gradient":
        st.markdown("### Gradient Program")
        gradient_df = st.data_editor(
            pd.DataFrame({"Time(min)": [0, 5, 10], "A(%)": [95, 80, 50], "B(%)": [5, 20, 50]}),
            num_rows="dynamic", key="grad_table"
        )

# -----------------------------
# 2. STANDARDS PREPARATION
# -----------------------------
with tabs[1]:
    st.subheader("Stock Standard Preparation")
    st_col1, st_col2 = st.columns(2)
    
    with st_col1:
        std_name = st.text_input("Standard Name", "Vitamin C")
        std_target_conc = st.number_input("Target Stock Conc (mg/mL)", value=1.0)
        std_vol = st.number_input("Volumetric Flask (mL) for Stock", value=50.0)
    with st_col2:
        st.info("Calculation: Mass needed")
        calc_mass = std_target_conc * std_vol
        st.metric("Required Standard Mass", f"{calc_mass:.2f} mg")
        actual_mass = st.number_input("Actual Weighed Mass (mg)", value=float(calc_mass))
        actual_stock_conc = actual_mass / std_vol if std_vol > 0 else 0
        st.success(f"Actual Stock Concentration: {actual_stock_conc:.4f} mg/mL")

    st.divider()
    st.subheader("Working Standards Preparation (Calibration Curve)")
    st.write("Въведете желаната финална концентрация за кривата и обема на колбата. Програмата ще пресметне колко mL да пипетирате от изходния (Stock) стандарт.")
    
    work_stds = st.data_editor(
        pd.DataFrame({
            "Std Name": ["Std 1", "Std 2", "Std 3", "Std 4", "Std 5"],
            "Target Conc (mg/mL)": [0.01, 0.05, 0.10, 0.20, 0.50],
            "Final Vol (mL)": [10.0, 10.0, 10.0, 10.0, 10.0]
        }),
        num_rows="dynamic", key="work_stds_table"
    )
    
    st.session_state.standards = work_stds.copy()
    
    # Изчисляване на необходимия обем: V1 = (C2 * V2) / C1
    if actual_stock_conc > 0:
        st.session_state.standards["Stock Vol Needed (mL)"] = (st.session_state.standards["Target Conc (mg/mL)"] * st.session_state.standards["Final Vol (mL)"]) / actual_stock_conc
    else:
        st.session_state.standards["Stock Vol Needed (mL)"] = 0.0
        
    # Показване на резултатите
    st.markdown("#### Рецепта за приготвяне:")
    st.dataframe(
        st.session_state.standards[["Std Name", "Target Conc (mg/mL)", "Final Vol (mL)", "Stock Vol Needed (mL)"]].style.format({"Stock Vol Needed (mL)": "{:.4f}"}), 
        use_container_width=True
    )

# -----------------------------
# 3. SAMPLE PREPARATION
# -----------------------------
with tabs[2]:
    st.subheader("Sample Preparation Workflow")
    
    num_samples = st.number_input("Number of samples to prepare", min_value=1, value=1, step=1)
    
    for i in range(num_samples):
        with st.expander(f"Sample {i+1} Setup", expanded=True):
            s_name = st.text_input(f"Sample {i+1} Name", f"Sample_{i+1}", key=f"s_name_{i}")
            s_type = st.selectbox("Sample Type", ["Tablets", "Powder", "Syrup", "Liquid"], key=f"s_type_{i}")
            
            s_data = {"name": s_name, "type": s_type}
            col_a, col_b = st.columns(2)
            
            with col_a:
                if s_type == "Tablets":
                    s_data["avg_mass"] = st.number_input("Average Tablet Mass (mg)", value=500.0, key=f"avg_{i}")
                    s_data["weighed_amount"] = st.number_input("Weighed Powder Mass (mg)", value=100.0, key=f"w_{i}")
                elif s_type == "Powder":
                    s_data["weighed_amount"] = st.number_input("Weighed Mass (mg)", value=100.0, key=f"w_{i}")
                elif s_type in ["Syrup", "Liquid"]:
                    s_data["weighed_amount"] = st.number_input("Volume Taken (mL)", value=5.0, key=f"v_{i}")
                    if s_type == "Syrup":
                        s_data["density"] = st.number_input("Density (g/mL)", value=1.2, key=f"d_{i}")
            
            with col_b:
                st.markdown("**Extraction & Processing**")
                s_data["solvent"] = st.text_input("Extraction Solvent", "Water", key=f"sol_{i}")
                s_data["portions"] = st.number_input("Number of extraction portions", value=1, key=f"port_{i}")
                s_data["vol_per_portion"] = st.number_input("Volume per portion (mL)", value=50.0, key=f"vport_{i}")
                s_data["total_ext_vol"] = s_data["portions"] * s_data["vol_per_portion"]
                
                s_data["ultrasound"] = st.checkbox("Ultrasound applied?", key=f"us_{i}")
                if s_data["ultrasound"]:
                    s_data["us_time"] = st.number_input("US Time (min)", value=15, key=f"ust_{i}")
                
            st.markdown("**Further Dilution**")
            s_data["aliquot"] = st.number_input("Aliquot taken (mL)", value=1.0, key=f"ali_{i}")
            s_data["final_vol"] = st.number_input("Diluted to Final Vol (mL)", value=10.0, key=f"fvol_{i}")
            
            # Dilution Factor Calculation
            if s_data["weighed_amount"] > 0 and s_data["aliquot"] > 0:
                s_data["dilution_factor"] = (s_data["total_ext_vol"] / s_data["weighed_amount"]) * (s_data["final_vol"] / s_data["aliquot"])
            else:
                s_data["dilution_factor"] = 0.0
                
            st.info(f"Total Method Multiplier for {s_name}: {s_data['dilution_factor']:.4f}")
            
            st.session_state.samples[s_name] = s_data

# -----------------------------
# 4. CHROMATOGRAM
# -----------------------------
with tabs[3]:
    st.subheader("Realistic Chromatogram Simulation")
    st.write("Enter Retention Times (RT), Areas, and Peak Widths to generate the chromatogram.")
    
    chrom_data = st.data_editor(
        pd.DataFrame({
            "Peak Name": ["Std 1", "Sample 1"],
            "Type": ["Standard", "Sample"],
            "RT(min)": [2.5, 2.52],
            "Area": [1500.0, 1350.0],
            "Width": [0.05, 0.05] # Controls peak broadness
        }),
        num_rows="dynamic", key="chrom_editor"
    )
    
    # Generate Gaussian peaks for realistic looking chromatogram
    fig_chrom = go.Figure()
    max_rt = chrom_data["RT(min)"].max() if not chrom_data.empty else 5.0
    x_axis = np.linspace(0, max_rt * 1.5, 1000)
    
    colors_dict = {"Standard": "blue", "Sample": "red"}
    
    for _, row in chrom_data.iterrows():
        if row["Width"] > 0:
            amplitude = row["Area"] / (row["Width"] * np.sqrt(2 * np.pi))
            y_axis = amplitude * norm.pdf(x_axis, row["RT(min)"], row["Width"])
            
            fig_chrom.add_trace(go.Scatter(
                x=x_axis, y=y_axis, mode='lines', 
                name=f"{row['Peak Name']} ({row['Type']})",
                line=dict(color=colors_dict.get(row['Type'], 'green'))
            ))
        
    fig_chrom.update_layout(title="Simulated HPLC Chromatogram", xaxis_title="Retention Time (min)", yaxis_title="Absorbance (mAU)", template="plotly_white")
    st.plotly_chart(fig_chrom, use_container_width=True)

# -----------------------------
# 5. CALIBRATION
# -----------------------------
with tabs[4]:
    st.subheader("Calibration Curve")
    st.info("Input data manually or copy from the Standards Preparation tab.")
    
    # Вземаме изчислените (Target) концентрации от таб 2
    default_concs = st.session_state.standards["Target Conc (mg/mL)"].tolist() if not st.session_state.standards.empty else [0.01, 0.05, 0.1, 0.2, 0.5]
    default_areas = [200.0, 1000.0, 2100.0, 4000.0, 10100.0][:len(default_concs)]
    
    # Ако дължината не съвпада, запълваме с нули
    while len(default_areas) < len(default_concs):
        default_areas.append(0.0)
        
    calib = st.data_editor(
        pd.DataFrame({
            "Concentration": default_concs,
            "Signal_Area": default_areas
        }),
        num_rows="dynamic", key="calib_table"
    )

    slope, intercept, r2, lod, loq = None, None, None, None, None
    fig_calib, ax = plt.subplots(figsize=(6,4))

    if len(calib) > 2:
        X = calib["Concentration"].values.reshape(-1,1)
        y = calib["Signal_Area"].values

        model = LinearRegression().fit(X,y)
        slope = model.coef_[0]
        intercept = model.intercept_
        r2 = model.score(X,y)
        
        residuals = y - model.predict(X)
        sigma = np.std(residuals) if np.std(residuals) > 0 else 0.001
        lod = 3.3 * sigma / slope if slope != 0 else 0
        loq = 10 * sigma / slope if slope != 0 else 0

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Slope", f"{slope:.2f}")
        c2.metric("Intercept", f"{intercept:.2f}")
        c3.metric("R²", f"{r2:.5f}")
        c4.metric("LOD", f"{lod:.4f}")
        c5.metric("LOQ", f"{loq:.4f}")

        ax.scatter(calib["Concentration"], calib["Signal_Area"], color='blue')
        x_line = np.linspace(min(calib["Concentration"])*0.8, max(calib["Concentration"])*1.1, 100)
        ax.plot(x_line, slope*x_line + intercept, color='red', linestyle='--')
        ax.set_xlabel("Concentration (mg/mL)")
        ax.set_ylabel("Peak Area")
        ax.set_title("Linear Regression")
        ax.grid(True, linestyle=':', alpha=0.6)
        st.pyplot(fig_calib)

# -----------------------------
# 6. RESULTS & REPORT
# -----------------------------
with tabs[5]:
    st.subheader("Final Results Calculation")
    
    if not st.session_state.samples:
        st.warning("Please setup at least one sample in the Sample Prep tab.")
    else:
        res_sel_sample = st.selectbox("Select Sample to Calculate", list(st.session_state.samples.keys()))
        res_area = st.number_input("Enter Peak Area for this Sample", value=1350.0)
        target_unit = st.selectbox("Convert Result to", ["mg/g", "mg/tablet", "mg/mL", "g/100g (%)", "ppm"])
        
        final_result_val = None
        
        if slope and slope > 0 and res_sel_sample:
            calc_conc_in_vial = (res_area - intercept) / slope
            s_dict = st.session_state.samples[res_sel_sample]
            mult_factor = s_dict["dilution_factor"]
            
            base_res_mg_per_unit = calc_conc_in_vial * mult_factor
            
            if target_unit == "mg/g" or target_unit == "mg/mL":
                final_result_val = base_res_mg_per_unit * 1000  
            elif target_unit == "mg/tablet" and s_dict["type"] == "Tablets":
                final_result_val = base_res_mg_per_unit * s_dict.get("avg_mass", 0)
            elif target_unit == "g/100g (%)":
                final_result_val = base_res_mg_per_unit * 100 
            elif target_unit == "ppm":
                final_result_val = base_res_mg_per_unit * 1_000_000
            else:
                final_result_val = base_res_mg_per_unit * 1000 
                
            st.success(f"Calculated Concentration in Vial: {calc_conc_in_vial:.4f} mg/mL")
            st.metric(f"Final Result for {res_sel_sample}", f"{final_result_val:.4f} {target_unit}")
            
            if st.button("Save Result to DB"):
                c.execute("INSERT INTO results VALUES (?,?,?,?)", (res_sel_sample, std_name, final_result_val, target_unit))
                conn.commit()
                st.toast("Result Saved!")

        st.divider()
        st.subheader("📄 Generate Comprehensive PDF Report")
        st.write("This PDF will include Method, Preparation steps, Chromatogram image, Calibration, and Results.")
        
        if st.button("Download Full PDF Report", type="primary"):
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
            styles = getSampleStyleSheet()
            elements = []

            # Helper function for tables
            def make_pdf_table(data):
                t = Table(data)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')
                ]))
                return t

            # Title
            elements.append(Paragraph("HPLC Complete Analytical Report", styles['Title']))
            elements.append(Spacer(1, 20))

            # 1. Method
            elements.append(Paragraph("1. HPLC Method", styles['Heading2']))
            m_data = [
                ["Parameter", "Value"],
                ["Column", column], ["Stationary Phase", stationary_phase],
                ["Flow rate (ml/min)", str(flow)], ["Temperature (C)", str(temperature)],
                ["Injection Vol (uL)", str(injection)], ["Elution Type", elution_type],
                ["Mobile Phase A", mobile_phase_A], ["Mobile Phase B", mobile_phase_B],
                ["Wavelengths", f"{wl1}, {wl2}, {wl3}, {wl4} nm"]
            ]
            elements.append(make_pdf_table(m_data))
            
            if elution_type == "Gradient" and not gradient_df.empty:
                elements.append(Spacer(1, 10))
                elements.append(Paragraph("Gradient Table:", styles['Normal']))
                grad_list = [list(gradient_df.columns)] + gradient_df.values.tolist()
                elements.append(make_pdf_table(grad_list))
            elements.append(Spacer(1, 20))

            # 2. Standards
            elements.append(Paragraph("2. Standards Preparation", styles['Heading2']))
            elements.append(Paragraph(f"Stock: {std_name}, Target: {std_target_conc} mg/mL, Actual: {actual_stock_conc:.4f} mg/mL", styles['Normal']))
            elements.append(Spacer(1, 10))
            if not st.session_state.standards.empty:
                # Взимаме само необходимите колони за изпринтяване
                pdf_stds_df = st.session_state.standards[["Std Name", "Target Conc (mg/mL)", "Final Vol (mL)", "Stock Vol Needed (mL)"]].copy()
                pdf_stds_df["Stock Vol Needed (mL)"] = pdf_stds_df["Stock Vol Needed (mL)"].map("{:.4f}".format)
                std_list = [list(pdf_stds_df.columns)] + pdf_stds_df.values.tolist()
                elements.append(make_pdf_table(std_list))
            elements.append(Spacer(1, 20))

            # 3. Sample Prep
            elements.append(Paragraph("3. Sample Preparation", styles['Heading2']))
            for smp_k, smp_v in st.session_state.samples.items():
                elements.append(Paragraph(f"<b>{smp_k} ({smp_v['type']})</b>", styles['Normal']))
                smp_text = f"Weighed: {smp_v['weighed_amount']}, Extraction Vol: {smp_v['total_ext_vol']} mL, Aliquot: {smp_v['aliquot']} mL diluted to {smp_v['final_vol']} mL. Dilution Factor: {smp_v['dilution_factor']:.4f}"
                if smp_v['type'] == 'Tablets':
                    smp_text += f", Avg Tablet Mass: {smp_v.get('avg_mass', 0)} mg."
                elements.append(Paragraph(smp_text, styles['Normal']))
                elements.append(Spacer(1, 5))
            elements.append(Spacer(1, 15))

            # 4. Chromatogram Image (ПРЕПРАВЕНО С MATPLOTLIB ЗА СИГУРНОСТ)
            elements.append(Paragraph("4. Chromatogram", styles['Heading2']))
            try:
                # Създаваме хроматограмата наново само за PDF-а
                fig_chrom_pdf, ax_chrom = plt.subplots(figsize=(7, 4))
                max_rt_pdf = chrom_data["RT(min)"].max() if not chrom_data.empty else 5.0
                x_axis_pdf = np.linspace(0, max_rt_pdf * 1.5, 1000)
                colors_dict_pdf = {"Standard": "blue", "Sample": "red"}
                
                for _, row in chrom_data.iterrows():
                    if row["Width"] > 0:
                        amplitude = row["Area"] / (row["Width"] * np.sqrt(2 * np.pi))
                        y_axis_pdf = amplitude * norm.pdf(x_axis_pdf, row["RT(min)"], row["Width"])
                        ax_chrom.plot(x_axis_pdf, y_axis_pdf, color=colors_dict_pdf.get(row['Type'], 'green'), label=f"{row['Peak Name']} ({row['Type']})")
                
                ax_chrom.set_title("Simulated HPLC Chromatogram")
                ax_chrom.set_xlabel("Retention Time (min)")
                ax_chrom.set_ylabel("Absorbance (mAU)")
                ax_chrom.legend()
                ax_chrom.grid(True, linestyle=':', alpha=0.6)
                
                buf_chrom = BytesIO()
                fig_chrom_pdf.savefig(buf_chrom, format='png', bbox_inches='tight')
                buf_chrom.seek(0)
                elements.append(RLImage(buf_chrom, width=14*cm, height=8*cm))
                plt.close(fig_chrom_pdf)
            except Exception as e:
                elements.append(Paragraph(f"<i>Could not render chromatogram image. Error: {str(e)}</i>", styles['Normal']))
            elements.append(Spacer(1, 20))

            # 5. Calibration
            elements.append(Paragraph("5. Calibration", styles['Heading2']))
            if slope:
                cal_data = [
                    ["Slope", f"{slope:.4f}"], ["Intercept", f"{intercept:.4f}"], 
                    ["R2", f"{r2:.5f}"], ["LOD", f"{lod:.4f}"], ["LOQ", f"{loq:.4f}"]
                ]
                elements.append(make_pdf_table(cal_data))
                elements.append(Spacer(1, 10))
                
                buf_plt = BytesIO()
                fig_calib.savefig(buf_plt, format='png', bbox_inches='tight')
                buf_plt.seek(0)
                elements.append(RLImage(buf_plt, width=12*cm, height=8*cm))
            elements.append(Spacer(1, 20))

            # 6. Final Result
            elements.append(Paragraph("6. Final Calculated Result", styles['Heading2']))
            if final_result_val:
                elements.append(Paragraph(f"<b>Sample:</b> {res_sel_sample}", styles['Normal']))
                elements.append(Paragraph(f"<b>Result:</b> {final_result_val:.4f} {target_unit}", styles['Normal']))
            else:
                elements.append(Paragraph("No final result calculated.", styles['Normal']))

            doc.build(elements)

            st.download_button(
                label="📥 Click here to download PDF",
                data=buffer.getvalue(),
                file_name="HPLC_Comprehensive_Report.pdf",
                mime="application/pdf"
            )
