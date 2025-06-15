from flask import Flask, request, jsonify, session, render_template
import google.generativeai as genai
import os
import uuid
from dotenv import load_dotenv
from training_data import TRAINING_DATA

# Загрузка настроек
load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default-secret-key')

# Настройка ИИ
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')  # Быстрая модель для чата

# Обучающие данные для специализации бота


# Построение промпта с контекстом и историей
def build_prompt(user_input, chat_history):
    # Системный промпт с ролью эксперта
    prompt = """Ты — персональный ИИ-помощник для мам, женщин, которые готовятся к беременности, вынашивают ребенка, воспитывает новорожденного, и всех, кто проходит эту жизнь стадии.  

---

## 🔹 Твоя главная цель:
- Поддерживать, помогать и информировать с помощью точных, практичных и легких для восприятия советов на русском языке.
- Распознавать контекст диалога, вопросы и потребности пользователя.
- Задавать точные вопросы, чтобы определить:
  - Беременна ли женщина и на какой стадии?
  - Рожала ли недавно?
  - Какие вопросы и трудности испытывает с новорожденными?
  - Какие меры нужно принять для повышения комфорта, спокойствия и уверенности (например, психологическая поддержка, направление к специалисту, подсказка по графику, подбор специалиста-няни)?

---

## 🔹 Главные правила:
✅ В ходе диалога всегда оставайся:
- Дружелюбным
- Чутким
- Профессионально точным
- Понятно излагающим информацию на русском языке
✅ Используй простой язык, избегай излишне технических выражений.
✅ Когда нужно — расскажи про юридические вопросы (например, оформление документов на ребенка, справки на Кыргызстан), про бюджет на услуги, про правила наблюдений у специалиста и график сдачи анализов.
✅ В критических случаях (например, температура у ребенка, сыпь, резкое ухудшение состояния) — порекомендуй сразу обратиться к врачу.

---

## 🔹 В ходе диалога:
1️⃣ Всё время учитывай контекст — что сказал собеседник до этого.
2️⃣ Задавай вопросы, чтобы точнее определить ситуацию.
3️⃣ Вноси эту информацию в “память сессии”.
4️⃣ Используй эту информацию, чтобы персонализировать ответы.

---

## 🔹 Расширенные возможности:
✅ Рекомендовать книги, потешки, колыбельные.
✅ Составлять график дня с учетом режима ребенка и потребностей мамы.
✅ В ходе диалога можешь дать подсказку по выбору специалиста, няни и других услуг.
✅ В психологическом плане — поддерживать, говорить тепло, помогать снять тревогу, дать точку опоры.

---

## 🔹 Итого:
Когда с тобою начинает говорить человек, главная твоая функция — точечно помогать на всех стадиях, что бы с ним ни произошло: до, вовремя и после появления ребенка.

---

Отвечай с помощью точных, легких для восприятия и психологически поддерживающих ответов на русском языке.
\n\n
"""
    
    # Добавляем обучающие примеры
    for example in TRAINING_DATA:
        prompt += f"Вопрос: {example['input']}\nОтвет: {example['output']}\n\n"
    
    # Добавляем историю диалога
    for msg in chat_history:
        if msg['sender'] == 'user':
            prompt += f"Вопрос: {msg['text']}\n"
        else:
            prompt += f"Ответ: {msg['text']}\n"
    
    # Добавляем текущий вопрос
    prompt += f"Вопрос: {user_input}\nОтвет:"
    return prompt

# Инициализация сессии
def setup_chat():
    if 'chat_history' not in session:
        session['chat_id'] = str(uuid.uuid4())
        session['chat_history'] = []
        print(f"🚀 Новый чат: {session['chat_id']}")

# Главная страница
@app.route('/')
def home():
    setup_chat()
    return render_template('chat.html')

# Обработка сообщений
@app.route('/chat', methods=['POST'])
def handle_message():
    setup_chat()
    user_input = request.json.get('message', '').strip()
    
    if not user_input:
        return jsonify({"error": "Сообщение не может быть пустым"}), 400
    
    try:
        chat_history = session['chat_history']
        
        # Формируем контекстный промпт
        prompt = build_prompt(user_input, chat_history[-4:])  # Берем последние 2 пары QA
        
        # Отправляем запрос
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.3)
        )
        ai_response = response.text
        
        # Обновляем историю
        chat_history.append({"sender": "user", "text": user_input})
        chat_history.append({"sender": "assistant", "text": ai_response})
        
        # Ограничиваем историю (последние 6 сообщений)
        session['chat_history'] = chat_history[-6:]
        
        return jsonify({"response": ai_response})
    
    except Exception as e:
        return jsonify({"error": f"Ошибка: {str(e)}"}), 500

# Сброс чата
@app.route('/reset', methods=['POST'])
def reset_chat():
    if 'chat_history' in session:
        session['chat_history'] = []
        print(f"♻️ Чат сброшен: {session['chat_id']}")
    return jsonify({"status": "История чата очищена"})

if __name__ == '__main__':
    app.run(debug=True)