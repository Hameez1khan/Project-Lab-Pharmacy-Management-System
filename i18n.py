from datetime import datetime
import re

from PyQt6.QtCore import QDate, QLocale, QSettings, Qt


LANGUAGES = {"English": "en_GB", "Magyar": "hu_HU", "العربية": "ar_EG"}
_language = "en"

# English source text | Hungarian | Arabic. Khalis Dawa is intentionally unchanged.
_catalog = r"""
Dashboard|Áttekintés|لوحة المعلومات
Purchase Cost|Beszerzési költség|تكلفة الشراء
PURCHASE COST|BESZERZÉSI KÖLTSÉG|تكلفة الشراء
SELLING PRICE|ELADÁSI ÁR|سعر البيع
Purchase cost must be a valid positive number.|A beszerzési költségnek érvényes pozitív számnak kell lennie.|يجب أن تكون تكلفة الشراء رقمًا موجبًا صالحًا.
Working...|Folyamatban...|جارٍ التنفيذ...
Exporting pharmacy data...|Gyógyszertári adatok exportálása...|جارٍ تصدير بيانات الصيدلية...
Merging pharmacy data...|Gyógyszertári adatok egyesítése...|جارٍ دمج بيانات الصيدلية...
WORKSPACE|MUNKATERÜLET|مساحة العمل
INVENTORY|KÉSZLET|المخزون
INSIGHTS|ELEMZÉSEK|التحليلات
OK|Rendben|آمن
FEFO inventory|FEFO-készletkezelés|مخزون وفق الأقرب انتهاءً
Audit history|Naplóelőzmények|سجل التدقيق
Local database|Helyi adatbázis|قاعدة بيانات محلية
Pharmacy operations workspace|Gyógyszertári munkaterület|مساحة عمل عمليات الصيدلية
Overview|Áttekintés|نظرة عامة
My workspace|Munkaterületem|مساحة عملي
A clear picture of pharmacy operations|A gyógyszertári működés áttekintése|صورة واضحة لعمليات الصيدلية
Everything needed for today's shift|Minden, ami a mai műszakhoz szükséges|كل ما يلزم لوردية اليوم
New sale|Új értékesítés|عملية بيع جديدة
Review batches|Tételek áttekintése|مراجعة الدفعات
View reports|Jelentések megtekintése|عرض التقارير
View prescriptions|Receptek megtekintése|عرض الوصفات
Sales history|Értékesítési előzmények|سجل المبيعات
Recent transactions|Legutóbbi tranzakciók|أحدث المعاملات
No recent transactions.|Nincsenek legutóbbi tranzakciók.|لا توجد معاملات حديثة.
Sales Today|Mai értékesítések|مبيعات اليوم
Prescriptions Today|Mai receptek|وصفات اليوم
Returns Today|Mai visszáruk|مرتجعات اليوم
A little help?|Segítségre van szüksége?|هل تحتاج إلى مساعدة؟
Use search and filters to find records quickly.|A keresővel és a szűrőkkel gyorsan megtalálhatja a rekordokat.|استخدم البحث وعوامل التصفية للعثور على السجلات بسرعة.
Previous|Előző|السابق
Next|Következő|التالي
Showing {first}-{last} of {total}|{first}-{last} / {total} megjelenítve|عرض {first}-{last} من {total}
Page {page} of {pages}|{page}. / {pages} oldal|الصفحة {page} من {pages}
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
Lead time|Szállítási idő|مهلة التوريد
Created by|Létrehozta|أنشأه
 days| nap| يومًا
 Ft| Ft| Ft
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
Purchase Order Details|Beszerzési rendelés részletei|تفاصيل أمر الشراء
Order notes|Rendelési megjegyzések|ملاحظات الطلب
Related receipts|Kapcsolódó bizonylatok|الإيصالات المرتبطة
No order notes provided.|Nincsenek rendelési megjegyzések.|لم يتم تقديم ملاحظات للطلب.
No receipts recorded.|Nincsenek rögzített bizonylatok.|لا توجد إيصالات مسجلة.
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
Welcome back|Üdvözöljük újra|مرحبًا بعودتك
A healthier way to run your pharmacy.|A gyógyszertár működtetésének egészségesebb módja.|طريقة أفضل لإدارة صيدليتك.
Connected inventory. Confident dispensing. More time for the people who need you.|Összekapcsolt készlet. Magabiztos kiadás. Több idő azokra, akiknek szükségük van Önre.|مخزون مترابط، وصرف آمن، ووقت أطول لمن يحتاجون إليك.
Secure pharmacy workspace|Biztonságos gyógyszertári munkatér|مساحة عمل آمنة للصيدلية
Sign in to continue to your workspace|Jelentkezzen be a munkaterület folytatásához|سجّل الدخول للمتابعة إلى مساحة العمل
Show password|Jelszó megjelenítése|إظهار كلمة المرور
Hide password|Jelszó elrejtése|إخفاء كلمة المرور
Language|Nyelv|اللغة
Remembered on this device|Az eszköz megjegyzi|يتم تذكره على هذا الجهاز
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
Add Batch|Tétel hozzáadása|إضافة دفعة
Edit Batch|Tétel szerkesztése|تعديل الدفعة
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
SSN and name are required because the cart contains prescription products.|A receptköteles termékek miatt az azonosító és a vásárló neve kötelező.|رقم الهوية واسم العميل مطلوبان لأن السلة تحتوي على منتجات بوصفة طبية.
Customer can share SSN and name, or decline for non-prescription purchases.|A vásárló megadhatja az azonosítóját és nevét, vagy elutasíthatja ezt a nem receptköteles vásárlásnál.|يمكن للعميل مشاركة رقم الهوية والاسم أو الرفض للمشتريات التي لا تتطلب وصفة طبية.
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
POS Performance|Pénztári teljesítmény|أداء نقطة البيع
Measured checkout and interaction times from this device|Ezen az eszközön mért fizetési és interakciós idők|أوقات إتمام البيع والتفاعل المقاسة على هذا الجهاز
Last 7 days|Elmúlt 7 nap|آخر 7 أيام
Last 30 days|Elmúlt 30 nap|آخر 30 يومًا
Last 90 days|Elmúlt 90 nap|آخر 90 يومًا
Last 365 days|Elmúlt 365 nap|آخر 365 يومًا
Refresh|Frissítés|تحديث
Checkout attempts|Fizetési kísérletek|محاولات إتمام البيع
Success rate|Sikerességi arány|معدل النجاح
Median checkout|Medián fizetési idő|الوقت الوسيط لإتمام البيع
95th percentile|95. percentilis|المئين الخامس والتسعون
Median processing|Medián feldolgozási idő|متوسط وقت المعالجة
Processing P95|Feldolgozási P95|المئين 95 للمعالجة
Sale saved and FEFO picking instructions confirmed. Total: {total}|Az eladás mentve, a FEFO kiadási utasítások jóváhagyva. Összesen: {total}|تم حفظ البيع وتأكيد تعليمات الصرف وفق FEFO. الإجمالي: {total}
Successful: {success} \| Failed: {failed} \| Cancelled: {cancelled}|Sikeres: {success} \| Sikertelen: {failed} \| Megszakítva: {cancelled}|ناجح: {success} \| فاشل: {failed} \| ملغى: {cancelled}
Operation|Művelet|العملية
Phase|Fázis|المرحلة
Type|Típus|النوع
Count|Darabszám|العدد
Average (ms)|Átlag (ms)|المتوسط (مللي ثانية)
Minimum (ms)|Minimum (ms)|الحد الأدنى (مللي ثانية)
Maximum (ms)|Maximum (ms)|الحد الأقصى (مللي ثانية)
Median (ms)|Medián (ms)|الوسيط (مللي ثانية)
P95 (ms)|P95 (ms)|المئين 95 (مللي ثانية)
Failed|Sikertelen|فاشل
processing|Feldolgozás|المعالجة
interaction|Interakció|التفاعل
processing_total|Teljes feldolgozási idő|إجمالي وقت المعالجة
interaction_total|Teljes interakciós idő|إجمالي وقت التفاعل
total_system_checkout|Teljes rendszeroldali fizetési idő|إجمالي وقت إتمام البيع في النظام
checkout|Fizetés|إتمام البيع
search|Keresés|البحث
product_lookup|Termékkeresés|البحث عن المنتج
cart_availability|Kosár és készlet ellenőrzése|التحقق من السلة والمخزون
prescription_check|Vénykötelezettség ellenőrzése|التحقق من الوصفة الطبية
customer_details|Vásárlói adatok|بيانات العميل
fefo_allocation|FEFO készletkiosztás|تخصيص المخزون وفق FEFO
batch_confirmation|Tételkiosztás jóváhagyása|تأكيد اختيار الدفعات
payment_selection|Fizetési mód kiválasztása|اختيار طريقة الدفع
transaction|Adatbázis-tranzakció|معاملة قاعدة البيانات
inventory_deduction|Készletcsökkentés|خصم المخزون
receipt_generation|Bizonylat összeállítása|إنشاء الإيصال
receipt_summary|Bizonylatösszesítő összeállítása|إعداد ملخص الإيصال
post_checkout_refresh|Eladás utáni frissítés|التحديث بعد إتمام البيع
New Purchase Order|Új beszerzési rendelés|أمر شراء جديد
Edit Purchase Order|Beszerzési rendelés szerkesztése|تعديل أمر الشراء
Purchase Orders|Beszerzési rendelések|أوامر الشراء
Reorder Suggestions|Újrarendelési javaslatok|اقتراحات إعادة الطلب
Draft|Piszkozat|مسودة
Pending|Függőben|قيد الانتظار
Ordered|Megrendelve|تم الطلب
Partially received|Részben átvéve|مستلم جزئيًا
Fully received|Teljesen átvéve|مستلم بالكامل
Cancelled|Törölve|ملغى
All statuses|Minden állapot|جميع الحالات
Order date|Rendelés dátuma|تاريخ الطلب
Expected delivery|Várható szállítás|التسليم المتوقع
Order items|Rendelési tételek|عناصر الطلب
Optional order notes|Opcionális rendelési megjegyzések|ملاحظات طلب اختيارية
Save Purchase Order|Beszerzési rendelés mentése|حفظ أمر الشراء
Receive Purchase Order|Beszerzési rendelés átvétele|استلام أمر الشراء
Receive {number}|{number} átvétele|استلام {number}
Outstanding|Fennmaradó|المتبقي
Receive now|Átvétel most|الاستلام الآن
Receive selected quantities|Kiválasztott mennyiségek átvétele|استلام الكميات المحددة
Search by order number or supplier...|Keresés rendelésszám vagy beszállító alapján...|البحث برقم الطلب أو المورد...
+ New Purchase Order|+ Új beszerzési rendelés|+ أمر شراء جديد
Order number|Rendelésszám|رقم الطلب
Expected|Várható|المتوقع
Received|Átvett|المستلم
Total cost|Összköltség|التكلفة الإجمالية
Recalculate|Újraszámítás|إعادة الحساب
Create Draft Order|Piszkozat létrehozása|إنشاء طلب مسودة
{days} days|{days} nap|{days} يومًا
Sales period|Értékesítési időszak|فترة المبيعات
Safety stock days|Biztonsági készlet napjai|أيام مخزون الأمان
Select|Kiválasztás|تحديد
Movement|Forgási sebesség|حركة المخزون
Daily sales|Napi értékesítés|المبيعات اليومية
Usable stock|Felhasználható készlet|المخزون القابل للاستخدام
Outstanding PO|Függő rendelés|طلبات الشراء المعلقة
Reorder point|Újrarendelési pont|نقطة إعادة الطلب
Suggested|Javasolt|المقترح
Order quantity|Rendelendő mennyiség|كمية الطلب
Calculation|Számítás|الحساب
The selected database file does not exist.|A kiválasztott adatbázisfájl nem létezik.|ملف قاعدة البيانات المحدد غير موجود.
Choose a different file for the backup.|Válasszon másik fájlt a biztonsági mentéshez.|اختر ملفًا مختلفًا للنسخة الاحتياطية.
The selected file is already the active database.|A kiválasztott fájl már az aktív adatbázis.|الملف المحدد هو قاعدة البيانات النشطة بالفعل.
The selected file is not a valid SQLite database.|A kiválasztott fájl nem érvényes SQLite-adatbázis.|الملف المحدد ليس قاعدة بيانات SQLite صالحة.
Registration has been completed.|A regisztráció befejeződött.|اكتمل التسجيل.
Batch added successfully.|A tétel sikeresen hozzáadva.|تمت إضافة الدفعة بنجاح.
Product added successfully.|A termék sikeresen hozzáadva.|تمت إضافة المنتج بنجاح.
Product updated successfully.|A termék sikeresen frissítve.|تم تحديث المنتج بنجاح.
Product deleted successfully.|A termék sikeresen törölve.|تم حذف المنتج بنجاح.
Return deleted successfully.|A visszáru sikeresen törölve.|تم حذف المرتجع بنجاح.
Sale deleted successfully.|Az értékesítés sikeresen törölve.|تم حذف البيع بنجاح.
Password is required.|A jelszó kötelező.|كلمة المرور مطلوبة.
Days must be between 1 and 366.|A napok száma 1 és 366 közötti legyen.|يجب أن يكون عدد الأيام بين 1 و366.
Days must be a whole number.|A napok száma egész szám legyen.|يجب أن يكون عدد الأيام عددًا صحيحًا.
Username and password are required.|A felhasználónév és a jelszó kötelező.|اسم المستخدم وكلمة المرور مطلوبان.
This username already exists.|Ez a felhasználónév már létezik.|اسم المستخدم هذا موجود بالفعل.
Password must be at least 4 characters long.|A jelszónak legalább 4 karakter hosszúnak kell lennie.|يجب ألا تقل كلمة المرور عن 4 أحرف.
Current password is incorrect.|A jelenlegi jelszó helytelen.|كلمة المرور الحالية غير صحيحة.
Selected user account not found.|A kiválasztott felhasználói fiók nem található.|لم يتم العثور على حساب المستخدم المحدد.
Product does not exist in the products table.|A termék nem szerepel a terméktáblában.|المنتج غير موجود في جدول المنتجات.
Batch number already exists.|A tételszám már létezik.|رقم الدفعة موجود بالفعل.
Enter a positive purchase cost with at most two decimal places.|Adjon meg pozitív beszerzési költséget, legfeljebb két tizedesjeggyel.|أدخل تكلفة شراء موجبة بحد أقصى منزلتين عشريتين.
Supplier lead time must be a whole number of days.|A szállítási idő egész számú nap legyen.|يجب أن تكون مهلة المورد عددًا صحيحًا من الأيام.
Supplier lead time must be between 0 and 365 days.|A szállítási idő 0 és 365 nap közötti legyen.|يجب أن تكون مهلة المورد بين 0 و365 يومًا.
Suppliers with purchase orders cannot be deleted.|Beszerzési rendeléssel rendelkező beszállító nem törölhető.|لا يمكن حذف مورد لديه أوامر شراء.
Purchase order was not found.|A beszerzési rendelés nem található.|لم يتم العثور على أمر الشراء.
The receipt supplier does not match the purchase order.|A bizonylat beszállítója nem egyezik a beszerzési rendeléssel.|مورد الإيصال لا يطابق أمر الشراء.
Only ordered or partially received orders can be received.|Csak megrendelt vagy részben átvett rendelés vehető át.|يمكن استلام الطلبات المطلوبة أو المستلمة جزئيًا فقط.
Every received line must belong to the purchase order.|Minden átvett sornak a beszerzési rendeléshez kell tartoznia.|يجب أن ينتمي كل سطر مستلم إلى أمر الشراء.
A received line does not match the purchase order.|Egy átvett sor nem egyezik a beszerzési rendeléssel.|أحد الأسطر المستلمة لا يطابق أمر الشراء.
Received quantity exceeds the outstanding order quantity.|Az átvett mennyiség meghaladja a rendelés fennmaradó mennyiségét.|الكمية المستلمة تتجاوز الكمية المتبقية في الطلب.
Purchase order quantities changed. Refresh and try again.|A rendelési mennyiségek megváltoztak. Frissítsen, majd próbálja újra.|تغيرت كميات أمر الشراء. حدّث الصفحة وحاول مرة أخرى.
Add at least one purchase order item.|Adjon hozzá legalább egy rendelési tételt.|أضف عنصرًا واحدًا على الأقل إلى أمر الشراء.
Check the product, quantity, and cost on every order line.|Ellenőrizze minden rendelési sor termékét, mennyiségét és költségét.|تحقق من المنتج والكمية والتكلفة في كل سطر طلب.
Each product can appear only once on a purchase order.|Egy termék csak egyszer szerepelhet a beszerzési rendelésen.|يمكن أن يظهر كل منتج مرة واحدة فقط في أمر الشراء.
Ordered quantities must be positive whole numbers.|A rendelt mennyiségek pozitív egész számok legyenek.|يجب أن تكون الكميات المطلوبة أعدادًا صحيحة موجبة.
Enter valid order and expected delivery dates.|Adjon meg érvényes rendelési és várható szállítási dátumot.|أدخل تاريخ طلب وتاريخ تسليم متوقع صالحين.
Expected delivery cannot be before the order date.|A várható szállítás nem lehet korábbi a rendelés dátumánál.|لا يمكن أن يكون التسليم المتوقع قبل تاريخ الطلب.
New purchase orders must be draft or pending.|Az új beszerzési rendelés állapota piszkozat vagy függőben lehet.|يجب أن تكون أوامر الشراء الجديدة مسودة أو قيد الانتظار.
Purchase order notes are too long.|A beszerzési rendelés megjegyzése túl hosszú.|ملاحظات أمر الشراء طويلة جدًا.
Only draft or pending purchase orders can be edited.|Csak piszkozat vagy függőben lévő rendelés szerkeszthető.|يمكن تعديل أوامر الشراء المسودة أو قيد الانتظار فقط.
Invalid purchase order status.|Érvénytelen beszerzési rendelési állapot.|حالة أمر الشراء غير صالحة.
This purchase order status change is not allowed.|Ez a rendelési állapotváltoztatás nem engedélyezett.|تغيير حالة أمر الشراء هذا غير مسموح.
A purchase order with received stock cannot be cancelled.|Átvett készlettel rendelkező beszerzési rendelés nem mondható le.|لا يمكن إلغاء أمر شراء تم استلام مخزون منه.
Sales period and safety stock must be whole numbers of days.|Az értékesítési időszak és a biztonsági készlet napjai egész számok legyenek.|يجب أن تكون فترة المبيعات وأيام مخزون الأمان أعدادًا صحيحة.
Sales period must be 7, 30, 60, or 90 days.|Az értékesítési időszak 7, 30, 60 vagy 90 nap lehet.|يجب أن تكون فترة المبيعات 7 أو 30 أو 60 أو 90 يومًا.
Safety stock days must be between 0 and 365.|A biztonsági készlet napjai 0 és 365 között legyenek.|يجب أن تكون أيام مخزون الأمان بين 0 و365.
Select at least one recommendation with a positive quantity.|Válasszon ki legalább egy pozitív mennyiségű javaslatot.|حدد اقتراحًا واحدًا على الأقل بكمية موجبة.
A product with this name already exists.|Már létezik ilyen nevű termék.|يوجد منتج بهذا الاسم بالفعل.
This barcode already exists.|Ez a vonalkód már létezik.|هذا الرمز الشريطي موجود بالفعل.
Product not found.|A termék nem található.|لم يتم العثور على المنتج.
Sale not found.|Az értékesítés nem található.|لم يتم العثور على البيع.
Return record not found.|A visszáru bejegyzése nem található.|لم يتم العثور على سجل المرتجع.
This sale already has processed returns and can no longer be deleted.|Ehhez az értékesítéshez már tartozik feldolgozott visszáru, ezért nem törölhető.|لهذا البيع مرتجعات معالجة بالفعل ولا يمكن حذفه.
Select at least one item to return.|Válasszon ki legalább egy visszaküldendő tételt.|حدد عنصرًا واحدًا على الأقل للإرجاع.
One of the selected sale items could not be found.|Az egyik kiválasztott értékesítési tétel nem található.|تعذر العثور على أحد عناصر البيع المحددة.
Customer SSN and name are required for prescription medicines.|Receptköteles gyógyszernél a vásárló neve és azonosítója kötelező.|رقم هوية العميل واسمه مطلوبان للأدوية الموصوفة.
The start date must not follow the end date.|A kezdőnap nem lehet későbbi a zárónapnál.|يجب ألا يكون تاريخ البداية بعد تاريخ النهاية.
Administrator access required.|Rendszergazdai hozzáférés szükséges.|يلزم وصول المسؤول.
Formulas are not allowed in a data workbook.|Képletek nem engedélyezettek az adatmunkafüzetben.|الصيغ غير مسموح بها في مصنف البيانات.
Use text for dates, codes and names.|A dátumokat, kódokat és neveket szövegként adja meg.|استخدم النص للتواريخ والرموز والأسماء.
Missing workbook manifest.|Hiányzik a munkafüzet jegyzéke.|بيان المصنف مفقود.
Not a pharmacy data workbook.|Ez nem gyógyszertári adatmunkafüzet.|هذا ليس مصنف بيانات صيدلية.
The workbook is missing required data worksheets.|A munkafüzetből hiányoznak kötelező adatlapok.|يفتقد المصنف أوراق البيانات المطلوبة.
Missing or unexpected worksheet.|Hiányzó vagy váratlan munkalap.|ورقة عمل مفقودة أو غير متوقعة.
Invalid manifest.|Érvénytelen jegyzék.|بيان غير صالح.
Expected a whole number.|Egész szám szükséges.|يجب إدخال عدد صحيح.
Expected a finite amount.|Véges számérték szükséges.|يجب إدخال مبلغ محدود.
Missing, invalid or repeated record ID.|Hiányzó, érvénytelen vagy ismétlődő rekordazonosító.|معرف سجل مفقود أو غير صالح أو مكرر.
Invalid quantity.|Érvénytelen mennyiség.|كمية غير صالحة.
Unexpected account role.|Váratlan fiókszerepkör.|دور حساب غير متوقع.
Separate sales histories cannot safely be matched by receipt number.|Külön értékesítési előzmények nem egyeztethetők biztonságosan nyugtaszám alapján.|لا يمكن مطابقة سجلات مبيعات منفصلة بأمان باستخدام رقم الإيصال.
Invalid audit snapshot.|Érvénytelen napló-pillanatkép.|لقطة تدقيق غير صالحة.
Purchase order {number} was saved.|A(z) {number} beszerzési rendelés mentve.|تم حفظ أمر الشراء {number}.
Supplier: {supplier}|Beszállító: {supplier}|المورد: {supplier}
Status: {status}|Állapot: {status}|الحالة: {status}
Expected delivery: {date}|Várható szállítás: {date}|التسليم المتوقع: {date}
Draft purchase order {number} was created.|A(z) {number} beszerzési rendelés piszkozata létrejött.|تم إنشاء مسودة أمر الشراء {number}.
Cancel Purchase Order|Beszerzési rendelés törlése|إلغاء أمر الشراء
Cancel purchase order {number}?|Törli a(z) {number} beszerzési rendelést?|هل تريد إلغاء أمر الشراء {number}؟
{product}: ordered {ordered}, received {received}, outstanding {outstanding}|{product}: rendelt {ordered}, átvett {received}, fennmaradó {outstanding}|{product}: المطلوب {ordered}، المستلم {received}، المتبقي {outstanding}
This order has no outstanding items.|Ennek a rendelésnek nincs fennmaradó tétele.|لا يحتوي هذا الطلب على عناصر متبقية.
Receipts:|Bizonylatok:|الإيصالات:
{reference} on {date}|{reference}, {date}|{reference} بتاريخ {date}
Submit|Beküldés|إرسال
Mark Ordered|Megrendeltnek jelölés|تحديد كمطلوب
Receive|Átvétel|استلام
Reference|Hivatkozás|المرجع
No sales history|Nincs értékesítési előzmény|لا يوجد سجل مبيعات
{sold} sold / {period} days; target {target}; usable {usable}; outstanding {outstanding}.|{sold} eladva / {period} nap; célkészlet {target}; használható {usable}; függő rendelés {outstanding}.|تم بيع {sold} خلال {period} يومًا؛ المخزون المستهدف {target}؛ المتاح {usable}؛ الطلبات المعلقة {outstanding}.
{sold} sold / {period} days = {daily} per day; lead time {lead} days + safety {safety} days; reorder point {point}; target {target}; usable {usable}; outstanding {outstanding}; suggested {suggested}.|{sold} eladás / {period} nap = napi {daily}; szállítás {lead} nap + biztonság {safety} nap; újrarendelési pont {point}; cél {target}; használható {usable}; függő {outstanding}; javasolt {suggested}.|تم بيع {sold} خلال {period} يومًا = {daily} يوميًا؛ مهلة {lead} أيام + أمان {safety} أيام؛ نقطة إعادة الطلب {point}؛ الهدف {target}؛ المتاح {usable}؛ المعلق {outstanding}؛ المقترح {suggested}.
Fast-moving|Gyorsan fogyó|سريع الحركة
Slow-moving|Lassan fogyó|بطيء الحركة
Updated password for {username}|{username} jelszava frissítve|تم تحديث كلمة مرور {username}
Added supplier {name}|{name} beszállító hozzáadva|تمت إضافة المورد {name}
Updated supplier {name}|{name} beszállító frissítve|تم تحديث المورد {name}
Deleted supplier {name}|{name} beszállító törölve|تم حذف المورد {name}
Received purchase {reference} from {supplier} ({quantity} units)|A(z) {reference} beszerzés átvéve ettől: {supplier} ({quantity} egység)|تم استلام المشتريات {reference} من {supplier} ({quantity} وحدة)
Created purchase order {number} for {supplier}|A(z) {number} beszerzési rendelés létrehozva: {supplier}|تم إنشاء أمر الشراء {number} للمورد {supplier}
Updated purchase order {number} for {supplier}|A(z) {number} beszerzési rendelés frissítve: {supplier}|تم تحديث أمر الشراء {number} للمورد {supplier}
Changed purchase order {number} from {old_status} to {new_status}|A(z) {number} rendelés állapota megváltozott: {old_status} → {new_status}|تم تغيير حالة أمر الشراء {number} من {old_status} إلى {new_status}
Added product {name}|{name} termék hozzáadva|تمت إضافة المنتج {name}
Updated product {name}|{name} termék frissítve|تم تحديث المنتج {name}
Deleted product {name}|{name} termék törölve|تم حذف المنتج {name}
Added batch {batch} for {product}|A(z) {batch} tétel hozzáadva ehhez: {product}|تمت إضافة الدفعة {batch} للمنتج {product}
Updated batch {batch} for {product}|A(z) {batch} tétel frissítve ehhez: {product}|تم تحديث الدفعة {batch} للمنتج {product}
Deleted batch {batch} for {product}|A(z) {batch} tétel törölve ehhez: {product}|تم حذف الدفعة {batch} للمنتج {product}
Carried out item return for {product} x{quantity} from {receipt}|{product} x{quantity} visszáru feldolgozva innen: {receipt}|تم تنفيذ إرجاع {product} x{quantity} من {receipt}
Deleted return {return_receipt} for {sale_receipt}|A(z) {return_receipt} visszáru törölve ehhez: {sale_receipt}|تم حذف المرتجع {return_receipt} للبيع {sale_receipt}
Sold {product} x{quantity}|Eladva: {product} x{quantity}|تم بيع {product} x{quantity}
Deleted sale {receipt}|A(z) {receipt} eladás törölve|تم حذف البيع {receipt}
Created from replenishment recommendations|Készletpótlási javaslatokból létrehozva|تم الإنشاء من توصيات تجديد المخزون
"""

