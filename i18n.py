from datetime import datetime

from PyQt6.QtCore import QDate, QLocale, QSettings, Qt
from PyQt6.QtWidgets import QInputDialog


LANGUAGES = {"English": "en_GB", "Magyar": "hu_HU", "العربية": "ar_EG"}
_language = "en"

# English source text | Hungarian | Arabic. Khalis Dawa is intentionally unchanged.
_catalog = r"""
Dashboard|Áttekintés|لوحة المعلومات
Batch Management|Készletek tételenként|إدارة دفعات المخزون
Purchasing|Beszerzés|المشتريات
Receive supplier deliveries and keep their complete history|Szállítói áruátvétel és teljes beszerzési előzmény|استلام توريدات الموردين والاحتفاظ بسجلها الكامل
Receive Stock|Áruátvétel|استلام المخزون
Purchase History|Beszerzési előzmények|سجل المشتريات
Suppliers|Beszállítók|الموردون
Add Supplier|Beszállító hozzáadása|إضافة مورد
Edit Supplier|Beszállító szerkesztése|تعديل المورد
+ Add Supplier|+ Új beszállító|+ إضافة مورد
Supplier|Beszállító|المورد
Supplier name|Beszállító neve|اسم المورد
Contact person|Kapcsolattartó|جهة الاتصال
Phone|Telefon|الهاتف
Email|E-mail|البريد الإلكتروني
Address|Cím|العنوان
Reference number|Hivatkozási szám|رقم المرجع
Supplier invoice or delivery note|Szállítói számla vagy szállítólevél|فاتورة المورد أو إشعار التسليم
Received date|Átvétel dátuma|تاريخ الاستلام
Received items|Átvett tételek|العناصر المستلمة
+ Add item|+ Tétel hozzáadása|+ إضافة عنصر
Unit cost (Ft)|Egységköltség (Ft)|تكلفة الوحدة (Ft)
Line total|Sorösszeg|إجمالي السطر
Notes|Megjegyzések|ملاحظات
Optional delivery notes|Opcionális szállítási megjegyzések|ملاحظات تسليم اختيارية
Receive delivery|Szállítmány átvétele|استلام التوريد
Search by supplier or reference...|Keresés beszállító vagy hivatkozás alapján...|البحث بالمورد أو الرقم المرجعي...
Search suppliers...|Beszállítók keresése...|البحث عن الموردين...
Received by|Átvevő|المستلم بواسطة
Select supplier|Válasszon beszállítót|اختر المورد
Select product|Válasszon terméket|اختر المنتج
Batch number|Tételszám|رقم الدفعة
Remove|Eltávolítás|إزالة
View|Megtekintés|عرض
Purchase details|Beszerzés részletei|تفاصيل الشراء
Delivery notes|Szállítási megjegyzések|ملاحظات التسليم
No delivery notes provided.|Nincs megadva szállítási megjegyzés.|لم يتم تقديم ملاحظات تسليم.
Purchase receipt was not found.|A beszerzési bizonylat nem található.|لم يتم العثور على إيصال الشراء.
Close|Bezárás|إغلاق
No received items found.|Nincsenek átvett tételek.|لم يتم العثور على عناصر مستلمة.
Purchase receipt P-{receipt:05d} was saved and stock was updated.|A P-{receipt:05d} beszerzési bizonylat mentve, a készlet frissítve.|تم حفظ إيصال الشراء P-{receipt:05d} وتحديث المخزون.
Delete Supplier|Beszállító törlése|حذف المورد
Delete supplier {name}?|Törli a(z) {name} beszállítót?|هل تريد حذف المورد {name}؟
Supplier name is required.|A beszállító neve kötelező.|اسم المورد مطلوب.
Supplier details are too long.|A beszállító adatai túl hosszúak.|بيانات المورد طويلة جدًا.
Enter a valid email address.|Adjon meg érvényes e-mail-címet.|أدخل عنوان بريد إلكتروني صالحًا.
Supplier was not found.|A beszállító nem található.|لم يتم العثور على المورد.
A supplier with this name already exists.|Már létezik ilyen nevű beszállító.|يوجد مورد بهذا الاسم بالفعل.
Supplier saved successfully.|A beszállító mentése sikeres.|تم حفظ المورد بنجاح.
Suppliers with purchase history cannot be deleted.|Beszerzési előzménnyel rendelkező beszállító nem törölhető.|لا يمكن حذف مورد لديه سجل مشتريات.
Supplier deleted successfully.|A beszállító törlése sikeres.|تم حذف المورد بنجاح.
Enter a purchase reference number.|Adjon meg beszerzési hivatkozási számot.|أدخل رقم مرجع الشراء.
Enter a valid received date.|Adjon meg érvényes átvételi dátumot.|أدخل تاريخ استلام صالحًا.
The received date cannot be in the future.|Az átvétel dátuma nem lehet jövőbeli.|لا يمكن أن يكون تاريخ الاستلام في المستقبل.
Add at least one received item.|Adjon hozzá legalább egy átvett tételt.|أضف عنصرًا مستلمًا واحدًا على الأقل.
Check the product, quantity, cost, and expiry date on every line.|Ellenőrizze minden sorban a terméket, mennyiséget, költséget és lejáratot.|تحقق من المنتج والكمية والتكلفة وتاريخ الصلاحية في كل سطر.
Every received item needs a batch number.|Minden átvett tételhez tételszám szükséges.|كل عنصر مستلم يحتاج إلى رقم دفعة.
Received quantities must be positive whole numbers.|Az átvett mennyiségnek pozitív egész számnak kell lennie.|يجب أن تكون الكميات المستلمة أعدادًا صحيحة موجبة.
Purchase costs must be positive with at most two decimal places.|A beszerzési költség legyen pozitív, legfeljebb két tizedesjeggyel.|يجب أن تكون تكلفة الشراء موجبة وبحد أقصى منزلتين عشريتين.
Batch expiry must be after the received date.|A tétel lejáratának az átvétel után kell lennie.|يجب أن يكون انتهاء صلاحية الدفعة بعد تاريخ الاستلام.
Choose a valid supplier.|Válasszon érvényes beszállítót.|اختر موردًا صالحًا.
This purchase reference already exists.|Ez a beszerzési hivatkozás már létezik.|مرجع الشراء هذا موجود بالفعل.
A selected product no longer exists.|A kiválasztott termék már nem létezik.|المنتج المحدد لم يعد موجودًا.
Batch number conflicts with existing product or expiry details.|A tételszám ütközik egy meglévő termék vagy lejárat adataival.|رقم الدفعة يتعارض مع بيانات منتج أو صلاحية موجودة.
Batch-based Inventory Management|Tételes készletkezelés|إدارة المخزون حسب الدفعة
Product Batch Manager|Készlettételek kezelése|إدارة دفعات المنتجات
Point of Sale|Pénztár|نقطة البيع
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
Use your Khalis Dawa account|Jelentkezzen be Khalis Dawa-fiókjába|سجّل الدخول بحسابك في Khalis Dawa
Staff-only access for administrators and pharmacists. Choose the account type above, then continue with your credentials.|Csak rendszergazdák és gyógyszerészek számára. Válassza ki a fióktípust, majd adja meg bejelentkezési adatait.|الدخول مخصص للمسؤولين والصيادلة. اختر نوع الحساب ثم أدخل بيانات تسجيل الدخول.
Switch to Pharmacist mode to create a pharmacist account.|Gyógyszerészi fiók létrehozásához váltson gyógyszerészi módra.|انتقل إلى وضع الصيدلي لإنشاء حساب صيدلي.
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
Fast movers|Gyorsan fogyó termékek|الأصناف سريعة الحركة
Slow movers|Lassan fogyó termékek|الأصناف بطيئة الحركة
Export report|Jelentés exportálása|تصدير التقرير
Export data|Adatok exportálása|تصدير البيانات
Merge data|Adatok egyesítése|دمج البيانات
Backup database|Adatbázis mentése|نسخ قاعدة البيانات احتياطيًا
Restore database|Adatbázis visszaállítása|استعادة قاعدة البيانات
SQLite Database (*.db)|SQLite-adatbázis (*.db)|قاعدة بيانات SQLite (*.db)
Database backup created successfully.|Az adatbázis biztonsági mentése elkészült.|تم إنشاء نسخة احتياطية لقاعدة البيانات بنجاح.
Database backup failed: {error}|Az adatbázis mentése sikertelen: {error}|فشل النسخ الاحتياطي لقاعدة البيانات: {error}
Restoring will replace the current database. A safety backup will be created and the application will close. Continue?|A visszaállítás lecseréli a jelenlegi adatbázist. Biztonsági mentés készül, majd az alkalmazás bezárul. Folytatja?|ستستبدل الاستعادة قاعدة البيانات الحالية. سيتم إنشاء نسخة أمان ثم إغلاق التطبيق. هل تريد المتابعة؟
Database restore failed: {error}|Az adatbázis visszaállítása sikertelen: {error}|فشلت استعادة قاعدة البيانات: {error}
Database restored successfully. Safety backup: {path}|Az adatbázis visszaállítása sikeres. Biztonsági mentés: {path}|تمت استعادة قاعدة البيانات بنجاح. نسخة الأمان: {path}
Pharmacy data|Gyógyszertári adatok|بيانات الصيدلية
No matching records.|Nincs találat.|لا توجد سجلات مطابقة.
No activity in this period|Nincs forgalom ebben az időszakban|لا يوجد نشاط في هذه الفترة
No sales activity in the last 30 days|Nem volt értékesítés az elmúlt 30 napban|لا توجد مبيعات خلال آخر 30 يومًا
Daily net sales - last 30 days|Napi nettó értékesítés – elmúlt 30 nap|صافي المبيعات اليومية - آخر 30 يومًا
Day|Nap|اليوم
Month|Hónap|الشهر
Net|Nettó|الصافي
Sold|Eladott mennyiség|الكمية المباعة
Returned|Visszaküldve|المرتجع
Refund|Visszatérítés|قيمة الاسترداد
Return ID|Visszáru azonosítója|رقم المرتجع
Receipt|Nyugta|الإيصال
Receipt ID|Nyugtaazonosító|رقم الإيصال
Available|Elérhető|المتاح
Minimum|Minimum|الحد الأدنى
Suggested order (units)|Javasolt rendelés (db)|الكمية المقترح طلبها
Recent sales|Közelmúltbeli értékesítés|المبيعات الأخيرة
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
+ Add Batch|+ Új tétel|+ إضافة دفعة
+ Add Product|+ Új termék|+ إضافة منتج
Cart|Kosár|السلة
Checkout|Fizetés|إتمام البيع
Empty Cart|Kosár ürítése|إفراغ السلة
Download|Letöltés|تنزيل
Return|Visszáru|إرجاع
Confirm|Megerősítés|تأكيد
Continue|Tovább|متابعة
Date|Dátum|التاريخ
Date returned|Visszaküldés dátuma|تاريخ الإرجاع
Name|Név|الاسم
Form|Forma|الشكل
Barcode|Vonalkód|الرمز الشريطي
Price|Ár|السعر
Role|Szerepkör|الدور
Description|Leírás|الوصف
Customer|Vásárló|العميل
SSN|Azonosító|رقم الهوية
Amount|Mennyiség|الكمية
Total|Összesen|الإجمالي
Items|Tételek|العناصر
Source sale|Eredeti eladás|البيع الأصلي
View and manage product records|Termékadatok megtekintése és kezelése|عرض سجلات المنتجات وإدارتها
Search products...|Termékek keresése...|البحث عن المنتجات...
All Categories|Minden kategória|كل الفئات
No products found|Nem található termék|لم يتم العثور على منتجات
No batches found|Nem található készlettétel|لم يتم العثور على دفعات
Search medicines...|Gyógyszerek keresése...|البحث عن الأدوية...
Search medicines by name or barcode|Keresés név vagy vonalkód alapján|البحث باسم الدواء أو الرمز الشريطي
Search products, add medicines to cart, and checkout|Keressen termékeket, tegye őket a kosárba, majd fizessen|ابحث عن المنتجات وأضف الأدوية إلى السلة ثم أكمل البيع
Requires prescription|Receptköteles|يتطلب وصفة طبية
Available: {value}|Elérhető: {value}|المتاح: {value}
{count} units|{count} db|{count} وحدة
Total: {amount} Ft|Összesen: {amount} Ft|الإجمالي: {amount} Ft
No medicines found|Nem található gyógyszer|لم يتم العثور على أدوية
Your cart is empty|A kosár üres|السلة فارغة
Select payment method|Fizetési mód kiválasztása|اختر طريقة الدفع
Cash|Készpénz|نقدًا
Card|Bankkártya|بطاقة
Customer details|Vásárló adatai|بيانات العميل
Customer name|Vásárló neve|اسم العميل
Customer SSN|Vásárló azonosítója|رقم هوية العميل
Pick items from these batches|Válasszon tételeket ezekből a készletekből|اختر العناصر من هذه الدفعات
Track sensitive medicine sales|Receptköteles gyógyszerek értékesítésének követése|تتبع مبيعات الأدوية الحساسة
Search by SSN, customer, or medicine...|Keresés azonosító, vásárló vagy gyógyszer alapján...|البحث برقم الهوية أو العميل أو الدواء...
No prescription-tracked sales found|Nem található receptköteles értékesítés|لم يتم العثور على مبيعات بوصفة طبية
View all completed sales|Befejezett értékesítések megtekintése|عرض جميع المبيعات المكتملة
Search by receipt ID...|Keresés nyugtaazonosító alapján...|البحث برقم الإيصال...
No sales found|Nem található értékesítés|لم يتم العثور على مبيعات
Return quantity|Visszáru mennyisége|كمية الإرجاع
Track completed returns and refund documents|Befejezett visszáruk és bizonylatok követése|تتبع المرتجعات المكتملة ومستندات الاسترداد
Search by return ID or sale receipt...|Keresés visszáru- vagy nyugtaazonosító alapján...|البحث برقم المرتجع أو إيصال البيع...
No returned items found|Nem található visszáru|لم يتم العثور على مرتجعات
Track actions performed by admins and pharmacists|Rendszergazdák és gyógyszerészek műveleteinek követése|تتبع إجراءات المسؤولين والصيادلة
Search by username, role, or action...|Keresés felhasználó, szerepkör vagy művelet alapján...|البحث باسم المستخدم أو الدور أو الإجراء...
No audit logs found|Nem található naplóbejegyzés|لم يتم العثور على سجلات تدقيق
Manage account passwords and access|Fiókjelszavak és hozzáférés kezelése|إدارة كلمات المرور والوصول
Password Management|Jelszókezelés|إدارة كلمات المرور
Select User|Felhasználó kiválasztása|اختر المستخدم
Admin Current Password|Rendszergazda jelenlegi jelszava|كلمة مرور المسؤول الحالية
Pharmacist Current Password|Gyógyszerész jelenlegi jelszava|كلمة مرور الصيدلي الحالية
New Password|Új jelszó|كلمة المرور الجديدة
Confirm New Password|Új jelszó megerősítése|تأكيد كلمة المرور الجديدة
Enter admin current password|Adja meg a rendszergazda jelenlegi jelszavát|أدخل كلمة مرور المسؤول الحالية
Enter pharmacist current password|Adja meg a gyógyszerész jelenlegi jelszavát|أدخل كلمة مرور الصيدلي الحالية
Enter new password|Adja meg az új jelszót|أدخل كلمة المرور الجديدة
Confirm new password|Erősítse meg az új jelszót|أكد كلمة المرور الجديدة
Update Password|Jelszó frissítése|تحديث كلمة المرور
Please fill in all fields|Töltse ki az összes mezőt|يرجى ملء جميع الحقول
New passwords do not match|Az új jelszavak nem egyeznek|كلمتا المرور الجديدتان غير متطابقتين
Password must be at least 4 characters long|A jelszónak legalább 4 karakter hosszúnak kell lennie|يجب ألا تقل كلمة المرور عن 4 أحرف
Selected user account not found|A kiválasztott felhasználó nem található|لم يتم العثور على حساب المستخدم المحدد
Admin current password is incorrect|A rendszergazda jelenlegi jelszava helytelen|كلمة مرور المسؤول الحالية غير صحيحة
Pharmacist current password is incorrect|A gyógyszerész jelenlegi jelszava helytelen|كلمة مرور الصيدلي الحالية غير صحيحة
Password updated successfully for {username}.|{username} jelszava sikeresen frissítve.|تم تحديث كلمة مرور {username} بنجاح.
Error|Hiba|خطأ
Warning|Figyelmeztetés|تحذير
Success|Siker|نجاح
Invalid username or password|Helytelen felhasználónév vagy jelszó|اسم المستخدم أو كلمة المرور غير صحيح
Please use Pharmacist mode for pharmacist accounts|Gyógyszerészi fiókhoz válassza a gyógyszerészi módot|استخدم وضع الصيدلي لحسابات الصيادلة
Please use Admin mode for admin account|Rendszergazdai fiókhoz válassza a rendszergazdai módot|استخدم وضع المسؤول لحساب المسؤول
Registration Failed|A regisztráció sikertelen|فشل التسجيل
Registration|Regisztráció|التسجيل
Confirm logout|Kijelentkezés megerősítése|تأكيد تسجيل الخروج
Are you sure you want to log out?|Biztosan ki szeretne jelentkezni?|هل تريد بالتأكيد تسجيل الخروج؟
Yes|Igen|نعم
No|Nem|لا
Expired|Lejárt|منتهي الصلاحية
Expiring soon|Hamarosan lejár|قريب الانتهاء
Good|Megfelelő|صالح
N/A|N/A|غير متاح
Export complete.|Az exportálás befejeződött.|اكتمل التصدير.
Import complete.|Az importálás befejeződött.|اكتمل الاستيراد.
Operation failed|A művelet sikertelen|فشلت العملية
{count} rows|{count} sor|{count} صف
USERNAME|FELHASZNÁLÓNÉV|اسم المستخدم
ROLE|SZEREPKÖR|الدور
DESCRIPTION|LEÍRÁS|الوصف
DATE|DÁTUM|التاريخ
MEDICINE|GYÓGYSZER|الدواء
CATEGORY|KATEGÓRIA|الفئة
BATCH|TÉTEL|الدفعة
STOCK|KÉSZLET|المخزون
UNIT PRICE|EGYSÉGÁR|سعر الوحدة
EXPIRY|LEJÁRAT|انتهاء الصلاحية
ACTIONS|MŰVELETEK|الإجراءات
NAME|NÉV|الاسم
FORM|FORMA|الشكل
BARCODE|VONALKÓD|الرمز الشريطي
PRICE|ÁR|السعر
MIN STOCK|MINIMUMKÉSZLET|الحد الأدنى للمخزون
RX|RECEPT|وصفة
AVAILABLE|ELÉRHETŐ|المتاح
RECEIPT ID|NYUGTAAZONOSÍTÓ|رقم الإيصال
ITEMS|TÉTELEK|العناصر
TOTAL|ÖSSZESEN|الإجمالي
PAYMENT|FIZETÉS|الدفع
REPORT|JELENTÉS|التقرير
SOURCE SALE|EREDETI ELADÁS|البيع الأصلي
DATE RETURNED|VISSZAKÜLDÉS DÁTUMA|تاريخ الإرجاع
User|Felhasználó|المستخدم
Product|Termék|المنتج
Min Required|Szükséges minimum|الحد الأدنى المطلوب
Expiry Date|Lejárati dátum|تاريخ انتهاء الصلاحية
Low Stock Products|Alacsony készletű termékek|منتجات منخفضة المخزون
Batches expiring within 30 days|30 napon belül lejáró tételek|دفعات تنتهي خلال 30 يومًا
No low stock products|Nincs alacsony készletű termék|لا توجد منتجات منخفضة المخزون
No batches expiring soon|Nincs hamarosan lejáró tétel|لا توجد دفعات قاربت على الانتهاء
All-time sales minus refunds|Összes értékesítés a visszatérítések levonásával|إجمالي المبيعات مطروحًا منه الاستردادات
Expired Batches|Lejárt tételek|الدفعات منتهية الصلاحية
Gross margin at the current selling price, before discounts|Bruttó árrés a jelenlegi eladási áron, kedvezmények előtt|هامش الربح الإجمالي بسعر البيع الحالي قبل الخصومات
Delete Batch|Tétel törlése|حذف الدفعة
Delete batch {batch} for {name}?|Törli a(z) {batch} tételt ehhez: {name}?|هل تريد حذف الدفعة {batch} للمنتج {name}؟
Invalid Product|Érvénytelen termék|منتج غير صالح
This product does not exist. Please add batches only for existing medicines.|Ez a termék nem létezik. Csak meglévő gyógyszerhez adjon tételt.|هذا المنتج غير موجود. أضف الدفعات للأدوية الموجودة فقط.
Add Batch Failed|A tétel hozzáadása sikertelen|فشلت إضافة الدفعة
Stock adjustment|Készletmódosítás|تعديل المخزون
Reason for changing stock (for example, damage or count correction):|A készletmódosítás oka (például sérülés vagy leltárkorrekció):|سبب تغيير المخزون (مثل التلف أو تصحيح العد):
Reason required|Indoklás szükséges|السبب مطلوب
Stock was not changed.|A készlet nem változott.|لم يتم تغيير المخزون.
Not saved|Nincs mentve|لم يتم الحفظ
This batch no longer exists.|Ez a tétel már nem létezik.|هذه الدفعة لم تعد موجودة.
Missing Data|Hiányzó adatok|بيانات ناقصة
Please fill in every required field.|Töltse ki az összes kötelező mezőt.|يرجى ملء جميع الحقول المطلوبة.
Invalid Data|Érvénytelen adat|بيانات غير صالحة
Quantity must be a valid non-negative number.|A mennyiség érvényes, nem negatív szám legyen.|يجب أن تكون الكمية رقمًا صالحًا غير سالب.
Invalid Date|Érvénytelen dátum|تاريخ غير صالح
Expiry date must be in YYYY-MM-DD format.|A lejárat formátuma ÉÉÉÉ-HH-NN legyen.|يجب أن يكون تاريخ الانتهاء بصيغة YYYY-MM-DD.
Batch Picking Instructions|Tételkiválasztási utasítások|تعليمات اختيار الدفعات
Confirm Checkout|Fizetés megerősítése|تأكيد إتمام البيع
Payment Method|Fizetési mód|طريقة الدفع
Select Quantity|Mennyiség kiválasztása|اختر الكمية
Decline|Elutasítás|رفض
Take {quantity} from batch {batch} (expires {expiry})|Vegyen ki {quantity} darabot a(z) {batch} tételből (lejár: {expiry})|خذ {quantity} من الدفعة {batch} (تنتهي في {expiry})
Stock Limit|Készletkorlát|حد المخزون
Only {count} non-expired unit(s) of {name} are available.|A(z) {name} termékből csak {count} nem lejárt darab érhető el.|يتوفر فقط {count} وحدة غير منتهية من {name}.
Cart Empty|A kosár üres|السلة فارغة
Please add medicines to the cart first.|Előbb tegyen gyógyszert a kosárba.|أضف الأدوية إلى السلة أولًا.
Customer Details Required|Vásárlói adatok szükségesek|بيانات العميل مطلوبة
Customer SSN and name are required because the cart contains prescription products.|A receptköteles termékek miatt a vásárló neve és azonosítója kötelező.|اسم العميل ورقم هويته مطلوبان لأن السلة تحتوي على أدوية بوصفة.
Incomplete Details|Hiányos adatok|بيانات غير مكتملة
Please provide both customer name and SSN, or decline.|Adja meg a vásárló nevét és azonosítóját, vagy utasítsa el.|أدخل اسم العميل ورقم هويته أو ارفض.
Invalid SSN|Érvénytelen azonosító|رقم هوية غير صالح
Customer SSN must contain 9 digits.|A vásárló azonosítója 9 számjegyből álljon.|يجب أن يتكون رقم هوية العميل من 9 أرقام.
Insufficient Stock|Nincs elegendő készlet|المخزون غير كافٍ
Checkout Failed|A fizetés sikertelen|فشل إتمام البيع
An unexpected error occurred while saving the sale:\n{error}|Váratlan hiba történt az értékesítés mentésekor:\n{error}|حدث خطأ غير متوقع أثناء حفظ البيع:\n{error}
Checkout Complete|Sikeres fizetés|اكتمل البيع
Sale saved and FEFO picking instructions confirmed.|Az értékesítés mentve, a FEFO-kiválasztás megerősítve.|تم حفظ البيع وتأكيد تعليمات اختيار FEFO.
The cart is already empty.|A kosár már üres.|السلة فارغة بالفعل.
Are you sure you want to remove all items from the cart?|Biztosan eltávolít minden tételt a kosárból?|هل تريد بالتأكيد إزالة جميع العناصر من السلة؟
Add Product|Termék hozzáadása|إضافة منتج
Edit Product|Termék szerkesztése|تعديل المنتج
Requires Prescription|Receptköteles|يتطلب وصفة طبية
Prescription|Recept|الوصفة الطبية
Delete Product|Termék törlése|حذف المنتج
Delete product {name}?|Törli ezt a terméket: {name}?|هل تريد حذف المنتج {name}؟
Product Deleted|Termék törölve|تم حذف المنتج
Add Product Failed|A termék hozzáadása sikertelen|فشلت إضافة المنتج
Update Product Failed|A termék frissítése sikertelen|فشل تحديث المنتج
Delete Failed|A törlés sikertelen|فشل الحذف
Please fill in all required fields.|Töltse ki az összes kötelező mezőt.|يرجى ملء جميع الحقول المطلوبة.
Invalid Barcode|Érvénytelen vonalkód|رمز شريطي غير صالح
Product barcode must contain digits only.|A vonalkód csak számjegyeket tartalmazhat.|يجب أن يحتوي الرمز الشريطي على أرقام فقط.
Selling price must be a valid non-negative number.|Az eladási ár érvényes, nem negatív szám legyen.|يجب أن يكون سعر البيع رقمًا صالحًا غير سالب.
Min stock must be a valid non-negative number.|A minimumkészlet érvényes, nem negatív szám legyen.|يجب أن يكون الحد الأدنى للمخزون رقمًا صالحًا غير سالب.
Choose an end date on or after the start date.|A zárónap nem lehet korábbi a kezdőnapnál.|اختر تاريخ نهاية يساوي تاريخ البداية أو يليه.
Could not load reports: {error}|A jelentések nem tölthetők be: {error}|تعذر تحميل التقارير: {error}
Excel Workbook (*.xlsx)|Excel-munkafüzet (*.xlsx)|مصنف Excel (*.xlsx)
Merge pharmacy data|Gyógyszertári adatok egyesítése|دمج بيانات الصيدلية
Add missing records from this workbook? Existing records will not be overwritten.|Hozzáadja a hiányzó rekordokat? A meglévő adatok nem íródnak felül.|هل تريد إضافة السجلات الناقصة؟ لن تتم الكتابة فوق السجلات الموجودة.
No changes made.|Nem történt változás.|لم يتم إجراء تغييرات.
Added: {added}\nAlready present: {skipped}|Hozzáadva: {added}\nMár létezett: {skipped}|تمت الإضافة: {added}\nموجود مسبقًا: {skipped}
Prescription Report|Receptjelentés|تقرير الوصفة الطبية
Prescription Report Downloaded|Receptjelentés letöltve|تم تنزيل تقرير الوصفة
Prescription report saved to Downloads as {filename}|A receptjelentés a Letöltések mappába került: {filename}|تم حفظ تقرير الوصفة في التنزيلات باسم {filename}
Date of Purchase|Vásárlás dátuma|تاريخ الشراء
Return Items|Tételek visszaküldése|إرجاع العناصر
Return items from {receipt}|Tételek visszaküldése erről a nyugtáról: {receipt}|إرجاع عناصر من الإيصال {receipt}
Sold on {sold}. Returns are allowed until {deadline}.|Eladás: {sold}. Visszáru eddig: {deadline}.|تم البيع في {sold}. الإرجاع متاح حتى {deadline}.
Process Return|Visszáru feldolgozása|معالجة الإرجاع
Access Denied|Hozzáférés megtagadva|تم رفض الوصول
Only administrators can delete sales history.|Csak rendszergazda törölhet értékesítési előzményt.|يمكن للمسؤولين فقط حذف سجل المبيعات.
Only administrators can delete returned items.|Csak rendszergazda törölhet visszárut.|يمكن للمسؤولين فقط حذف المرتجعات.
Delete Sale|Értékesítés törlése|حذف البيع
Delete Return|Visszáru törlése|حذف المرتجع
Are you sure you want to delete sale {receipt}?|Biztosan törli ezt az értékesítést: {receipt}?|هل تريد بالتأكيد حذف البيع {receipt}؟
Are you sure you want to delete return {receipt}?|Biztosan törli ezt a visszárut: {receipt}?|هل تريد بالتأكيد حذف المرتجع {receipt}؟
Sale Deleted|Értékesítés törölve|تم حذف البيع
Return Deleted|Visszáru törölve|تم حذف المرتجع
Return Window Closed|A visszáru-időszak lezárult|انتهت فترة الإرجاع
{receipt} can only be returned until {deadline}.|A(z) {receipt} nyugta csak eddig küldhető vissza: {deadline}.|يمكن إرجاع الإيصال {receipt} حتى {deadline} فقط.
Nothing Returnable|Nincs visszaküldhető tétel|لا توجد عناصر قابلة للإرجاع
All remaining sold units are already returned or expired.|Minden fennmaradó tételt visszaküldtek vagy lejárt.|تم إرجاع جميع الوحدات المتبقية أو انتهت صلاحيتها.
No Items Selected|Nincs kiválasztott tétel|لم يتم اختيار عناصر
Select at least one item quantity to return.|Válasszon ki legalább egy visszaküldendő mennyiséget.|اختر كمية عنصر واحد على الأقل للإرجاع.
Confirm Return|Visszáru megerősítése|تأكيد الإرجاع
Process return for {receipt}?\nRefund amount: {amount}|Feldolgozza a(z) {receipt} visszárut?\nVisszatérítés: {amount}|هل تريد معالجة إرجاع {receipt}؟\nمبلغ الاسترداد: {amount}
Return Failed|A visszáru sikertelen|فشل الإرجاع
Return Complete|Visszáru kész|اكتمل الإرجاع
Receipt Error|Nyugtahiba|خطأ في الإيصال
Sale receipt data could not be found.|A nyugta adatai nem találhatók.|تعذر العثور على بيانات إيصال البيع.
Receipt Downloaded|Nyugta letöltve|تم تنزيل الإيصال
Receipt saved to Downloads as {filename}|A nyugta a Letöltések mappába került: {filename}|تم حفظ الإيصال في التنزيلات باسم {filename}
Return Report Error|Visszárujelentés-hiba|خطأ في تقرير الإرجاع
Return report data could not be found.|A visszárujelentés adatai nem találhatók.|تعذر العثور على بيانات تقرير الإرجاع.
Return Report Downloaded|Visszárujelentés letöltve|تم تنزيل تقرير الإرجاع
Return report saved to Downloads as {filename}|A visszárujelentés a Letöltések mappába került: {filename}|تم حفظ تقرير الإرجاع في التنزيلات باسم {filename}
Payment Method|Fizetési mód|طريقة الدفع
Original Sale Date|Eredeti eladás dátuma|تاريخ البيع الأصلي
Processed By|Feldolgozta|تمت المعالجة بواسطة
No.|Ssz.|الرقم
Item|Tétel|العنصر
Unit Price|Egységár|سعر الوحدة
Subtotal|Részösszeg|المجموع الفرعي
Total Items Returned|Visszaküldött tételek száma|إجمالي العناصر المرتجعة
Original Sale Receipt|Eredeti nyugta|إيصال البيع الأصلي
Invoice|Számla|فاتورة
Pharmacy Receipt|Gyógyszertári nyugta|إيصال الصيدلية
Thank you for shopping with Khalis Dawa.|Köszönjük, hogy a Khalis Dawa gyógyszertárat választotta.|شكرًا لتسوقك من Khalis Dawa.
Returned Items Report|Visszárujelentés|تقرير العناصر المرتجعة
Refund total|Visszatérítés összesen|إجمالي المبلغ المسترد
{name} × {count}|{name} × {count}|{name} × {count}
Sold: {sold} • Already returned: {returned} • Available now: {available} • Unit price: {price}|Eladva: {sold} • Már visszaküldve: {returned} • Most elérhető: {available} • Egységár: {price}|المباع: {sold} • المرتجع سابقًا: {returned} • المتاح الآن: {available} • سعر الوحدة: {price}
{count} unit(s) can no longer be returned because they are expired.|{count} darab lejárat miatt már nem küldhető vissza.|لا يمكن إرجاع {count} وحدة لانتهاء صلاحيتها.
Export private pharmacy data|Bizalmas gyógyszertári adatok exportálása|تصدير بيانات الصيدلية الخاصة
Period|Időszak|الفترة
Inventory as of|Készlet dátuma|المخزون بتاريخ
"""

