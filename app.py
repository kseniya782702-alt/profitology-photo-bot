import streamlit as st
from PIL import Image
import numpy as np
from datetime import datetime

st.set_page_config(page_title='PROFITOLOGY • Фотоаналіз', page_icon='📈', layout='centered')
st.markdown('''<style>
.stApp{background:radial-gradient(circle at top,#17301d,#070d0a 60%);color:#edfbea}
.block-container{max-width:560px;padding-top:1rem}
.card{border:1px solid #3c6d43;background:#101c13;border-radius:18px;padding:20px;margin:12px 0;box-shadow:0 6px 28px #0006}
.brand{font-size:32px;font-weight:900;color:#a7ff3c;text-shadow:0 0 18px #59c81d55}
.subtitle{color:#c4d6c1;font-size:14px}
.buy{color:#76ff71;font-size:46px;font-weight:900;text-align:center}
.sell{color:#ff756c;font-size:46px;font-weight:900;text-align:center}
.wait{color:#f8dc67;font-size:46px;font-weight:900;text-align:center}
div.stButton>button[kind=primary]{background:#56e92e;color:#091307;border:0;font-weight:800}
[data-testid='stFileUploader']{border:1px solid #4c8645;border-radius:12px;padding:10px}
</style>''', unsafe_allow_html=True)
st.markdown('<div class="brand">↗ PROFITOLOGY</div><div class="subtitle">PHOTO BOT • Аналіз скриншотів Pocket Option • Демоверсія</div>', unsafe_allow_html=True)
with st.container():
    st.markdown('<div class="card"><b>📊 СИГНАЛИ ЗА ФОТО</b><br><span class="subtitle">Оберіть актив і додайте чіткий скриншот свічкового графіка. Не фотографуйте екран іншого пристрою, якщо можете зробити скриншот.</span></div>', unsafe_allow_html=True)
    assets=['BTC/USD','ETH/USD','SOL/USD','AED/CNY OTC','KES/USD OTC','CHF/JPY OTC','AUD/CAD OTC','AUD/USD OTC','Інший актив']
    asset=st.selectbox('Валютна пара',assets)
    if asset=='Інший актив': asset=st.text_input('Назва активу','')
    duration=st.selectbox('Експірація',['1 хв','3 хв','5 хв','15 хв'])
    pic=st.file_uploader('📷 Завантажити скриншот графіка',type=['png','jpg','jpeg','webp'])
    if pic:
        im=Image.open(pic).convert('RGB')
        st.image(im,caption=f'{asset} • скриншот для аналізу',use_container_width=True)
        st.info('Фото дозволяє оцінити лише видимий фрагмент графіка. Автоматична перевірка достовірності ціни, індикаторів та майбутнього результату недоступна.')
        trend=st.radio('Що видно на останніх 5–10 свічках?', ['Не можу визначити','Вищі максимуми й мінімуми (зростання)','Нижчі максимуми й мінімуми (падіння)','Боковий рух'],index=0)
        confirmation=st.checkbox('На скриншоті видно чіткий пробій рівня та його підтвердження')
        if st.button('⚡ АНАЛІЗУВАТИ',type='primary',use_container_width=True):
            # No pretend image recognition or fabricated confidence score.
            if confirmation and trend.startswith('Вищі'): signal='BUY'; css='buy'; why='Ви позначили висхідну структуру та підтверджений пробій.'
            elif confirmation and trend.startswith('Нижчі'): signal='SELL'; css='sell'; why='Ви позначили низхідну структуру та підтверджений пробій.'
            else: signal='WAIT'; css='wait'; why='Немає достатнього підтвердження напрямку за доступними даними.'
            st.session_state.result=(signal,css,why,asset,duration,datetime.now().strftime('%H:%M:%S'))
    if 'result' in st.session_state:
        sig,css,why,a,d,t=st.session_state.result
        st.markdown(f'<div class="card"><div class="subtitle">{a} • {d} • {t}</div><div class="{css}">{"↗" if sig=="BUY" else "↘" if sig=="SELL" else "◌"} {sig}</div><p>{why}</p><span class="subtitle">Попередня оцінка за введеними вами ознаками, не автоматичне розпізнавання свічок. Імовірність прибутку не розрахована.</span></div>',unsafe_allow_html=True)
        if st.button('Зберегти в історію'):
            st.session_state.setdefault('history',[]).append({'Час':t,'Актив':a,'Сигнал':sig,'Експірація':d,'Результат':'Не перевірено'})
            st.success('Додано до історії поточного сеансу')
    with st.expander('📚 Історія сигналів'):
        st.dataframe(st.session_state.get('history',[]),use_container_width=True)
        st.caption('WIN / LOSS не визначається за одним скриншотом. Для перевірки потрібна ціна після експірації.')
    with st.expander('👤 Профіль і пояснення'):
        st.write('Прототип інтерфейсу за вашим зразком. Це не офіційний продукт PROFITOLOGY чи Pocket Option і не підключається до рахунку. Сигнали — умовна інтерпретація ознак, які ви самі зазначили. Повноцінний автоматичний аналіз зображення потребує окремого модуля комп’ютерного зору та тестування.')