def _split_catalog_line(line):
    return [
        part.replace(r"\|", "|").replace(r"\n", "\n")
        for part in re.split(r"(?<!\\)\|", line, maxsplit=2)
    ]


def _parse_catalog(catalog):
    strings = {}
    folded_strings = {}
    for line_number, line in enumerate(catalog.strip().splitlines(), 1):
        if not line.strip():
            continue
        parts = _split_catalog_line(line)
        if len(parts) != 3:
            raise ValueError(f"Malformed translation catalog line {line_number}")
        en, hu, ar = parts
        if en in strings:
            raise ValueError(f"Duplicate translation key on line {line_number}: {en}")
        translations = {"hu": hu, "ar": ar}
        strings[en] = translations
        folded_strings.setdefault(en.casefold(), translations)
    return strings, folded_strings


_strings, _folded_strings = _parse_catalog(_catalog)


def language():
    return _language


def is_rtl():
    return _language == "ar"


def T(key):
    key = str(key)
    if _language == "en":
        return key
    translations = _strings.get(key)
    if translations is None:
        translations = _folded_strings.get(key.casefold(), {})
    translated = translations.get(_language)
    if translated is not None:
        return translated
    if key.endswith(" (Ft)"):
        return T(key[:-5]) + " (Ft)"
    return key