_strings = {}
for line in _catalog.strip().splitlines():
    if line.strip():
        en, hu, ar = (part.replace(r"\n", "\n") for part in line.split("|", 2))
        _strings[en.casefold()] = {"hu": hu, "ar": ar}


def language():
    return _language


def is_rtl():
    return _language == "ar"


def T(key):
    key = str(key)
    if _language == "en":
        return key
    translated = _strings.get(key.casefold(), {}).get(_language)
    if translated is not None:
        return translated
    if key.endswith(" (Ft)"):
        return T(key[:-5]) + " (Ft)"
    return key


def TF(key, **values):
    return T(key).format(**values)


def locale():
    return QLocale()


def format_date(value, long=False, include_time=False):
    if value in (None, ""):
        return "-"
    raw = str(value).strip()
    parsed = None
    for pattern in ("yyyy-MM-dd HH:mm:ss", "yyyy-MM-dd HH:mm", "yyyy-MM-dd"):
        candidate = QLocale.c().toDateTime(raw, pattern)
        if candidate.isValid():
            parsed = candidate
            break
    if parsed is None:
        try:
            native = datetime.fromisoformat(raw)
            parsed_date = QDate(native.year, native.month, native.day)
            text = locale().toString(
                parsed_date,
                QLocale.FormatType.LongFormat if long else QLocale.FormatType.ShortFormat,
            )
            return f"{text} {native:%H:%M}" if include_time or " " in raw else text
        except ValueError:
            return raw
    text = locale().toString(
        parsed.date(),
        QLocale.FormatType.LongFormat if long else QLocale.FormatType.ShortFormat,
    )
    if include_time or " " in raw:
        return f"{text} {locale().toString(parsed.time(), QLocale.FormatType.ShortFormat)}"
    return text


def format_current_date():
    return locale().toString(QDate.currentDate(), QLocale.FormatType.LongFormat)


def format_number(value, decimals=0):
    try:
        return locale().toString(float(value), "f", decimals)
    except (TypeError, ValueError):
        return str(value)


def format_money(value, decimals=2):
    return f"{format_number(value, decimals)} Ft"


def ltr_text(value):
    return f"\u2066{value}\u2069"


def force_ltr(widget, right=False):
    widget.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
    if hasattr(widget, "setAlignment"):
        widget.setAlignment(
            (Qt.AlignmentFlag.AlignRight if right else Qt.AlignmentFlag.AlignLeft)
            | Qt.AlignmentFlag.AlignVCenter
        )
    return widget


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
    locale_value = QLocale(LANGUAGES[name])
    _language = LANGUAGES[name][:2]
    QLocale.setDefault(locale_value)
    app.setLayoutDirection(
        Qt.LayoutDirection.RightToLeft if _language == "ar"
        else Qt.LayoutDirection.LeftToRight
    )
    return True
