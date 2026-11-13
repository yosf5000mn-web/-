// Y-N STORE - نسخة ثابتة HTML/CSS/JS
// تنبيه أمني: هذا المشروع يخزن البيانات على نفس المتصفح فقط، وكلمة المرور داخل JavaScript ليست حماية حقيقية.
// لا تضع بيانات شديدة الحساسية هنا. لمزامنة البيانات بين الأجهزة تحتاج Backend أو خدمة قاعدة بيانات مثل Supabase.

const PASSWORD = "ChangeMe123!"; // غيّرها هنا، لكن هذا لا يمنع أي شخص من فحص ملفات الموقع.
const STORAGE_KEY = "yn_store_invoices_v1";
const SESSION_KEY = "yn_store_logged_in";
const labels = { expense: "مصروف", payment: "مدفوعات", receipt: "مستلمات", debt: "دين" };
let invoices = [];
let toastTimer;

const $ = (id) => document.getElementById(id);
const loginScreen = $("loginScreen");
const appScreen = $("appScreen");
const invoiceDialog = $("invoiceDialog");
const viewDialog = $("viewDialog");

function todayISO() {
  const d = new Date();
  const local = new Date(d.getTime() - d.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}
function money(n) {
  return Number(n || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[ch]);
}
function loadInvoices() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    invoices = Array.isArray(parsed) ? parsed : [];
  } catch { invoices = []; }
}
function saveInvoices() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(invoices));
}
function showToast(message) {
  const toast = $("toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.add("hidden"), 3000);
}
function enterApp() {
  loginScreen.classList.add("hidden");
  appScreen.classList.remove("hidden");
  loadInvoices();
  render();
}
function logout() {
  sessionStorage.removeItem(SESSION_KEY);
  appScreen.classList.add("hidden");
  loginScreen.classList.remove("hidden");
  $("loginPassword").value = "";
}
$("loginForm").addEventListener("submit", (event) => {
  event.preventDefault();
  if ($("loginPassword").value === PASSWORD) {
    sessionStorage.setItem(SESSION_KEY, "yes");
    $("loginError").textContent = "";
    enterApp();
  } else {
    $("loginError").textContent = "كلمة المرور غير صحيحة.";
  }
});
$("logoutBtn").addEventListener("click", logout);
$("homeLink").addEventListener("click", (e) => { e.preventDefault(); render(); window.scrollTo({top:0,behavior:"smooth"}); });

function render() {
  const totals = { expense: 0, payment: 0, receipt: 0, debt: 0 };
  invoices.forEach(inv => { totals[inv.kind] = (totals[inv.kind] || 0) + Number(inv.amount || 0); });
  $("cashTotal").textContent = money(totals.receipt - totals.payment - totals.expense);
  $("receiptTotal").textContent = money(totals.receipt);
  $("expenseTotal").textContent = money(totals.expense);
  $("debtTotal").textContent = money(totals.debt);

  const query = $("searchInput").value.trim().toLowerCase();
  const kind = $("filterKind").value;
  const filtered = [...invoices].filter(inv => {
    const text = `${inv.invoiceNo} ${inv.person} ${inv.description} ${inv.notes || ""}`.toLowerCase();
    return (!query || text.includes(query)) && (kind === "all" || inv.kind === kind);
  }).sort((a,b) => b.createdAt - a.createdAt);
  $("invoiceCount").textContent = `${filtered.length} فاتورة`;
  const list = $("invoiceList");
  if (!filtered.length) {
    list.innerHTML = `<div class="empty"><div class="empty-icon">▤</div><h3>${invoices.length ? "لا توجد نتائج مطابقة" : "لا توجد فواتير بعد"}</h3><p>${invoices.length ? "جرّب تغيير كلمات البحث أو نوع الفاتورة." : "ابدأ بتسجيل أول حركة مالية ليظهر ملخص حساباتك هنا."}</p><button class="btn primary" id="emptyNewBtn">إنشاء فاتورة</button></div>`;
    $("emptyNewBtn").addEventListener("click", () => openInvoice());
    return;
  }
  list.innerHTML = `<div class="table-wrap"><table><thead><tr><th>رقم الفاتورة</th><th>النوع</th><th>الاسم / الجهة</th><th>التفاصيل</th><th>التاريخ</th><th>المبلغ</th><th></th></tr></thead><tbody>${filtered.map(inv => `
    <tr><td><button class="text-button invoice-link" data-view="${inv.id}">${escapeHtml(inv.invoiceNo)}</button></td>
    <td><span class="type-pill ${inv.kind}">${labels[inv.kind]}</span></td><td>${escapeHtml(inv.person)}</td>
    <td class="description-cell">${escapeHtml(inv.description)}</td><td>${escapeHtml(inv.invoiceDate)}</td>
    <td class="amount">${money(inv.amount)} <small>${escapeHtml(inv.currency)}</small></td>
    <td><button class="text-button open-link" data-view="${inv.id}">عرض ←</button></td></tr>`).join("")}</tbody></table></div>`;
  list.querySelectorAll("[data-view]").forEach(btn => btn.addEventListener("click", () => viewInvoice(btn.dataset.view)));
}

function openInvoice(kind = "receipt") {
  $("invoiceForm").reset();
  $("kind").value = kind;
  $("invoiceDate").value = todayISO();
  $("invoiceDialog").showModal();
}
$("newInvoiceBtn").addEventListener("click", () => openInvoice());
document.querySelectorAll("[data-kind]").forEach(btn => btn.addEventListener("click", () => openInvoice(btn.dataset.kind)));
$("closeDialog").addEventListener("click", () => invoiceDialog.close());
$("cancelInvoice").addEventListener("click", () => invoiceDialog.close());

$("invoiceForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const amount = Number($("amount").value);
  if (!Number.isFinite(amount) || amount <= 0) { showToast("أدخل مبلغاً صحيحاً أكبر من صفر."); return; }
  const invoice = {
    id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    invoiceNo: `YN-${Date.now().toString().slice(-8)}`,
    kind: $("kind").value,
    person: $("person").value.trim(),
    description: $("description").value.trim(),
    amount,
    currency: $("currency").value,
    invoiceDate: $("invoiceDate").value,
    dueDate: $("dueDate").value,
    notes: $("notes").value.trim(),
    createdAt: Date.now()
  };
  if (!invoice.person || !invoice.description || !invoice.invoiceDate) { showToast("يرجى تعبئة الحقول المطلوبة."); return; }
  invoices.push(invoice);
  saveInvoices();
  invoiceDialog.close();
  render();
  showToast("تم حفظ الفاتورة بنجاح.");
});

