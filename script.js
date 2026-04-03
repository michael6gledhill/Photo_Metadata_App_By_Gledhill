(() => {
  const body = document.body;
  const sidebar = document.getElementById('sidebar');
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebarClose = document.getElementById('sidebarClose');
  const overlay = document.getElementById('sidebarOverlay');
  const searchInput = document.getElementById('searchInput');
  const searchButton = document.getElementById('searchButton');

  const openSidebar = () => {
    sidebar?.classList.add('is-open');
    overlay?.classList.add('is-open');
    body.classList.add('sidebar-open');
  };

  const closeSidebar = () => {
    sidebar?.classList.remove('is-open');
    overlay?.classList.remove('is-open');
    body.classList.remove('sidebar-open');
  };

  sidebarToggle?.addEventListener('click', openSidebar);
  sidebarClose?.addEventListener('click', closeSidebar);
  overlay?.addEventListener('click', closeSidebar);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeSidebar();
  });

  const searchableElements = () => Array.from(document.querySelectorAll('.searchable'));

  const applySearch = () => {
    const query = (searchInput?.value || '').trim().toLowerCase();
    const items = searchableElements();
    let firstMatch = null;

    items.forEach((el) => {
      const text = ((el.getAttribute('data-searchable-text') || el.textContent || '')).toLowerCase();
      const match = !query || text.includes(query);
      el.hidden = !match;
      if (match && !firstMatch) firstMatch = el;
    });

    if (searchButton && query && firstMatch) {
      firstMatch.classList.add('search-highlight');
      window.setTimeout(() => firstMatch?.classList.remove('search-highlight'), 900);
      firstMatch.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  searchInput?.addEventListener('input', applySearch);
  searchButton?.addEventListener('click', applySearch);

  searchableElements().forEach((el) => {
    if (!el.hasAttribute('data-searchable-text')) {
      el.setAttribute('data-searchable-text', el.textContent || '');
    }
  });
})();
