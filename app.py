import streamlit as st
from PIL import Image
import numpy as np
import cv2
from datetime import datetime

st.set_page_config(page_title='Криптобот • Аналіз фото',page_icon='📈',layout='centered')
st.markdown('''<style>.stApp{background:radial-gradient(circle at top,#17301d,#070d0a 65%);color:#eefbea}.block-container{max-width:650px;padding-top:1rem}.brand{font-size:34px;font-weight:900;color:#a7ff3c}.card{border:1px solid #497a48;background:#101c13;border-radius:16px;padding:16px;margin:12px 0}.sig{font-size:45px;font-weight:900;text-align:center}</style>''',unsafe_allow_html=True)
st.markdown('<div class="brand">↗ КРИПТОБОТ</div><p>Автоматичний фотоаналіз свічок Pocket Option • українською</p>',unsafe_allow_html=True)
st.info('Це експериментальний аналіз видимих свічок, а не підключення до котирувань. Прогноз на 1 хвилину ненадійний; за нечітких даних бот обирає «ОЧІКУВАТИ».')
assets=['BTC/USD','ETH/USD','SOL/USD','AED/CNY OTC','KES/USD OTC','CHF/JPY OTC','AUD/CAD OTC','AUD/USD OTC','Інший актив']
asset=st.selectbox('Валютна пара',assets)
if asset=='Інший актив': asset=st.text_input('Назва активу')
duration=st.selectbox('Час прогнозу',['1 хв','3 хв','5 хв','15 хв'])
pic=st.file_uploader('📸 Завантажити скриншот свічкового графіка',type=['png','jpg','jpeg','webp'])

def analyze(img):
    # The input must contain a tight crop of a chart with green/red candles.
    rgb=np.asarray(img.convert('RGB'))
    h,w=rgb.shape[:2]
    scale=min(1.,900/max(h,w))
    if scale<1: rgb=cv2.resize(rgb,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA)
    hsv=cv2.cvtColor(rgb,cv2.COLOR_RGB2HSV)
    # Bright green and red candle bodies; avoid very dark chart lines.
    green=cv2.inRange(hsv,np.array([35,95,95]),np.array([90,255,255]))
    red=cv2.bitwise_or(cv2.inRange(hsv,np.array([0,105,100]),np.array([12,255,255])),cv2.inRange(hsv,np.array([170,105,100]),np.array([179,255,255])))
    mask=cv2.bitwise_or(green,red)
    hh,ww=mask.shape
    # Group adjacent pixels by x column and identify candle-like components.
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    comps=[]
    for c in contours:
        x,y,cw,ch=cv2.boundingRect(c)
        area=cv2.contourArea(c)
        if 2<=cw<=max(8,int(ww*.09)) and 5<=ch<=hh*.65 and area>=9 and ch/cw>=.65:
            patch_g=green[y:y+ch,x:x+cw]; patch_r=red[y:y+ch,x:x+cw]
            color='зелена' if cv2.countNonZero(patch_g)>cv2.countNonZero(patch_r) else 'червона'
            comps.append((x,y,cw,ch,color))
    comps.sort(key=lambda z:z[0])
    # Multiple colored fragments at the same x may be one candle; merge their extents.
    grouped=[]
    for c in comps:
        if grouped and abs((c[0]+c[2]/2)-grouped[-1]['x'])<max(4,ww*.012):
            g=grouped[-1];g['top']=min(g['top'],c[1]);g['bottom']=max(g['bottom'],c[1]+c[3]);g['colors'].append(c[4]);g['x']=(g['x']+c[0]+c[2]/2)/2
        else: grouped.append({'x':c[0]+c[2]/2,'top':c[1],'bottom':c[1]+c[3],'colors':[c[4]]})
    # Filter likely noise and insist on a reasonably large sample.
    grouped=[g for g in grouped if g['bottom']-g['top']>=6]
    recent=grouped[-min(12,len(grouped)):]
    if len(recent)<7: return 'ОЧІКУВАТИ','Замало чітко розпізнаних свічок (потрібно щонайменше 7).',len(recent),None
    xs=np.array([g['x'] for g in recent],dtype=float)
    ys=np.array([(g['top']+g['bottom'])/2 for g in recent],dtype=float)
    if np.ptp(xs)<ww*.09: return 'ОЧІКУВАТИ','Свічки розташовані надто щільно для оцінки.',len(recent),None
    # Slope in pixel coordinates; negative slope = upward price direction.
    slope=np.polyfit(xs,ys,1)[0]
    displacement=-slope*np.ptp(xs)
    threshold=max(14,hh*.065)
    colors=[max(set(g['colors']),key=g['colors'].count) for g in recent[-5:]]
    up=sum(c=='зелена' for c in colors);down=sum(c=='червона' for c in colors)
    if displacement>threshold and up>=4:
        return 'BUY','Видимі центри свічок підвищуються; переважають зелені свічки. Це лише умовна ознака, не прогноз із перевіреною точністю.',len(recent),displacement
    if displacement<-threshold and down>=4:
        return 'SELL','Видимі центри свічок знижуються; переважають червоні свічки. Це лише умовна ознака, не прогноз із перевіреною точністю.',len(recent),displacement
    return 'ОЧІКУВАТИ','Напрямок свічок не підтверджений або зображення містить неоднозначні елементи.',len(recent),displacement

if pic:
    im=Image.open(pic).convert('RGB')
    st.image(im,caption='Завантажене зображення',use_container_width=True)
    st.markdown('**Обріжте зображення до області свічок:** не включайте меню, кнопки, осцилятори, лінії інших індикаторів і написи. Для кращого результату використовуйте скриншот, а не фото монітора.')
    l,r=st.slider('Горизонтальні межі графіка (%)',0,100,(5,95))
    t,b=st.slider('Вертикальні межі графіка (%)',0,100,(10,85))
    box=(int(im.width*l/100),int(im.height*t/100),int(im.width*r/100),int(im.height*b/100))
    crop=im.crop(box)
    st.image(crop,caption='Область для аналізу',use_container_width=True)
    if st.button('🔎 АВТОМАТИЧНО АНАЛІЗУВАТИ',type='primary',use_container_width=True):
        sig,why,n,disp=analyze(crop)
        st.session_state['last']={'Час':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'Актив':asset,'Прогноз':duration,'Сигнал':sig,'Пояснення':why,'Розпізнано свічок':n}
if 'last' in st.session_state:
    result=st.session_state['last'];sig=result['Сигнал']
    color={'BUY':'#65ff71','SELL':'#ff766f','ОЧІКУВАТИ':'#f7dc70'}[sig]
    st.markdown(f'<div class="card"><div class="sig" style="color:{color}">{sig}</div><p>{result["Пояснення"]}</p><small>Розпізнано елементів: {result["Розпізнано свічок"]}. Відсоток успіху не розрахований.</small></div>',unsafe_allow_html=True)
    if st.button('💾 Зберегти результат'):
        st.session_state.setdefault('history',[]).append(result.copy())
        st.success('Збережено в історії цього сеансу.')
with st.expander('📚 Історія сигналів'):
    st.dataframe(st.session_state.get('history',[]),use_container_width=True)
    st.caption('Історія не зберігається після завершення сеансу. WIN/LOSS неможливо визначити з початкового фото.')
with st.expander('ℹ️ Обмеження'):
    st.write('Алгоритм розпізнає кольорові фрагменти, схожі на свічки. Інтерфейс, індикатори та кольорові лінії можуть бути помилково прийняті за свічки. Немає доступу до Pocket Option, біржових котирувань чи історії майбутніх цін. Сигнали не слід використовувати як єдину підставу для реальних угод.')
