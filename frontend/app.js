// Frontend logic for the Member Management app.
// Talks to the FastAPI backend over JSON through apiFetch(), which attaches the
// admin session token and bounces back to the login page if it has lapsed.
// That helper, the API base URL and the session store all live in auth.js,
// which every page loads first.

const form = document.getElementById("member-form");
const formTitle = document.getElementById("form-title");
const submitBtn = document.getElementById("submit-btn");
const cancelEditBtn = document.getElementById("cancel-edit-btn");
const formError = document.getElementById("form-error");
const memberIdField = document.getElementById("member-id");

const tbody = document.getElementById("members-tbody");
const emptyState = document.getElementById("empty-state");
const memberCount = document.getElementById("member-count");
const statusMessage = document.getElementById("status-message");

const searchFirstname = document.getElementById("search-firstname");
const searchLastname = document.getElementById("search-lastname");
const searchIntercessor = document.getElementById("search-intercessor");
const searchBtn = document.getElementById("search-btn");
const clearSearchBtn = document.getElementById("clear-search-btn");

const exportCsvBtn = document.getElementById("export-csv-btn");
const importCsvBtn = document.getElementById("import-csv-btn");
const importCsvInput = document.getElementById("import-csv-input");
const printBtn = document.getElementById("print-btn");
const printMeta = document.getElementById("print-meta");

const listPanel = document.getElementById("list-panel");
const detailPanel = document.getElementById("detail-panel");
const detailName = document.getElementById("detail-name");
const detailId = document.getElementById("detail-id");
const detailGrid = document.getElementById("detail-grid");
const detailPrintMeta = document.getElementById("detail-print-meta");
const detailPrintBtn = document.getElementById("detail-print-btn");
const detailEditBtn = document.getElementById("detail-edit-btn");
const detailBackBtn = document.getElementById("detail-back-btn");

const logoutBtn = document.getElementById("logout-btn");

const deleteModal = document.getElementById("delete-modal");
const deleteModalText = document.getElementById("delete-modal-text");
const confirmDeleteBtn = document.getElementById("confirm-delete-btn");
const cancelDeleteBtn = document.getElementById("cancel-delete-btn");

// Canonical field order — drives the form payload, the table columns and the
// CSV column order. Keep it in sync with the <th> row in index.html.
const FIELDS = [
  "firstname",
  "lastname",
  "date_of_birth",
  "place_of_birth",
  "father_name",
  "mother_name",
  "intercessor_name",
  "godfather_name",
  "godmother_name",
  "baptizing_priest",
  "place_of_baptism",
  "date_of_baptism",
  "comments",
];

// The one field that may be left blank — free-form notes. Everything else in
// FIELDS is required by the API, and CSV rows missing any of them are skipped.
const OPTIONAL_FIELDS = new Set(["comments"]);

// Arabic labels for the detail view, keyed by the field names above. Same
// wording as the form labels and the table headings.
const FIELD_LABELS = {
  firstname: "الاسم الأول",
  lastname: "اسم العائلة",
  date_of_birth: "تاريخ الميلاد",
  place_of_birth: "مكان الميلاد",
  father_name: "اسم الأب",
  mother_name: "اسم الأم",
  intercessor_name: "اسم الشفيع",
  godfather_name: "اسم العرّاب",
  godmother_name: "اسم العرّابة",
  baptizing_priest: "الكاهن المعمّد",
  place_of_baptism: "مكان العماد",
  date_of_baptism: "تاريخ العماد",
  comments: "ملاحظات",
};

let pendingDeleteId = null;
let currentMembers = [];

// ---- Rendering ----

