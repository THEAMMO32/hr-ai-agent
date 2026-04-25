"""
HR AI Agent Dashboard for manual E2E testing.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from src.agent.core import HRAgent
from src.agent.state import agent_state
from config.settings import HR_TOPICS, USER_ROLES, RSS_SOURCES

st.set_page_config(page_title="HR AI Agent | E2E Validation", layout="wide")
st.title("🤖 HR AI Agent Dashboard")

# Инициализируем глобального агента (для тестов используем его же)
if "agent" not in st.session_state:
    st.session_state.agent = HRAgent()

agent = st.session_state.agent

tab1, tab2, tab3 = st.tabs(["🔥 Hot Topics", "📡 Источники", "📊 Качество"])

with tab1:
    st.subheader("Проактивные инсайты")
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("▶️ Запустить цикл анализа"):
            with st.spinner("Агент анализирует..."):
                result = agent.run_cycle()
                st.success(f"Новых элементов: {result['new_items']}")
    with col2:
        st.caption(f"Последняя проверка: {agent_state.state.get('last_check', '—')}")

    # 3–5 циклов для E2E (можно запустить несколько раз)
    insights = agent_state.get_recent_insights(5)
    if not insights:
        st.info("Нажмите «Запустить цикл анализа», чтобы получить инсайты.")
    for ins in insights:
        with st.expander(f"📌 {ins.get('topic_name', '')} — {ins.get('what_changed', '')[:80]}..."):
            st.markdown(f"**Что изменилось:** {ins.get('what_changed', '')}")
            st.markdown(f"**Почему важно:** {ins.get('why_important', '')}")
            st.markdown(f"**Рекомендация:** {ins.get('recommendation', '')}")
            st.caption(f"Риск: {ins.get('risk_level', '')} | Срочность: {ins.get('urgency', '')} | Источник: {ins.get('source_title', '—')}")

with tab2:
    st.subheader("Источники данных")
    st.write("Активные источники (из RSS_SOURCES):")
    # Для переключения используем чекбоксы; состояние можно сохранять в session_state
    for src in RSS_SOURCES:
        key = f"src_{src['name']}"
        if key not in st.session_state:
            st.session_state[key] = True
        active = st.checkbox(src["name"], value=st.session_state[key], key=src["url"])
        st.session_state[key] = active
    st.caption("Изменения сохраняются в сессии. Для постоянного сохранения можно записывать в state.json.")

    # Drill-in: показать последние наблюдения
    st.subheader("Последние наблюдения")
    observations = agent_state.state.get("observations", [])[-10:]
    if observations:
        df = pd.DataFrame(observations)
        st.dataframe(df[["title", "source", "risk_score"]].tail(5), use_container_width=True)
    else:
        st.info("Нет данных наблюдений.")

with tab3:
    st.subheader("Метрики качества")
    metrics = agent_state.state.get("metrics", {})
    col1, col2, col3 = st.columns(3)
    col1.metric("Всего наблюдений", len(agent_state.state.get("observations", [])))
    col2.metric("Инсайтов", metrics.get("total_insights_generated", 0))
    col3.metric("Аномалий", metrics.get("anomalies_detected", 0))
    st.metric("Обработанных URL", len(agent_state.state.get("processed_urls", [])))

    # Кнопка сброса для чистоты тестов
    if st.button("🔄 Сбросить состояние агента"):
        agent_state.reset()
        st.success("Состояние сброшено!")