from PyQt6.QtCore import QLocale, QSettings, Qt
from PyQt6.QtWidgets import QInputDialog

LANGUAGES = {"English": "en_GB", "Magyar": "hu_HU", "العربية": "ar_EG"}
_language = "en"

# English key | Hungarian | Arabic
_catalog = """
Dashboard|Áttekintés|لوحة المعلومات
Batch Management|Készletek tételenként|إدارة دفعات المخزون
Batch-based Inventory Management|Tételes készletkezelés|إدارة المخزون حسب الدفعة
Product Batch Manager|Készlettételek|دفعات المنتجات
Point of Sale|Pénztár|نقطة البيع
Product|Termék|المنتج
Products|Termékek|المنتجات
Prescriptions|Receptek|الوصفات الطبية
Sales History|Értékesítési előzmények|سجل المبيعات
Returned Items|Visszáruk|المرتجعات
Reports|Jelentések|التقارير
Audit Logs|Műveleti napló|سجل التدقيق
Settings|Beállítások|الإعدادات
Settings & profile|Beállítások és profil|الإعدادات والملف الشخصي
Logout|Kijelentkezés|تسجيل الخروج
Administrator Mode|Rendszergazdai mód|وضع المسؤول
Pharmacist Mode|Gyógyszerészi mód|وضع الصيدلي
Log in|Bejelentkezés|تسجيل الدخول
Use your Khalis Dawa account|Jelentkezzen be a Khalis Dawa-fiókjába|سجّل الدخول بحسابك في Khalis Dawa
Username|Felhasználónév|اسم المستخدم
Password|Jelszó|كلمة المرور
Admin|Rendszergazda|المسؤول
Pharmacist|Gyógyszerész|الصيدلي
Proceed|Belépés|دخول
Create account|Fiók létrehozása|إنشاء حساب
Home Page|Kezdőlap|الصفحة الرئيسية
Medicines|Gyógyszerek|الأدوية
Sales|Értékesítések|المبيعات
Expiration Alert|Lejárati figyelmeztetés|تنبيهات انتهاء الصلاحية
Low Stock|Alacsony készlet|مخزون منخفض
Revenue|Nettó árbevétel|صافي المبيعات
From|Kezdőnap|من
To|Zárónap|إلى
Receipts|Nyugták|الإيصالات
Gross sales|Bruttó értékesítés|إجمالي المبيعات
Refunds|Visszatérítések|المبالغ المستردة
Net sales|Nettó értékesítés|صافي المبيعات
Report|Jelentés|التقرير
Daily|Napi|يومي
Monthly|Havi|شهري
Payment|Fizetési mód|طريقة الدفع
Returns|Visszáruk|المرتجعات
Low stock now|Aktuális készlethiány|المخزون المنخفض حاليًا
Expiry now|Aktuális lejáratok|حالة الصلاحية الحالية
Export report|Jelentés exportálása|تصدير التقرير
Export data|Adatok exportálása|تصدير البيانات
Merge data|Adatok egyesítése|دمج البيانات
Pharmacy data|Gyógyszertári adatok|بيانات الصيدلية
No matching records.|Nincs találat.|لا توجد سجلات مطابقة.
Day|Nap|اليوم
Month|Hónap|الشهر
Net|Nettó|الصافي
Sold|Eladott mennyiség|الكمية المباعة
Returned|Visszaküldve|المرتجع
Refund|Visszatérítés|قيمة الاسترداد
Return ID|Visszáru azonosítója|رقم المرتجع
Receipt|Nyugta|الإيصال
Available|Elérhető|المتاح
Minimum|Minimum|الحد الأدنى
Suggested order (units)|Javasolt rendelés (db)|الكمية المقترح طلبها
Batch|Tétel|الدفعة
Expiry|Lejárat|انتهاء الصلاحية
Units|Darab|الوحدات
Status|Állapot|الحالة
Stock value|Készletérték|قيمة المخزون
Medicine|Gyógyszer|الدواء
Category|Kategória|الفئة
Stock|Készlet|المخزون
Buy / unit|Beszerzési egységár|تكلفة الوحدة
Sell / unit|Eladási egységár|سعر بيع الوحدة
Margin|Árrésszint|هامش الربح
Actions|Műveletek|الإجراءات
Purchase cost per unit (Ft)|Beszerzési egységár (Ft)|تكلفة شراء الوحدة (Ft)
Product selling price (Ft)|Termék eladási ára (Ft)|سعر بيع المنتج (Ft)
Min Stock|Minimumkészlet|الحد الأدنى للمخزون
Quantity|Mennyiség|الكمية
Edit|Szerkesztés|تعديل
Delete|Törlés|حذف
Cancel|Mégse|إلغاء
Save|Mentés|حفظ
Add|Hozzáadás|إضافة
+ Add Batch|+ Új tétel|إضافة دفعة
+ Add Product|+ Új termék|إضافة منتج
Cart|Kosár|السلة
Checkout|Fizetés|إتمام البيع
Empty Cart|Kosár ürítése|إفراغ السلة
Download|Letöltés|تنزيل
Return|Visszáru|إرجاع
Confirm|Megerősítés|تأكيد
Continue|Tovább|متابعة
Date|Dátum|التاريخ
Name|Név|الاسم
Barcode|Vonalkód|الرمز الشريطي
Price|Ár|السعر
Role|Szerepkör|الدور
Description|Leírás|الوصف
Customer|Vásárló|العميل
Amount|Mennyiség|الكمية
Total|Összesen|الإجمالي
"""
_strings = {}
for line in _catalog.strip().splitlines():
    en, hu, ar = line.split("|")
    _strings[en.casefold()] = {"hu": hu, "ar": ar}


def T(key):
    if _language == "en":
        return key
    translated = _strings.get(key.casefold(), {}).get(_language)
    if translated is not None:
        return translated
    if key.endswith(" (Ft)"):
        return T(key[:-5]) + " (Ft)"
    return key


def choose_language(app):
    global _language
    settings = QSettings("KhalisDawa", "Pharmacy")
    names = list(LANGUAGES)
    saved = settings.value("language", "English")
    default = names.index(saved) if saved in names else 0
    name, ok = QInputDialog.getItem(
        None, "Khalis Dawa", "Language / Nyelv / اللغة", names, default, False
    )
    if not ok:
        return False
    settings.setValue("language", name)
    locale = QLocale(LANGUAGES[name])
    _language = LANGUAGES[name][:2]
    QLocale.setDefault(locale)
    app.setLayoutDirection(
        Qt.LayoutDirection.RightToLeft if _language == "ar"
        else Qt.LayoutDirection.LeftToRight
    )
    return True