import streamlit as st

# 1. Основна конфигурация на портала
st.set_page_config(
    page_title="Лабораторен Софтуерен Център",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Стилизирано заглавие
st.title("🧪 Централен лабораторен панел")
st.subheader("Изберете необходимия софтуерен модул:")
st.divider()

# 2. Разпределяне на програмите в 3 колони за по-добра видимост
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 📊 Аналитичен софтуер")
    if st.button("📈 Box-Behnken Design", use_container_width=True):
        st.switch_page("pages/Box- benhken.py")
    
   
    
    # НОВИЯТ МОДУЛ
    if st.button("🧮 MS Calculator", use_container_width=True):
        st.switch_page("pages/MS Calculator.py")

with col2:
    st.markdown("### 🧪 Физикохимия")
    if st.button("💧 Surface Tension", use_container_width=True):
        st.switch_page("pages/Surface tension.py")
    
    if st.button("🌡️ Physico-chemical Params", use_container_width=True):
        st.switch_page("pages/Physico chemical parameters .py")
    
    if st.button("⚗️ TFC / TPC Analysis", use_container_width=True):
        st.switch_page("pages/TFC TPC.py")

with col3:
    st.markdown("### 📁 Протоколи")
    
    if st.button("📋 Protokol ALV", use_container_width=True):
        st.switch_page("pages/protokol alv.py")

st.divider()

# Долно каре с информация
st.info("💡 **Инструкция:** След като приключите работа с даден модул, можете да се върнете тук чрез менюто вляво.")
st.caption("Разработено за нуждите на лабораторията | 2024")
