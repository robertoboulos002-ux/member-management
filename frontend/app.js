// Frontend logic for the Member Management app.
// Talks to the FastAPI backend at API_BASE via fetch/JSON.

const API_BASE = "https://member-management-42by.onrender.com";
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

const deleteModal = document.getElementById("delete-modal");
const deleteModalText = document.getElementById("delete-modal-text");
const confirmDeleteBtn = document.getElementById("confirm-delete-btn");
const cancelDeleteBtn = document.getElementById("cancel-delete-btn");

const FIELDS = ["firstname", "lastname", "date_of_birth", "father_name", "mother_name", "intercessor_name"];

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
      <td>${escapeHtml(member.father_name)}</td>
      <td>${escapeHtml(member.mother_name)}</td>
      <td>${escapeHtml(member.intercessor_name)}</td>
      <td class="actions-cell">
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
  const url = `${API_BASE}/members${query ? `?${query}` : ""}`;

  const response = await fetch(url);
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

async function createMember(payload) {
  const response = await fetch(`${API_BASE}/members`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await extractError(response));
  return response.json();
}

async function updateMember(id, payload) {
  const response = await fetch(`${API_BASE}/members/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await extractError(response));
  return response.json();
}

async function deleteMember(id) {
  const response = await fetch(`${API_BASE}/members/${id}`, { method: "DELETE" });
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
    payload[field] = document.getElementById(field).value.trim();
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

// ---- Table actions (edit / delete) ----

tbody.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;

  const id = button.dataset.id;

  if (button.dataset.action === "edit") {
    try {
      const response = await fetch(`${API_BASE}/members/${id}`);
      if (!response.ok) throw new Error("العضو غير موجود.");
      const member = await response.json();
      enterEditMode(member);
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

searchBtn.addEventListener("click", () => {
  const params = {};
  if (searchFirstname.value.trim()) params.firstname = searchFirstname.value.trim();
  if (searchLastname.value.trim()) params.lastname = searchLastname.value.trim();
  if (searchIntercessor.value.trim()) params.intercessor_name = searchIntercessor.value.trim();
  loadAndRenderMembers(params);
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
// fields; otherwise falls back to the canonical FIELDS order.
function resolveColumns(headerRow) {
  const normalized = headerRow.map((cell) => cell.trim().toLowerCase());
  const isHeader = FIELDS.every((field) => normalized.includes(field));

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
      if (!value) valid = false;
      payload[field] = value;
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

// ---- Init ----

loadAndRenderMembers();