def TF(key, **values):
    return T(key).format(**values)


def translate_audit_description(description):
    patterns = (
        (r"Updated password for (?P<username>.+)", "Updated password for {username}"),
        (r"(?P<action>Added|Updated|Deleted) supplier (?P<name>.+)", None),
        (r"Received purchase (?P<reference>.+) from (?P<supplier>.+) \((?P<quantity>\d+) units\)",
         "Received purchase {reference} from {supplier} ({quantity} units)"),
        (r"(?P<action>Created|Updated) purchase order (?P<number>\S+) for (?P<supplier>.+)", None),
        (r"Changed purchase order (?P<number>\S+) from (?P<old_status>\S+) to (?P<new_status>\S+)",
         "Changed purchase order {number} from {old_status} to {new_status}"),
        (r"(?P<action>Added|Updated|Deleted) product (?P<name>.+)", None),
        (r"(?P<action>Added|Updated|Deleted) batch (?P<batch>\S+) for (?P<product>.+)", None),
        (r"Carried out item return for (?P<product>.+) x(?P<quantity>\d+) from (?P<receipt>.+)",
         "Carried out item return for {product} x{quantity} from {receipt}"),
        (r"Deleted return (?P<return_receipt>\S+) for (?P<sale_receipt>\S+)",
         "Deleted return {return_receipt} for {sale_receipt}"),
        (r"Sold (?P<product>.+) x(?P<quantity>\d+)", "Sold {product} x{quantity}"),
        (r"Deleted sale (?P<receipt>.+)", "Deleted sale {receipt}"),
    )
    for pattern, template in patterns:
        match = re.fullmatch(pattern, str(description or ""))
        if not match:
            continue
        values = match.groupdict()
        if template is None:
            action = values.pop("action")
            if "batch" in values:
                template = f"{action} batch {{batch}} for {{product}}"
            elif "number" in values:
                template = f"{action} purchase order {{number}} for {{supplier}}"
            else:
                template = f"{action} {'supplier' if 'name' in values and 'supplier' in pattern else 'product'} {{name}}"
        for status in ("old_status", "new_status"):
            if status in values:
                values[status] = T(values[status].replace("_", " ").title())
        return TF(template, **values)
    return T(description)


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


def set_language(app, name):
    """Apply and persist a language selected by its user-facing name."""
    global _language
    settings = QSettings("KhalisDawa", "Pharmacy")
    names = list(LANGUAGES)
    if name not in names:
        name = "English"
    settings.setValue("language", name)
    locale_value = QLocale(LANGUAGES[name])
    _language = LANGUAGES[name][:2]
    QLocale.setDefault(locale_value)
    app.setLayoutDirection(
        Qt.LayoutDirection.RightToLeft if _language == "ar"
        else Qt.LayoutDirection.LeftToRight
    )
    return name


def language_name():
    code = f"{_language}_"
    return next((name for name, locale_name in LANGUAGES.items() if locale_name.startswith(code)), "English")


def initialize_language(app):
    """Restore the saved language without interrupting application startup."""
    saved = QSettings("KhalisDawa", "Pharmacy").value("language", "English")
    return set_language(app, saved)


def choose_language(app):
    """Backward-compatible alias retained for older callers."""
    initialize_language(app)
    return True
