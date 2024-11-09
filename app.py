# app.py
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit
from datetime import datetime
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

active_users = {}  # {sid: {'nickname': nickname, 'blocked': set(), 'reported': set()}}
messages = {}      # {message_id: {'text': text, 'sender': sender, 'status': status}}

# 욕설 필터링
BAD_WORDS = {
    '시발', '씨발', 'ㅅㅂ', 'ㅆㅂ', '개새끼', '새끼', 'ㄱㅅㄲ', '지랄', 'ㅈㄹ',
    '병신', 'ㅂㅅ', '멍청이', '바보', '죽어', '등신', '미친', 'ㅁㅊ', '씨팔'
}

def filter_message(text):
    for word in BAD_WORDS:
        if word in text:
            text = text.replace(word, '*' * len(word))
    return text

@app.route('/')
def index():
    if 'nickname' not in session:
        return render_template('nickname.html')
    return render_template('chat.html')

@app.route('/check_nickname', methods=['POST'])
def check_nickname():
    nickname = request.json.get('nickname', '').strip()
    is_available = nickname not in [user.get('nickname', '') for user in active_users.values()]
    return jsonify({'available': is_available})

@app.route('/set_nickname', methods=['POST'])
def set_nickname():
    nickname = request.form.get('nickname', '').strip()
    if not nickname:
        return redirect(url_for('index'))
    
    if nickname in [user.get('nickname', '') for user in active_users.values()]:
        return render_template('nickname.html', error="이미 사용 중인 닉네임입니다.")
    
    session['nickname'] = nickname
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('nickname', None)
    return redirect(url_for('index'))

@socketio.on('connect')
def handle_connect():
    if 'nickname' not in session:
        return False
    
    active_users[request.sid] = {
        'nickname': session['nickname'],
        'blocked': set(),
        'reported': set()
    }
    emit('system_message', {
        'message': f'{session["nickname"]}님이 입장하셨습니다.',
        'type': 'info'
    }, broadcast=True)
    emit('user_count', {'count': len(active_users)}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in active_users:
        nickname = active_users[request.sid]['nickname']
        del active_users[request.sid]
        emit('system_message', {
            'message': f'{nickname}님이 퇴장하셨습니다.',
            'type': 'info'
        }, broadcast=True)
        emit('user_count', {'count': len(active_users)}, broadcast=True)

@socketio.on('message')
def handle_message(data):
    if 'nickname' not in session:
        return

    message_text = data.get('message', '').strip()
    filtered_text = filter_message(message_text)
    
    # 욕설이 감지된 경우
    if filtered_text != message_text:
        emit('system_message', {
            'message': '욕설이 감지되어 필터링되었습니다.',
            'type': 'warning'
        }, room=request.sid)

    message_id = f"{datetime.now().timestamp()}-{request.sid}"
    
    # 차단된 사용자를 제외한 수신자 목록
    recipients = [sid for sid, user in active_users.items()
                 if session['nickname'] not in user.get('blocked', set())]
    
    # 메시지 전송
    for recipient in recipients:
        emit('message', {
            'id': message_id,
            'message': filtered_text,
            'nickname': session['nickname'],
            'status': 'sent',
            'timestamp': str(datetime.now())
        }, room=recipient)

@socketio.on('block_user')
def handle_block(data):
    target_nickname = data.get('nickname')
    if request.sid in active_users and target_nickname:
        active_users[request.sid]['blocked'].add(target_nickname)
        emit('system_message', {
            'message': f'{target_nickname}님을 차단했습니다.',
            'type': 'warning'
        }, room=request.sid)

@socketio.on('report_user')
def handle_report(data):
    target_nickname = data.get('nickname')
    reason = data.get('reason', '사유 없음')
    if request.sid in active_users and target_nickname:
        active_users[request.sid]['reported'].add(target_nickname)
        emit('system_message', {
            'message': f'{target_nickname}님을 신고했습니다.',
            'type': 'warning'
        }, room=request.sid)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)