# دليل ربط PFC مع n8n وPostman

## النتيجة

تم تحويل موقع **Patient Flow Controller (PFC)** من واجهة تعتمد على `localStorage` فقط إلى تطبيق يملك REST API قابلة للاستخدام من n8n وPostman. الواجهة تظل قادرة على العمل محلياً عند توقف الخادم، وتحاول مزامنة الحالة مع الخادم عندما يكون متاحاً.

تم إنشاء العناصر التالية:

| العنصر | القيمة |
|---|---|
| Workflow في n8n | `PFC API Gateway` |
| Workflow ID | `bO3eHhkNBguGyqOW` |
| رابط Workflow | `https://bessan.duckdns.org/workflow/bO3eHhkNBguGyqOW` |
| Webhook path | `POST /webhook/pfc-api-gateway` |
| Postman workspace | `Mohamed Hosamm's Workspace` |
| Postman collection | `PFC — n8n API Integration` |
| Collection UID | `58402816-3271c257-9cbc-4926-877c-8343083a3804` |
| Postman environment | `PFC n8n Integration` |
| Environment UID | `58402816-896a678d-092d-4512-87c3-79c32c53f562` |

> رابط n8n الموجود في Collection هو الرابط المنشور حالياً: `https://bessan.duckdns.org/webhook/pfc-api-gateway`. يجب تحديثه إذا تغير عنوان n8n.

## كيف يعمل التدفق

يرسل Postman أو أي نظام خارجي طلب `POST` إلى Webhook في n8n. يحتوي جسم الطلب على العملية المطلوبة ومسار API والبيانات. يتحقق n8n من أن العملية من العمليات المسموح بها، ثم يرسل الطلب إلى REST API الخاص بالموقع، وأخيراً يعيد استجابة الموقع إلى العميل.

```json
{
  "method": "PATCH",
  "path": "/api/patients/245",
  "query": {},
  "body": {
    "status": "Done",
    "late": false
  }
}
```

يستخدم n8n متغيري بيئة، ولا يجب وضع قيمهما داخل الكود أو Collection:

```text
PFC_API_BASE_URL=https://your-pfc-domain.example
PFC_API_KEY=ضع_مفتاحاً_طويلاً_وعشوائياً
```

إذا كان PFC يعمل خلف نفس الخادم أو في شبكة داخلية، يمكن أن تكون قيمة `PFC_API_BASE_URL` مثل `http://pfc-app:3000`. يجب أن يبدأ `path` دائماً بـ `/api/` حتى لا يتحول الـ Gateway إلى Proxy مفتوح لمسارات أخرى.

## تشغيل الموقع محلياً

يتطلب المشروع Node.js 18 أو أحدث.

```bash
cd PFC-Project
PFC_API_KEY='change-this-in-production' npm start
```

يفتح الموقع على `http://localhost:3000`. يفحص الخادم عمله من خلال:

```bash
curl http://localhost:3000/api/health
```

الاستجابة المتوقعة:

```json
{
  "ok": true,
  "service": "pfc-api"
}
```

يُحفظ سجل البيانات في `data/state.json`. هذا الملف مستثنى من Git لأنه قد يحتوي على بيانات تشغيلية. في بيئة الإنتاج يجب استخدام قاعدة بيانات فعلية أو تخزين دائم مؤمّن بدلاً من ملف JSON.

## REST API المتاحة

| الطريقة | المسار | الوظيفة |
|---|---|---|
| GET | `/api/health` | فحص حالة الخدمة |
| GET | `/api/state` | قراءة الحالة الكاملة للتكامل أو الترحيل |
| PUT/PATCH | `/api/state` | استبدال أو تحديث الحالة الكاملة |
| GET | `/api/{resource}` | قراءة مجموعة سجلات مع فلاتر مطابقة تامة |
| POST | `/api/{resource}` | إضافة سجل جديد |
| GET | `/api/{resource}/{id}` | قراءة سجل واحد |
| PUT | `/api/{resource}/{id}` | استبدال سجل كامل |
| PATCH | `/api/{resource}/{id}` | تعديل حقول محددة |
| DELETE | `/api/{resource}/{id}` | حذف سجل |

الموارد الحالية هي: `users`, `patients`, `organizations`, `rooms`, `sessions`, `actions`, `notifications`, و`routing`.

مثال مباشر خارج n8n:

```bash
curl -X POST "$PFC_API_BASE_URL/api/patients" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $PFC_API_KEY" \
  -d '{"service":"CMO","branch":"CMO","status":"Waiting"}'
```

## Postman

افتح Collection باسم **PFC — n8n API Integration** واختر Environment باسم **PFC n8n Integration**. تحتوي Collection على أمثلة جاهزة لفحص الخدمة، قراءة المرضى، إضافة تذكرة، تعديل الحالة، استبدال مؤسسة، حذف سجل، وقراءة الحالة الكاملة.

في بيئة حقيقية، لا تضع مفتاح API في وصف عام أو داخل مستودع Git. مفتاح PFC يتم ضبطه في n8n من خلال متغير البيئة `PFC_API_KEY`، بينما يمرر n8n المفتاح إلى الموقع في ترويسة `X-API-Key`.

## ملاحظات أمنية مهمة

النسخة الحالية مناسبة كبنية تكامل أولية وبيئة اختبار. قبل استخدامها على الإنترنت يجب إضافة قاعدة بيانات، وتسجيل دخول حقيقي يعتمد على جلسات أو JWT، وتحديد صلاحيات حسب الدور، والتحقق من مخطط كل مورد، وتسجيل تدقيق للعمليات الحساسة، وتحديد معدل الطلبات، وتفعيل HTTPS. كما يجب عدم استخدام الحسابات التجريبية الموجودة في الواجهة كحسابات إنتاج.

## خياران للتشغيل

| الخيار | المزايا | القيود | التكلفة والتعقيد |
|---|---|---|---|
| تشغيل API الحالي مع n8n | يحقق المطلوب بسرعة، ويدعم أي مورد جديد عبر نفس الـ Gateway، ويتيح الاختبار من Postman | يحتاج خادماً دائماً وطبقة أمان وقاعدة بيانات قبل الإنتاج | أقل تعقيداً، وتكلفته تعتمد على الاستضافة الحالية |
| بناء Backend كامل بقاعدة بيانات وAuth | أمان وصلاحيات وتدقيق أفضل، ومناسب للاستخدام الرسمي طويل المدى | يحتاج تصميم مخطط وترحيل البيانات واختبارات إضافية | أعلى تعقيداً، لكنه المسار الصحيح للإنتاج |

التنفيذ الحالي اختار الخيار الأول كطبقة تكامل قابلة للتشغيل، مع إبقاء المسار الثاني واضحاً قبل التسليم الرسمي.

## الملفات المضافة أو المعدلة

- `server.js`: خادم الملفات وREST API وحفظ الحالة.
- `package.json`: أوامر تشغيل المشروع.
- `app.js`: مزامنة الواجهة مع `/api/state` مع fallback محلي.
- `.gitignore`: منع رفع ملف الحالة التشغيلي.
- `INTEGRATION_GUIDE_AR.md`: هذا الدليل.
