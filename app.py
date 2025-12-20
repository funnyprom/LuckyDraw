from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import random
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lucky_draw.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'lucky_draw_secret_key_2024'
app.config['UPLOAD_FOLDER_PRIZES'] = 'static/uploads/prizes'
app.config['UPLOAD_FOLDER_PARTICIPANTS'] = 'static/uploads/participants'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# สร้าง folder สำหรับเก็บรูปภาพ
os.makedirs(app.config['UPLOAD_FOLDER_PRIZES'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER_PARTICIPANTS'], exist_ok=True)

db = SQLAlchemy(app)

# ==================== Authentication ====================

def login_required(f):
    """Decorator สำหรับหน้าที่ต้อง login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_type' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator สำหรับหน้าที่ต้องเป็น admin เท่านั้น"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_type' not in session:
            return redirect(url_for('login_page'))
        if session.get('user_type') != 'admin':
            return redirect(url_for('results_page'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== Models ====================
class User(db.Model):
    """ผู้ใช้งานระบบ"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    display_name = db.Column(db.String(100), nullable=True)
    user_type = db.Column(db.String(20), default='guest')  # admin หรือ guest
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Participant(db.Model):
    """รายชื่อคน (ผู้เข้าร่วม)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    image_path = db.Column(db.String(500), nullable=True)  # path ของรูปภาพผู้เข้าร่วม
    is_winner = db.Column(db.Boolean, default=False)
    prize_id = db.Column(db.Integer, db.ForeignKey('prize.id'), nullable=True)
    won_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    prize = db.relationship('Prize', backref='winner', foreign_keys=[prize_id])

class Prize(db.Model):
    """รายชื่อรางวัล (จัดเป็นหมวดหมู่)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    color = db.Column(db.String(20), default='#00d4ff')  # สีของรางวัล
    qr_code = db.Column(db.String(200), nullable=True)  # รหัส QR Code สำหรับค้นหา
    image_path = db.Column(db.String(500), nullable=True)  # path ของรูปภาพรางวัล
    is_grand = db.Column(db.Boolean, default=False)  # รางวัลใหญ่หรือไม่
    quantity = db.Column(db.Integer, default=1)  # จำนวนรางวัลทั้งหมด
    claimed_count = db.Column(db.Integer, default=0)  # จำนวนที่ถูกสุ่มไปแล้ว
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def remaining(self):
        """จำนวนรางวัลที่เหลือ"""
        return self.quantity - self.claimed_count
    
    @property
    def is_available(self):
        """ยังมีรางวัลเหลือหรือไม่"""
        return self.remaining > 0

class DrawHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    participant_name = db.Column(db.String(100), nullable=False)
    prize_name = db.Column(db.String(200), nullable=False)
    is_grand = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Helper functions
def allowed_file(filename):
    """ตรวจสอบว่าไฟล์ที่อัปโหลดเป็นประเภทที่อนุญาตหรือไม่"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Create tables and default admin user
with app.app_context():
    db.create_all()
    
    # สร้าง default admin ถ้ายังไม่มี
    if not User.query.filter_by(username='admin').first():
        default_admin = User(
            username='admin',
            display_name='Administrator',
            user_type='admin',
            is_active=True
        )
        default_admin.set_password('P@ssw0rd')
        db.session.add(default_admin)
        db.session.commit()

# ==================== Login/Logout Routes ====================
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    # ถ้า login แล้ว redirect ไปหน้าหลัก
    if 'user_type' in session:
        if session['user_type'] == 'admin':
            return redirect(url_for('spin_page'))
        else:
            return redirect(url_for('results_page'))
    
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        # ตรวจสอบจาก database
        user = User.query.filter_by(username=username, is_active=True).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_type'] = user.user_type
            session['username'] = user.display_name or user.username
            
            if user.user_type == 'admin':
                return redirect(url_for('spin_page'))
            else:
                return redirect(url_for('results_page'))
        else:
            error = 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง'
    
    return render_template('login.html', error=error)

@app.route('/login/guest', methods=['POST'])
def login_guest():
    session['user_type'] = 'guest'
    session['username'] = 'Guest'
    return redirect(url_for('results_page'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# ==================== Main Routes ====================
@app.route('/')
def index():
    if 'user_type' not in session:
        return redirect(url_for('login_page'))
    if session['user_type'] == 'admin':
        return redirect(url_for('spin_page'))
    return redirect(url_for('results_page'))

@app.route('/spin')
@admin_required
def spin_page():
    total_participants = Participant.query.count()  # ผู้เข้าร่วมทั้งหมด
    participants = Participant.query.filter_by(is_winner=False).all()  # ผู้รอลุ้นรางวัล
    
    # ดึงรางวัลที่ยังมีเหลือ (quantity > claimed_count)
    all_prizes = Prize.query.all()
    grand_prizes_db = [p for p in all_prizes if p.is_grand and p.remaining > 0]
    normal_prizes_db = [p for p in all_prizes if not p.is_grand and p.remaining > 0]
    
    # สี default สำหรับรางวัลที่ไม่มีสีกำหนด
    default_colors = ['#ff6b35', '#00d4ff', '#ff00ff', '#00ff88', '#ffd700', '#e91e63', '#9c27b0', '#2196f3']
    
    def get_color(prize, index, is_grand):
        color = prize.color
        if color and isinstance(color, str) and color.strip() and color.strip().lower() not in ['#000000', '#000', 'none', 'null', '']:
            return color.strip()
        return '#ffd700' if is_grand else default_colors[index % len(default_colors)]
    
    # รายการรางวัล (หมวดหมู่) พร้อมจำนวนที่เหลือ
    grand_prizes = [{
        'id': p.id, 
        'name': p.name, 
        'is_grand': p.is_grand, 
        'color': get_color(p, i, True),
        'qr_code': p.qr_code or '',
        'image_path': p.image_path or '',
        'quantity': p.quantity,
        'remaining': p.remaining
    } for i, p in enumerate(grand_prizes_db)]
    
    normal_prizes = [{
        'id': p.id, 
        'name': p.name, 
        'is_grand': p.is_grand, 
        'color': get_color(p, i, False),
        'qr_code': p.qr_code or '',
        'image_path': p.image_path or '',
        'quantity': p.quantity,
        'remaining': p.remaining
    } for i, p in enumerate(normal_prizes_db)]
    
    # รายชื่อผู้เข้าร่วม (สำหรับ wheel)
    participants_list = [{
        'id': p.id,
        'name': p.name,
        'image_path': p.image_path or ''
    } for p in participants]
    
    # นับจำนวนรางวัลทั้งหมดที่เหลือ
    total_grand_remaining = sum(p['remaining'] for p in grand_prizes)
    total_normal_remaining = sum(p['remaining'] for p in normal_prizes)
    
    return render_template('spin.html', 
                         total_participants=total_participants,
                         participants=participants_list,
                         grand_prizes=grand_prizes,
                         normal_prizes=normal_prizes,
                         total_grand_remaining=total_grand_remaining,
                         total_normal_remaining=total_normal_remaining)

@app.route('/results')
@login_required
def results_page():
    # ดึงประวัติการสุ่ม
    history = DrawHistory.query.order_by(DrawHistory.created_at.desc()).all()
    # ผู้ที่ยังไม่ได้รางวัล
    non_winners = Participant.query.filter_by(is_winner=False).all()
    # รางวัลที่ยังเหลือ (remaining > 0)
    all_prizes = Prize.query.all()
    unclaimed_prizes = [p for p in all_prizes if p.remaining > 0]
    
    # สร้าง dictionary สำหรับค้นหารูปภาพรางวัลจากชื่อรางวัลและประเภท
    # ใช้ชื่อรางวัลและ is_grand เป็น key
    prize_image_map = {}
    for prize in all_prizes:
        key = (prize.name, prize.is_grand)
        # ถ้ายังไม่มีใน map หรือมีรูปภาพ ให้อัปเดต
        if key not in prize_image_map:
            prize_image_map[key] = prize.image_path or ''
        elif prize.image_path and prize.image_path.strip():
            # ถ้ามีรูปภาพใหม่ ให้ใช้รูปภาพใหม่
            prize_image_map[key] = prize.image_path
    
    # สร้าง dictionary เพิ่มเติมจากผู้ชนะที่ยังมี prize_id
    winners = Participant.query.filter_by(is_winner=True).all()
    for winner in winners:
        if winner.prize_id:
            prize = Prize.query.get(winner.prize_id)
            if prize:
                key = (prize.name, prize.is_grand)
                if prize.image_path and prize.image_path.strip():
                    prize_image_map[key] = prize.image_path
    
    return render_template('results.html', 
                         history=history,
                         non_winners=non_winners,
                         unclaimed_prizes=unclaimed_prizes,
                         prize_image_map=prize_image_map)

@app.route('/admin')
@admin_required
def admin_page():
    participants = Participant.query.all()
    prizes = Prize.query.all()
    return render_template('admin.html', participants=participants, prizes=prizes)

@app.route('/static/uploads/prizes/<filename>')
def uploaded_prize_image(filename):
    """Serve uploaded prize images"""
    return send_from_directory(app.config['UPLOAD_FOLDER_PRIZES'], filename)

@app.route('/static/uploads/participants/<filename>')
def uploaded_participant_image(filename):
    """Serve uploaded participant images"""
    return send_from_directory(app.config['UPLOAD_FOLDER_PARTICIPANTS'], filename)

@app.route('/users')
@admin_required
def users_page():
    users = User.query.all()
    return render_template('users.html', users=users)

# ==================== API Routes - Participants ====================
@app.route('/api/participants', methods=['GET'])
@admin_required
def get_participants():
    participants = Participant.query.filter_by(is_winner=False).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'phone': p.phone,
        'image_path': p.image_path
    } for p in participants])

@app.route('/api/participants', methods=['POST'])
@admin_required
def add_participant():
    # รองรับทั้ง JSON และ FormData
    if request.is_json:
        data = request.json
        image_path = None
    else:
        data = request.form.to_dict()
        image_path = None
        
        # จัดการการอัปโหลดรูปภาพ
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # เพิ่ม timestamp เพื่อป้องกันชื่อไฟล์ซ้ำ
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = timestamp + filename
                filepath = os.path.join(app.config['UPLOAD_FOLDER_PARTICIPANTS'], filename)
                file.save(filepath)
                image_path = f'uploads/participants/{filename}'
    
    participant = Participant(
        name=data['name'],
        phone=data.get('phone', ''),
        image_path=image_path
    )
    db.session.add(participant)
    db.session.commit()
    return jsonify({'success': True, 'id': participant.id, 'image_path': image_path})

@app.route('/api/participants/<int:id>', methods=['DELETE'])
@admin_required
def delete_participant(id):
    participant = Participant.query.get_or_404(id)
    db.session.delete(participant)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/participants/bulk', methods=['POST'])
@admin_required
def add_bulk_participants():
    data = request.json
    names = data.get('names', [])
    count = 0
    for name in names:
        if name.strip():
            participant = Participant(name=name.strip())
            db.session.add(participant)
            count += 1
    db.session.commit()
    return jsonify({'success': True, 'count': count})

# ==================== API Routes - Prizes ====================
@app.route('/api/prizes', methods=['GET'])
@admin_required
def get_prizes():
    is_grand = request.args.get('is_grand', None)
    available_only = request.args.get('available', 'false') == 'true'
    
    query = Prize.query
    if is_grand is not None:
        query = query.filter_by(is_grand=is_grand == 'true')
    
    prizes = query.all()
    
    # กรองเฉพาะที่ยังมีเหลือ
    if available_only:
        prizes = [p for p in prizes if p.remaining > 0]
    
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'color': p.color,
        'qr_code': p.qr_code,
        'image_path': p.image_path,
        'is_grand': p.is_grand,
        'quantity': p.quantity,
        'claimed_count': p.claimed_count,
        'remaining': p.remaining
    } for p in prizes])

@app.route('/api/prizes', methods=['POST'])
@admin_required
def add_prize():
    # รองรับทั้ง JSON และ FormData
    if request.is_json:
        data = request.json
        image_path = None
    else:
        data = request.form.to_dict()
        image_path = None
        
        # จัดการการอัปโหลดรูปภาพ
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # เพิ่ม timestamp เพื่อป้องกันชื่อไฟล์ซ้ำ
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = timestamp + filename
                filepath = os.path.join(app.config['UPLOAD_FOLDER_PRIZES'], filename)
                file.save(filepath)
                image_path = f'uploads/prizes/{filename}'
    
    # แปลง string เป็น boolean และ int
    is_grand = data.get('is_grand', False)
    if isinstance(is_grand, str):
        is_grand = is_grand.lower() == 'true'
    
    quantity = data.get('quantity', 1)
    if isinstance(quantity, str):
        quantity = int(quantity) if quantity.isdigit() else 1
    
    prize = Prize(
        name=data['name'],
        description=data.get('description', ''),
        color=data.get('color', '#00d4ff'),
        qr_code=data.get('qr_code', ''),
        image_path=image_path,
        is_grand=is_grand,
        quantity=quantity
    )
    db.session.add(prize)
    db.session.commit()
    return jsonify({'success': True, 'id': prize.id, 'image_path': image_path})

@app.route('/api/prizes/<int:id>', methods=['PUT'])
@admin_required
def update_prize(id):
    prize = Prize.query.get_or_404(id)
    
    # รองรับทั้ง JSON และ FormData
    if request.is_json:
        data = request.json
        image_path = None
    else:
        data = request.form.to_dict()
        image_path = None
        
        # จัดการการอัปโหลดรูปภาพ
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                # ลบรูปเก่าถ้ามี
                if prize.image_path:
                    old_path = os.path.join('static', prize.image_path)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = timestamp + filename
                filepath = os.path.join(app.config['UPLOAD_FOLDER_PRIZES'], filename)
                file.save(filepath)
                image_path = f'uploads/prizes/{filename}'
    
    if 'name' in data:
        prize.name = data['name']
    if 'description' in data:
        prize.description = data['description']
    if 'color' in data:
        prize.color = data['color']
    if 'qr_code' in data:
        prize.qr_code = data['qr_code']
    if 'is_grand' in data:
        is_grand = data['is_grand']
        if isinstance(is_grand, str):
            is_grand = is_grand.lower() == 'true'
        prize.is_grand = is_grand
    if 'quantity' in data:
        quantity = data['quantity']
        if isinstance(quantity, str):
            quantity = int(quantity) if quantity.isdigit() else prize.quantity
        prize.quantity = quantity
    if image_path:
        prize.image_path = image_path
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/prizes/<int:id>', methods=['DELETE'])
@admin_required
def delete_prize(id):
    prize = Prize.query.get_or_404(id)
    db.session.delete(prize)
    db.session.commit()
    return jsonify({'success': True})

# ==================== API Routes - Spin ====================
@app.route('/api/spin', methods=['POST'])
@admin_required
def spin():
    """
    สุ่มหาผู้โชคดี - เลือกรางวัลก่อน แล้วค่อยสุ่มหาคน
    Input: prize_id (รางวัลที่เลือก), count (จำนวนผู้โชคดี)
    """
    data = request.json
    prize_id = data.get('prize_id')
    count = data.get('count', 1)
    
    if not prize_id:
        return jsonify({'error': 'กรุณาเลือกรางวัลก่อน'}), 400
    
    # หารางวัลที่เลือก
    prize = Prize.query.get(prize_id)
    if not prize:
        return jsonify({'error': 'ไม่พบรางวัลที่เลือก'}), 400
    
    # ตรวจสอบจำนวนรางวัลที่เหลือ
    if prize.remaining < count:
        return jsonify({'error': f'รางวัล "{prize.name}" เหลือไม่เพียงพอ (เหลือ {prize.remaining} รางวัล)'}), 400
    
    # หาผู้เข้าร่วมที่ยังไม่ได้รางวัล
    available_participants = Participant.query.filter_by(is_winner=False).all()
    
    if len(available_participants) < count:
        return jsonify({'error': f'มีผู้เข้าร่วมไม่เพียงพอ (เหลือ {len(available_participants)} คน)'}), 400
    
    # สุ่มผู้โชคดี
    winners = random.sample(available_participants, count)
    
    results = []
    for winner in winners:
        winner.is_winner = True
        winner.prize_id = prize.id
        winner.won_at = datetime.utcnow()
        
        # เพิ่มจำนวนที่ถูกสุ่มไป
        prize.claimed_count += 1
        
        # บันทึกประวัติ
        history = DrawHistory(
            participant_name=winner.name,
            prize_name=prize.name,
            is_grand=prize.is_grand
        )
        db.session.add(history)
        
        results.append({
            'winner_id': winner.id,
            'winner_name': winner.name,
            'prize_id': prize.id,
            'prize_name': prize.name,
            'is_grand': prize.is_grand
        })
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'results': results,
        'prize_remaining': prize.remaining
    })

@app.route('/api/reset', methods=['POST'])
@admin_required
def reset_all():
    # รีเซ็ตผู้เข้าร่วม
    Participant.query.update({
        'is_winner': False,
        'prize_id': None,
        'won_at': None
    })
    # รีเซ็ตรางวัล (claimed_count กลับเป็น 0)
    Prize.query.update({
        'claimed_count': 0
    })
    # ลบประวัติ
    DrawHistory.query.delete()
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/clear-all', methods=['POST'])
@admin_required
def clear_all():
    Participant.query.delete()
    Prize.query.delete()
    DrawHistory.query.delete()
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/clear-participants', methods=['POST'])
@admin_required
def clear_participants():
    Participant.query.delete()
    DrawHistory.query.delete()
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/clear-prizes', methods=['POST'])
@admin_required
def clear_prizes():
    Prize.query.delete()
    DrawHistory.query.delete()
    db.session.commit()
    return jsonify({'success': True})

# ==================== API Routes - Users ====================
@app.route('/api/users', methods=['GET'])
@admin_required
def get_users():
    users = User.query.all()
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'display_name': u.display_name,
        'user_type': u.user_type,
        'is_active': u.is_active,
        'created_at': u.created_at.isoformat() if u.created_at else None
    } for u in users])

@app.route('/api/users', methods=['POST'])
@admin_required
def add_user():
    data = request.json
    
    # ตรวจสอบว่า username ซ้ำหรือไม่
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'ชื่อผู้ใช้นี้มีอยู่แล้ว'}), 400
    
    user = User(
        username=data['username'],
        display_name=data.get('display_name', ''),
        user_type=data.get('user_type', 'guest'),
        is_active=data.get('is_active', True)
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    return jsonify({'success': True, 'id': user.id})

@app.route('/api/users/<int:id>', methods=['GET'])
@admin_required
def get_user(id):
    user = User.query.get_or_404(id)
    return jsonify({
        'id': user.id,
        'username': user.username,
        'display_name': user.display_name,
        'user_type': user.user_type,
        'is_active': user.is_active
    })

@app.route('/api/users/<int:id>', methods=['PUT'])
@admin_required
def update_user(id):
    user = User.query.get_or_404(id)
    data = request.json
    
    # ตรวจสอบว่า username ซ้ำหรือไม่ (ยกเว้นตัวเอง)
    if 'username' in data and data['username'] != user.username:
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'ชื่อผู้ใช้นี้มีอยู่แล้ว'}), 400
        user.username = data['username']
    
    if 'display_name' in data:
        user.display_name = data['display_name']
    
    if 'user_type' in data:
        user.user_type = data['user_type']
    
    if 'is_active' in data:
        user.is_active = data['is_active']
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/users/<int:id>/password', methods=['PUT'])
@admin_required
def change_user_password(id):
    user = User.query.get_or_404(id)
    data = request.json
    
    if 'password' not in data or len(data['password']) < 4:
        return jsonify({'error': 'รหัสผ่านต้องมีอย่างน้อย 4 ตัวอักษร'}), 400
    
    user.set_password(data['password'])
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/users/<int:id>', methods=['DELETE'])
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)
    
    # ป้องกันการลบ admin คนสุดท้าย
    if user.user_type == 'admin':
        admin_count = User.query.filter_by(user_type='admin', is_active=True).count()
        if admin_count <= 1:
            return jsonify({'error': 'ไม่สามารถลบ Admin คนสุดท้ายได้'}), 400
    
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