function viewInvoice(id) {
  const inv = invoices.find(item => item.id === id);
  if (!inv) return;
  $("invoiceDetail").innerHTML = `
    <div class="modal-heading no-print"><div><p class="eyebrow">INVOICE DETAILS</p><h2>تفاصيل الفاتورة</h2></div><button type="button" class="close-btn" id="closeView">×</button></div>
    <section class="invoice-sheet"><div class="invoice-header"><div><div class="brand-mark">YN</div><h1>Y-N STORE</h1><p class="muted">فاتورة مالية</p></div><div class="invoice-number"><span>رقم الفاتورة</span><b>${escapeHtml(inv.invoiceNo)}</b><span>تاريخ الإصدار: ${escapeHtml(inv.invoiceDate)}</span></div></div>
    <div class="invoice-type ${inv.kind}">${labels[inv.kind]}</div>
    <div class="invoice-parties"><div><small>الاسم / الجهة</small><strong>${escapeHtml(inv.person)}</strong></div><div><small>تاريخ الاستحقاق</small><strong>${escapeHtml(inv.dueDate || "—")}</strong></div></div>
    <table class="invoice-table"><thead><tr><th>البيان</th><th>العملة</th><th>المبلغ</th></tr></thead><tbody><tr><td>${escapeHtml(inv.description)}</td><td>${escapeHtml(inv.currency)}</td><td class="amount">${money(inv.amount)}</td></tr></tbody></table>
    <div class="total-box"><span>الإجمالي</span><strong>${money(inv.amount)} ${escapeHtml(inv.currency)}</strong></div>
    ${inv.notes ? `<div class="notes"><b>ملاحظات</b><p>${escapeHtml(inv.notes)}</p></div>` : ""}
    <div class="signature-row"><div>توقيع المسؤول: __________________</div><div>توقيع المستلم: __________________</div></div><div class="invoice-bottom">شكراً لك · Y-N STORE</div></section>
    <div class="invoice-actions no-print"><button class="btn primary" id="printInvoice">طباعة / حفظ PDF</button><button class="btn danger" id="deleteInvoice">حذف الفاتورة</button></div>`;
  viewDialog.showModal();
  $("closeView").addEventListener("click", () => viewDialog.close());
  $("printInvoice").addEventListener("click", () => window.print());
  $("deleteInvoice").addEventListener("click", () => {
    if (!confirm("هل أنت متأكد من حذف هذه الفاتورة؟ لا يمكن التراجع عن الحذف.")) return;
    invoices = invoices.filter(item => item.id !== id);
    saveInvoices();
    viewDialog.close();
    render();
    showToast("تم حذف الفاتورة.");
  });
}
$("searchInput").addEventListener("input", render);
$("filterKind").addEventListener("change", render);

function downloadFile(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}
$("exportBtn").addEventListener("click", () => {
  const rows = [["رقم الفاتورة","النوع","الاسم","التفاصيل","المبلغ","العملة","التاريخ","تاريخ الاستحقاق","ملاحظات"]];
  invoices.forEach(inv => rows.push([inv.invoiceNo, labels[inv.kind], inv.person, inv.description, inv.amount, inv.currency, inv.invoiceDate, inv.dueDate || "", inv.notes || ""]));
  const csv = "\uFEFF" + rows.map(row => row.map(value => `"${String(value).replace(/"/g,'""')}"`).join(",")).join("\r\n");
  downloadFile("yn-store-invoices.csv", csv, "text/csv;charset=utf-8");
  showToast("تم تجهيز ملف CSV.");
});
$("backupBtn").addEventListener("click", () => {
  downloadFile(`yn-store-backup-${todayISO()}.json`, JSON.stringify({ exportedAt: new Date().toISOString(), invoices }, null, 2), "application/json");
  showToast("تم تنزيل النسخة الاحتياطية.");
});

if (sessionStorage.getItem(SESSION_KEY) === "yes") enterApp();
