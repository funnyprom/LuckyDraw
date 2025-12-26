# 📝 คู่มือการเพิ่มฟิลด์ในฐานข้อมูล

## วิธีที่ 1: ใช้ Flask-Migrate (แนะนำสำหรับ Production)

### 1. ติดตั้ง Flask-Migrate

```bash
pip install flask-migrate
```

### 2. เพิ่ม Flask-Migrate ใน requirements.txt

```
flask-migrate==4.0.5
```

### 3. แก้ไข app.py เพื่อเพิ่ม Flask-Migrate

```python
from flask_migrate import Migrate

# เพิ่มหลังจาก db = SQLAlchemy(app)
migrate = Migrate(app, db)
```

### 4. Initialize Migration (ทำครั้งเดียว)

```bash
flask db init
```

### 5. สร้าง Migration เมื่อเพิ่มฟิลด์ใหม่

```bash
flask db migrate -m "Add new field to Prize table"
```

### 6. Apply Migration

```bash
flask db upgrade
```

---

## วิธีที่ 2: ใช้ SQL ALTER TABLE (ง่ายและรวดเร็ว)

### ขั้นตอนการเพิ่มฟิลด์ใหม่:

#### 1. เพิ่มฟิลด์ใน Model (app.py)

ตัวอย่าง: เพิ่มฟิลด์ `price` ในตาราง `Prize`

```python
class Prize(db.Model):
    # ... ฟิลด์เดิม ...
    price = db.Column(db.Float, nullable=True)  # เพิ่มฟิลด์ใหม่
```

#### 2. สร้าง Script สำหรับ Migrate Database

สร้างไฟล์ `migrate_db.py`:

```python
from app import app, db
from sqlalchemy import text

def add_new_field():
    """เพิ่มฟิลด์ใหม่ในฐานข้อมูล"""
    with app.app_context():
        try:
            # เพิ่มคอลัมน์ใหม่ (ตัวอย่าง: เพิ่มฟิลด์ price ในตาราง prize)
            db.session.execute(text("""
                ALTER TABLE prize 
                ADD COLUMN price REAL
            """))
            db.session.commit()
            print("✅ เพิ่มฟิลด์สำเร็จ!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ เกิดข้อผิดพลาด: {e}")

if __name__ == '__main__':
    add_new_field()
```

#### 3. รัน Script

```bash
python migrate_db.py
```

---

## วิธีที่ 3: ใช้ SQLite Browser (สำหรับการทดสอบ)

1. เปิดไฟล์ `instance/lucky_draw.db` ด้วย DB Browser for SQLite
2. ไปที่แท็บ "Execute SQL"
3. รันคำสั่ง ALTER TABLE:

```sql
ALTER TABLE prize ADD COLUMN price REAL;
```

---

## ตัวอย่างการเพิ่มฟิลด์หลายฟิลด์พร้อมกัน

### ใน Model (app.py):

```python
class Prize(db.Model):
    # ... ฟิลด์เดิม ...
    
    # เพิ่มฟิลด์ใหม่
    price = db.Column(db.Float, nullable=True)
    category = db.Column(db.String(100), nullable=True)
    is_featured = db.Column(db.Boolean, default=False)
    expiry_date = db.Column(db.DateTime, nullable=True)
```

### ใน Script migrate_db.py:

```python
from app import app, db
from sqlalchemy import text

def add_new_fields():
    """เพิ่มฟิลด์ใหม่หลายฟิลด์ในฐานข้อมูล"""
    with app.app_context():
        try:
            # เพิ่มคอลัมน์ใหม่
            db.session.execute(text("""
                ALTER TABLE prize 
                ADD COLUMN price REAL;
            """))
            
            db.session.execute(text("""
                ALTER TABLE prize 
                ADD COLUMN category VARCHAR(100);
            """))
            
            db.session.execute(text("""
                ALTER TABLE prize 
                ADD COLUMN is_featured BOOLEAN DEFAULT 0;
            """))
            
            db.session.execute(text("""
                ALTER TABLE prize 
                ADD COLUMN expiry_date DATETIME;
            """))
            
            db.session.commit()
            print("✅ เพิ่มฟิลด์ทั้งหมดสำเร็จ!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ เกิดข้อผิดพลาด: {e}")

if __name__ == '__main__':
    add_new_fields()
```

---

## ⚠️ ข้อควรระวัง

1. **สำรองข้อมูลก่อน**: สำรองไฟล์ `instance/lucky_draw.db` ก่อนทำ migration
2. **ตรวจสอบชื่อตาราง**: SQLite ใช้ชื่อตารางเป็นตัวพิมพ์เล็ก (เช่น `prize` ไม่ใช่ `Prize`)
3. **Default Values**: ถ้าเพิ่มฟิลด์ NOT NULL ต้องระบุ default value
4. **Foreign Keys**: ถ้าเพิ่ม Foreign Key ต้องตรวจสอบว่าตารางที่อ้างอิงมีอยู่แล้ว

---

## 📋 ประเภทข้อมูลที่ใช้ได้

- `Integer` → `INTEGER`
- `String(n)` → `VARCHAR(n)`
- `Float` → `REAL`
- `Boolean` → `BOOLEAN` หรือ `INTEGER` (0/1)
- `DateTime` → `DATETIME`
- `Text` → `TEXT`

---

## 🔄 Rollback (ย้อนกลับ)

ถ้าต้องการลบฟิลด์ที่เพิ่มไป:

```sql
-- หมายเหตุ: SQLite ไม่รองรับ DROP COLUMN โดยตรง
-- ต้องสร้างตารางใหม่และคัดลอกข้อมูล
```

หรือใช้ Flask-Migrate:

```bash
flask db downgrade -1
```

