// Happy Local Adventure ERP - Client-Side App Helpers

function hlaToggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  try { localStorage.setItem('hla-theme', next); } catch (e) {}
}

function hlaToggleNavLayout() {
  const current = document.documentElement.getAttribute('data-nav') || 'topbar';
  const next = current === 'topbar' ? 'sidebar' : 'topbar';
  document.documentElement.setAttribute('data-nav', next);
  try { localStorage.setItem('hla-nav-layout', next); } catch (e) {}
}

function hlaToggleMobileNav() {
  const nav = document.getElementById('main-nav');
  const backdrop = document.querySelector('.mobile-nav-backdrop');
  if (!nav) return;
  const isOpen = nav.classList.contains('mobile-open');
  if (isOpen) {
    hlaCloseMobileNav();
  } else {
    nav.classList.add('mobile-open');
    if (backdrop) backdrop.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function hlaCloseMobileNav() {
  const nav = document.getElementById('main-nav');
  const backdrop = document.querySelector('.mobile-nav-backdrop');
  if (nav) nav.classList.remove('mobile-open');
  if (backdrop) backdrop.classList.remove('active');
  document.body.style.overflow = '';
}

// Close mobile nav on escape key press
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    hlaCloseMobileNav();
  }
});

function showToast(message, type = 'info') {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.25s ease';
    setTimeout(() => toast.remove(), 250);
  }, 3000);
}

// Client-Side Instant Table Filter & Search
function setupTableFilter(searchInputId, tableSelector, statusAttribute = 'data-status') {
  const searchInput = document.getElementById(searchInputId);
  const table = document.querySelector(tableSelector);
  if (!table) return;

  const rows = table.querySelectorAll('tbody tr, tr:not(:first-child)');

  function filterRows() {
    const query = (searchInput ? searchInput.value : '').toLowerCase().trim();
    const activeTab = document.querySelector('.tabs button.active, .tabs a.active');
    const filterStatus = activeTab ? (activeTab.getAttribute('data-filter') || 'all').toLowerCase() : 'all';

    let visibleCount = 0;
    rows.forEach(row => {
      // Ignore header or empty-state row
      if (row.querySelector('th') || row.classList.contains('no-filter')) return;

      const text = row.textContent.toLowerCase();
      const status = (row.getAttribute(statusAttribute) || '').toLowerCase();

      const matchesSearch = !query || text.includes(query);
      const matchesStatus = filterStatus === 'all' || status.includes(filterStatus);

      if (matchesSearch && matchesStatus) {
        row.style.display = '';
        visibleCount++;
      } else {
        row.style.display = 'none';
      }
    });

    const emptyMsg = document.getElementById('table-empty-msg');
    if (emptyMsg) {
      emptyMsg.style.display = visibleCount === 0 ? '' : 'none';
    }
  }

  if (searchInput) {
    searchInput.addEventListener('input', filterRows);
  }

  const tabButtons = document.querySelectorAll('.tabs button[data-filter]');
  tabButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
      tabButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      filterRows();
    });
  });
}

document.addEventListener('DOMContentLoaded', () => {
  setupTableFilter('booking-search', '#bookings-table');
  setupTableFilter('invoice-search', '#invoices-table');
  setupTableFilter('partner-search', '#partners-table');
});