function renderMembers(members) {
  currentMembers = members;
  tbody.innerHTML = "";

  if (members.length === 0) {
    emptyState.hidden = false;
  } else {
    emptyState.hidden = true;
  }

  memberCount.textContent = members.length;

  for (const member of members) {
    const row = document.createElement("tr");

    row.innerHTML = `
      <td>${escapeHtml(member.firstname)}</td>
      <td>${escapeHtml(member.lastname)}</td>
      <td>${escapeHtml(member.date_of_birth)}</td>
      <td>${escapeHtml(member.place_of_birth)}</td>
      <td>${escapeHtml(member.father_name)}</td>
      <td>${escapeHtml(member.mother_name)}</td>
      <td>${escapeHtml(member.intercessor_name)}</td>
      <td>${escapeHtml(member.godfather_name)}</td>
      <td>${escapeHtml(member.godmother_name)}</td>
      <td>${escapeHtml(member.baptizing_priest)}</td>
      <td>${escapeHtml(member.place_of_baptism)}</td>
      <td>${escapeHtml(member.date_of_baptism)}</td>
      <td class="comments-cell" title="${escapeHtml(member.comments)}">${escapeHtml(member.comments)}</td>
      <td class="actions-cell">
        <button type="button" class="btn btn-primary btn-small" data-action="open" data-id="${member.id}">فتح</button>
        <button type="button" class="btn btn-ghost btn-small" data-action="edit" data-id="${member.id}">تعديل</button>
        <button type="button" class="btn btn-danger btn-small" data-action="delete" data-id="${member.id}">حذف</button>
      </td>
    `;

    tbody.appendChild(row);
  }
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

function showStatus(message, type) {
  statusMessage.textContent = message;
  statusMessage.className = `status-message ${type}`;
  statusMessage.hidden = false;
  setTimeout(() => { statusMessage.hidden = true; }, 3500);
}

// ---- API calls ----

async function fetchMembers(params = {}) {
  const query = new URLSearchParams(params).toString();

  const response = await apiFetch(`/members${query ? `?${query}` : ""}`);
  if (!response.ok) {
    throw new Error("تعذّر تحميل قائمة الأعضاء.");
  }
  return response.json();
}

async function loadAndRenderMembers(params = {}) {
  try {
    const members = await fetchMembers(params);
    renderMembers(members);
  } catch (err) {
    showStatus("تعذّر تحميل قائمة الأعضاء. تأكد من أن الخدمة الخلفية تعمل.", "error");
  }
}

async function fetchMember(id) {
  const response = await apiFetch(`/members/${id}`);
  if (!response.ok) throw new Error("العضو غير موجود.");
  return response.json();
}

async function createMember(payload) {
  const response = await apiFetch("/members", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await extractError(response));
  return response.json();
}

async function updateMember(id, payload) {
  const response = await apiFetch(`/members/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await extractError(response));
  return response.json();
}

async function deleteMember(id) {
  const response = await apiFetch(`/members/${id}`, { method: "DELETE" });
  if (!response.ok) throw new Error(await extractError(response));
}

// The API reports errors in English; map the known ones to Arabic and fall
// back to a generic message so nothing English reaches the user.
const SERVER_ERRORS = {
  "Member not found": "العضو غير موجود.",
};

async function extractError(response) {
  try {
    const data = await response.json();
    if (Array.isArray(data.detail)) {
      return "يرجى التأكد من تعبئة جميع الحقول بشكل صحيح.";
    }
    return SERVER_ERRORS[data.detail] || "حدث خطأ ما. يرجى المحاولة مرة أخرى.";
  } catch {
    return "حدث خطأ ما. يرجى المحاولة مرة أخرى.";
  }
}

// ---- Form handling ----

function getFormPayload() {
  const payload = {};
  for (const field of FIELDS) {
    const value = document.getElementById(field).value.trim();
    // An empty optional field means "no value", so send null rather than an
    // empty string — that is what an omitted field stores.
    payload[field] = !value && OPTIONAL_FIELDS.has(field) ? null : value;
  }
  return payload;
}

function resetForm() {
  form.reset();
  memberIdField.value = "";
  formTitle.textContent = "إضافة عضو";
  submitBtn.textContent = "إضافة عضو";
  cancelEditBtn.hidden = true;
  formError.textContent = "";
}

function enterEditMode(member) {
  memberIdField.value = member.id;
  for (const field of FIELDS) {
    document.getElementById(field).value = member[field] ?? "";
  }
  formTitle.textContent = `تعديل بيانات العضو رقم ${member.id}`;
  submitBtn.textContent = "حفظ التغييرات";
  cancelEditBtn.hidden = false;
  formError.textContent = "";
  document.getElementById("firstname").focus();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  formError.textContent = "";

  const payload = getFormPayload();
  const editingId = memberIdField.value;

  try {
    if (editingId) {
      await updateMember(editingId, payload);
      showStatus("تم تحديث بيانات العضو.", "success");
    } else {
      await createMember(payload);
      showStatus("تمت إضافة العضو.", "success");
    }
    resetForm();
    await loadAndRenderMembers();
  } catch (err) {
    formError.textContent = err.message;
  }
});

cancelEditBtn.addEventListener("click", resetForm);

// ---- Member detail view ----

// The detail view replaces the list in place rather than navigating: the
// `detail-open` body class hides the form, the search panel and the list, so
// both the screen and the print sheet show one member only.
let currentDetailMember = null;

function renderMemberDetail(member) {
  currentDetailMember = member;

  const fullName = [member.firstname, member.lastname].filter(Boolean).join(" ");
  detailName.textContent = fullName || "—";
  detailId.textContent = `رقم العضو: ${member.id}`;

  detailGrid.innerHTML = "";
  for (const field of FIELDS) {
    const term = document.createElement("dt");
    term.textContent = FIELD_LABELS[field];

    const value = document.createElement("dd");
    const raw = member[field];
    // Rows created before the later columns existed come back empty.
    value.textContent = raw === null || raw === undefined || raw === "" ? "—" : raw;
    if (!raw) value.classList.add("detail-empty");

    detailGrid.append(term, value);
  }
}

function openDetail(member) {
  renderMemberDetail(member);
  detailPanel.hidden = false;
  document.body.classList.add("detail-open");
  window.scrollTo({ top: 0 });
  detailBackBtn.focus();
}

function closeDetail() {
  document.body.classList.remove("detail-open");
  detailPanel.hidden = true;
  currentDetailMember = null;
}

async function openDetailById(id) {
  try {
    openDetail(await fetchMember(id));
  } catch {
    showStatus("تعذّر تحميل بيانات هذا العضو.", "error");
  }
}

detailBackBtn.addEventListener("click", closeDetail);

detailPrintBtn.addEventListener("click", () => {
  if (!currentDetailMember) return;
  detailPrintMeta.textContent = `تاريخ الطباعة: ${todayStamp()}`;
  window.print();
});

detailEditBtn.addEventListener("click", () => {
  if (!currentDetailMember) return;
  const member = currentDetailMember;
  closeDetail();
  enterEditMode(member);
  document.getElementById("form-panel").scrollIntoView({ block: "start" });
});

// Esc closes the detail view, unless the delete dialog is the thing on top.
document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  if (!deleteModal.hidden) return;
  if (document.body.classList.contains("detail-open")) closeDetail();
});

// ---- Table actions (open / edit / delete) ----

tbody.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;

  const id = button.dataset.id;

  if (button.dataset.action === "open") {
    await openDetailById(id);
  }

  if (button.dataset.action === "edit") {
    try {
      enterEditMode(await fetchMember(id));
    } catch {
      showStatus("تعذّر تحميل بيانات هذا العضو للتعديل.", "error");
    }
  }

  if (button.dataset.action === "delete") {
    pendingDeleteId = id;
    deleteModalText.textContent = `سيتم حذف العضو رقم ${id} نهائيًا.`;
    deleteModal.hidden = false;
  }
});

confirmDeleteBtn.addEventListener("click", async () => {
  if (!pendingDeleteId) return;
  try {
    await deleteMember(pendingDeleteId);
    showStatus("تم حذف العضو.", "success");
    if (memberIdField.value === pendingDeleteId) resetForm();
    await loadAndRenderMembers();
  } catch (err) {
    showStatus(err.message, "error");
  } finally {
    deleteModal.hidden = true;
    pendingDeleteId = null;
  }
});

cancelDeleteBtn.addEventListener("click", () => {
  deleteModal.hidden = true;
  pendingDeleteId = null;
});

// ---- Search ----

// Any combination of the three fields is allowed — the backend ANDs together
// whichever ones are filled in, and returns the full list when none are.
function currentSearchParams() {
  const params = {};
  const firstname = searchFirstname.value.trim();
  const lastname = searchLastname.value.trim();
  const intercessor = searchIntercessor.value.trim();
  if (firstname) params.firstname = firstname;
  if (lastname) params.lastname = lastname;
  if (intercessor) params.intercessor_name = intercessor;
  return params;
}

searchBtn.addEventListener("click", () => {
  loadAndRenderMembers(currentSearchParams());
});

clearSearchBtn.addEventListener("click", () => {
  searchFirstname.value = "";
  searchLastname.value = "";
  searchIntercessor.value = "";
  loadAndRenderMembers();
});

// ---- CSV export ----

function csvEscape(value) {
  const text = String(value ?? "");
  if (/[",\r\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function buildCsv(members) {
  const lines = [FIELDS.join(",")];
  for (const member of members) {
    lines.push(FIELDS.map((field) => csvEscape(member[field])).join(","));
  }
  return lines.join("\r\n");
}

function todayStamp() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

exportCsvBtn.addEventListener("click", () => {
  if (currentMembers.length === 0) {
    showStatus("لا توجد بيانات للتصدير — قائمة الأعضاء فارغة.", "error");
    return;
  }

  const blob = new Blob([buildCsv(currentMembers)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = `members-export-${todayStamp()}.csv`; // ASCII filename keeps downloads portable
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);

  showStatus(`تم تصدير ${currentMembers.length} عضو.`, "success");
});

// ---- Print ----

// The print stylesheet hides the form, the search panel and the row actions,
// so printing the page itself gives a clean list — no separate print window.
printBtn.addEventListener("click", () => {
  if (currentMembers.length === 0) {
    showStatus("لا توجد بيانات للطباعة — قائمة الأعضاء فارغة.", "error");
    return;
  }

  const parts = [`عدد الأعضاء: ${currentMembers.length}`, `تاريخ الطباعة: ${todayStamp()}`];
  const firstname = searchFirstname.value.trim();
  const lastname = searchLastname.value.trim();
  const intercessor = searchIntercessor.value.trim();
  if (firstname) parts.push(`بحث بالاسم الأول: ${firstname}`);
  if (lastname) parts.push(`بحث باسم العائلة: ${lastname}`);
  if (intercessor) parts.push(`بحث بالشفيع: ${intercessor}`);
  printMeta.textContent = parts.join(" — ");

  window.print();
});

// ---- CSV import ----

// Minimal state-machine parser: handles quoted fields containing commas,
// escaped double quotes (""), and CRLF or LF line endings.
function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const char = text[i];

    if (inQuotes) {
      if (char === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        field += char;
      }
      continue;
    }

    if (char === '"') {
      inQuotes = true;
    } else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\n" || char === "\r") {
      if (char === "\r" && text[i + 1] === "\n") i++;
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }

  if (field !== "" || row.length > 0) {
    row.push(field);
    rows.push(row);
  }

  return rows.filter((r) => r.some((cell) => cell.trim() !== ""));
}

// Maps CSV columns to member fields. Uses the header row when it names the
// fields; otherwise falls back to the canonical FIELDS order. Only the two
// name columns need to be present to recognise a header, so files exported
// before a field was added are still read as having one instead of having
// their header row imported as a member.
function resolveColumns(headerRow) {
  const normalized = headerRow.map((cell) => cell.trim().toLowerCase());
  const isHeader = normalized.includes("firstname") && normalized.includes("lastname");

  if (!isHeader) {
    return { hasHeader: false, indexes: FIELDS.map((_, index) => index) };
  }
  return { hasHeader: true, indexes: FIELDS.map((field) => normalized.indexOf(field)) };
}

async function importCsvText(text) {
  const rows = parseCsv(text);
  if (rows.length === 0) {
    showStatus("ملف CSV فارغ.", "error");
    return;
  }

  const { hasHeader, indexes } = resolveColumns(rows[0]);
  const dataRows = hasHeader ? rows.slice(1) : rows;

  if (dataRows.length === 0) {
    showStatus("لا يحتوي ملف CSV على أي صفوف بيانات.", "error");
    return;
  }

  let imported = 0;
  let skippedInvalid = 0;
  let failed = 0;

  for (const row of dataRows) {
    const payload = {};
    let valid = true;

    FIELDS.forEach((field, position) => {
      const value = (row[indexes[position]] ?? "").trim();
      const optional = OPTIONAL_FIELDS.has(field);
      if (!value && !optional) valid = false;
      payload[field] = !value && optional ? null : value;
    });

    if (!valid) {
      skippedInvalid++;
      continue;
    }

    try {
      await createMember(payload);
      imported++;
    } catch {
      failed++;
    }
  }

  await loadAndRenderMembers();

  const parts = [`تم استيراد ${imported} من ${dataRows.length} عضو.`];
  if (skippedInvalid > 0) parts.push(`تم تجاهل ${skippedInvalid} صفًا بسبب حقول ناقصة.`);
  if (failed > 0) parts.push(`تم رفض ${failed} صفًا من الخادم.`);

  showStatus(parts.join(" "), imported === dataRows.length ? "success" : "error");
}

importCsvBtn.addEventListener("click", () => importCsvInput.click());

importCsvInput.addEventListener("change", () => {
  const file = importCsvInput.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = async () => {
    try {
      await importCsvText(String(reader.result));
    } finally {
      importCsvInput.value = "";
    }
  };
  reader.onerror = () => {
    showStatus("تعذّر قراءة هذا الملف.", "error");
    importCsvInput.value = "";
  };
  reader.readAsText(file);
});

// ---- Session ----

// logout() clears the token and returns to the login page. Nothing needs
// clearing from the DOM: the page is left behind, and the records were never
// cached anywhere.
logoutBtn.addEventListener("click", logout);

// ---- Init ----

// auth.js has already redirected an anonymous visitor by this point; the check
// keeps this from firing a doomed request during the redirect.
if (hasSession()) {
  loadAndRenderMembers();
}