import streamlit as st

# Настройка на страницата
st.set_page_config(
    page_title="Лабораторен Софтуерен Портал",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Заглавие и стил
st.title("🧪 Централен портал за изчисления")
st.markdown("---")

# Добре дошли
st.subheader("Добре дошли в личната ви работна станция!")
st.write("""
Използвайте менюто вляво, за да изберете съответната програма. 
Всички инструменти за анализ и изчисления са събрани тук за по-бърза работа.
""")

# Визуално представяне на наличните модули (за ориентир)
col1, col2 = st.columns(2)

with col1:
    st.info("📊 **Аналитични модули:**")
    st.write("- Box-Behnken Design")
    st.write("- HPLC Database & Results")
    st.write("- MS App Analysis")

with col2:
    st.info("🧬 **Физикохимични модули:**")
    st.write("- Surface Tension (Повърхностно напрежение)")
    st.write("- TFC/TPC Изчисления")
    st.write("- Физикохимични параметри")

st.markdown("---")
st.caption("Система за автоматизация на лабораторни данни | Версия 1.0")