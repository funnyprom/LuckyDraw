"""
Script สำหรับเพิ่มฟิลด์ใหม่ในฐานข้อมูล
ใช้เมื่อต้องการเพิ่มฟิลด์ใหม่ในตารางที่มีอยู่แล้ว
"""
from app import app, db
from sqlalchemy import text

def add_new_field_to_prize():
    """
    ตัวอย่าง: เพิ่มฟิลด์ใหม่ในตาราง Prize
    แก้ไขส่วนนี้ตามฟิลด์ที่ต้องการเพิ่ม
    """
    with app.app_context():
        try:
            # ตัวอย่าง: เพิ่มฟิลด์ price ในตาราง prize
            # แก้ไข SQL ตามฟิลด์ที่ต้องการเพิ่ม
            
            # ตรวจสอบว่าฟิลด์มีอยู่แล้วหรือไม่
            result = db.session.execute(text("""
                PRAGMA table_info(prize);
            """))
            columns = [row[1] for row in result]
            
            # เพิ่มฟิลด์ price ถ้ายังไม่มี
            if 'price' not in columns:
                db.session.execute(text("""
                    ALTER TABLE prize 
                    ADD COLUMN price REAL;
                """))
                print("✅ เพิ่มฟิลด์ 'price' สำเร็จ!")
            else:
                print("ℹ️  ฟิลด์ 'price' มีอยู่แล้ว")
            
            # เพิ่มฟิลด์อื่นๆ ตามต้องการ
            # ตัวอย่าง: เพิ่มฟิลด์ category
            # if 'category' not in columns:
            #     db.session.execute(text("""
            #         ALTER TABLE prize 
            #         ADD COLUMN category VARCHAR(100);
            #     """))
            #     print("✅ เพิ่มฟิลด์ 'category' สำเร็จ!")
            
            db.session.commit()
            print("✅ Migration สำเร็จ!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ เกิดข้อผิดพลาด: {e}")
            import traceback
            traceback.print_exc()

def add_new_field_to_participant():
    """
    ตัวอย่าง: เพิ่มฟิลด์ใหม่ในตาราง Participant
    """
    with app.app_context():
        try:
            result = db.session.execute(text("""
                PRAGMA table_info(participant);
            """))
            columns = [row[1] for row in result]
            
            # ตัวอย่าง: เพิ่มฟิลด์ email
            # if 'email' not in columns:
            #     db.session.execute(text("""
            #         ALTER TABLE participant 
            #         ADD COLUMN email VARCHAR(200);
            #     """))
            #     print("✅ เพิ่มฟิลด์ 'email' สำเร็จ!")
            
            db.session.commit()
            print("✅ Migration สำเร็จ!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ เกิดข้อผิดพลาด: {e}")

if __name__ == '__main__':
    print("=" * 50)
    print("Database Migration Script")
    print("=" * 50)
    
    # เลือกฟังก์ชันที่ต้องการรัน
    # แก้ไขส่วนนี้ตามตารางที่ต้องการเพิ่มฟิลด์
    
    add_new_field_to_prize()
    # add_new_field_to_participant()
    
    print("=" * 50)
    print("เสร็จสิ้น!")

