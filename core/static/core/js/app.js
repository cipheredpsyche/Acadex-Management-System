// Acadex front-end behaviour (plain JavaScript, no libraries)
(function () {
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* ---------- sidebar on phones ---------- */
  var menuBtn = $('#menuBtn');
  if (menuBtn) menuBtn.addEventListener('click', function () { $('#sidebar').classList.toggle('open'); });

  /* ---------- flash messages fade out ---------- */
  $$('[data-flash]').forEach(function (el) {
    setTimeout(function () { el.classList.add('hide'); }, 4500);
  });

  /* ---------- login: show / hide password ---------- */
  $$('[data-toggle-pw]').forEach(function (b) {
    b.addEventListener('click', function () {
      var input = b.parentNode.querySelector('input');
      input.type = input.type === 'password' ? 'text' : 'password';
    });
  });

  /* ---------- social buttons (design placeholders) ---------- */
  var toast = $('#toast');
  $$('[data-soon]').forEach(function (b) {
    b.addEventListener('click', function () {
      if (!toast) return;
      toast.textContent = 'Account sign-in is not available yet. Please use your School ID or email.';
      toast.classList.add('show');
      setTimeout(function () { toast.classList.remove('show'); }, 2800);
    });
  });

  /* ---------- popups (<dialog>) ---------- */
  function openDialog(d) { if (d.showModal) d.showModal(); else d.setAttribute('open', ''); }
  $$('dialog').forEach(function (d) {
    $$('[data-close]', d).forEach(function (b) { b.addEventListener('click', function () { d.close(); }); });
    d.addEventListener('click', function (e) { if (e.target === d) d.close(); });
    if (d.hasAttribute('data-autoopen')) openDialog(d);
  });
  $$('[data-open-dialog]').forEach(function (b) {
    b.addEventListener('click', function () { openDialog(document.getElementById(b.dataset.openDialog)); });
  });

  /* ---------- the shared "Are you sure?" popup ---------- */
  var confirmDialog = $('#confirmDialog');
  $$('[data-confirm]').forEach(function (b) {
    b.addEventListener('click', function () {
      $('#confirmTitle').textContent = b.dataset.confirmTitle || 'Are you sure?';
      $('#confirmText').textContent = b.dataset.confirmText || '';
      $('#confirmYes').textContent = b.dataset.confirmYes || 'Yes';
      $('#confirmForm').action = b.dataset.confirmAction;
      var kebab = b.closest('details'); if (kebab) kebab.open = false;
      openDialog(confirmDialog);
    });
  });

  /* ---------- auto-submit (photo upload) ---------- */
  $$('[data-autosubmit]').forEach(function (i) {
    i.addEventListener('change', function () { i.form.submit(); });
  });

  /* ---------- close the ⋮ menus when clicking elsewhere ---------- */
  document.addEventListener('click', function (e) {
    $$('details.kebab[open]').forEach(function (d) { if (!d.contains(e.target)) d.open = false; });
  });

  /* ---------- calendar fields: click opens the calendar ---------- */
  function wireDate(input) {
    input.addEventListener('click', function () { try { input.showPicker(); } catch (e) { /* older browser */ } });
  }
  $$('input[type=date]').forEach(wireDate);

  /* ================= MY TASKS: Add Task / Edit Task popup ================= */
  var taskDialog = $('#taskDialog');
  if (taskDialog) {
    var tf = $('#taskForm');
    var setTask = function (action, head, btn, subject, title, due, status) {
      tf.action = action;
      $('#taskModalTitle').textContent = head;
      $('#taskSubmit').textContent = btn;
      $('#t-subject').value = subject; $('#t-title').value = title;
      $('#t-due').value = due; $('#t-status').value = status;
      openDialog(taskDialog);
    };
    $$('[data-add-task]').forEach(function (b) {
      b.addEventListener('click', function () {
        setTask(b.dataset.action, 'Add Task', 'Add Task', '', '', '', b.dataset.defaultStatus || 'Pending');
      });
    });
    $$('[data-edit-task]').forEach(function (b) {
      b.addEventListener('click', function () {
        setTask(b.dataset.action, 'Edit Task', 'Save Changes', b.dataset.subject, b.dataset.title,
                b.dataset.due, b.dataset.status);
      });
    });
  }

  /* ================= ADMIN: Add / Edit Student popup ================= */
  var studentDialog = $('#studentDialog');
  if (studentDialog) {
    var sf = $('#studentForm');
    var dob = $('#id_birthdate');
    var ageField = $('#ageField');
    var qpM = $('#qpMonth'), qpD = $('#qpDay'), qpY = $('#qpYear');
    var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
                  'September', 'October', 'November', 'December'];

    // fill the quick-pick drop-downs
    function opt(sel, value, text) { var o = document.createElement('option'); o.value = value; o.textContent = text; sel.appendChild(o); }
    opt(qpM, '', 'Month'); MONTHS.forEach(function (m, i) { opt(qpM, String(i + 1), m); });
    opt(qpD, '', 'Day'); for (var d = 1; d <= 31; d++) opt(qpD, String(d), String(d));
    opt(qpY, '', 'Year'); for (var y = new Date().getFullYear(); y >= 1960; y--) opt(qpY, String(y), String(y));

    function pad(n) { return (n < 10 ? '0' : '') + n; }

    // date input -> age + quick-pick drop-downs
    function fromDateInput() {
      var v = dob.value;
      if (!v) { ageField.value = ''; qpM.value = qpD.value = qpY.value = ''; return; }
      var p = v.split('-').map(Number);
      qpY.value = String(p[0]); qpM.value = String(p[1]); qpD.value = String(p[2]);
      var t = new Date(), age = t.getFullYear() - p[0];
      if (t.getMonth() + 1 < p[1] || (t.getMonth() + 1 === p[1] && t.getDate() < p[2])) age--;
      ageField.value = age >= 0 ? age + ' years old' : '';
    }
    // quick-pick drop-downs -> date input
    function fromQuickPick() {
      if (!qpY.value || !qpM.value || !qpD.value) return;
      var yy = +qpY.value, mm = +qpM.value, dd = +qpD.value;
      var maxDay = new Date(yy, mm, 0).getDate();           // e.g. February has 28/29
      if (dd > maxDay) { dd = maxDay; qpD.value = String(dd); }
      var picked = yy + '-' + pad(mm) + '-' + pad(dd);
      if (dob.max && picked > dob.max) picked = dob.max;      // no future birthdays
      dob.value = picked;
      fromDateInput();
    }
    dob.addEventListener('input', fromDateInput);
    dob.addEventListener('change', fromDateInput);
    [qpM, qpD, qpY].forEach(function (s) { s.addEventListener('change', fromQuickPick); });
    $$('[data-open-date]').forEach(function (b) {
      b.addEventListener('click', function () { try { dob.showPicker(); } catch (e) { dob.focus(); } });
    });

    function setField(name, value) { var el = $('#id_' + name); if (el) el.value = value; }
    var FIELDS = ['full_name', 'gender', 'birthdate', 'address', 'email', 'contact_number', 'course',
                  'academic_year', 'year_level', 'section', 'school_id'];

    $$('[data-add-student]').forEach(function (b) {
      b.addEventListener('click', function () {
        sf.action = b.dataset.action;
        $('#studentModalTitle').textContent = 'Add New Student';
        FIELDS.forEach(function (f) { setField(f, ''); });
        setField('password', '');
        $('#id_password').required = true;
        $('#pwLabel').textContent = 'Password';
        fromDateInput();
        openDialog(studentDialog);
      });
    });
    $$('[data-edit-student]').forEach(function (b) {
      b.addEventListener('click', function () {
        var data = JSON.parse(b.dataset.student);
        sf.action = b.dataset.action;
        $('#studentModalTitle').textContent = 'Edit Student';
        FIELDS.forEach(function (f) { setField(f, data[f] || ''); });
        setField('password', '');
        $('#id_password').required = false;
        $('#pwLabel').textContent = 'New Password (leave blank to keep the current one)';
        var kebab = b.closest('details'); if (kebab) kebab.open = false;
        fromDateInput();
        openDialog(studentDialog);
      });
    });
    fromDateInput();     // when the popup re-opens after a validation error
  }
})();
