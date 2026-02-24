/* global Telegram */

const tg = window.Telegram?.WebApp;

function rub(n) {
  return `${n} ₽`;
}

function keyOf(category, title) {
  return `${category}||${title}`;
}

async function loadMenu() {
  const url = new URL('menu.json', window.location.href);
  url.searchParams.set('v', String(Date.now()));
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error('menu.json not found');
  return await res.json();
}

function createEl(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}

function emojiFor(categoryName) {
  const s = String(categoryName || '').toLowerCase();
  if (s.includes('напит')) return '🥤';
  if (s.includes('закус')) return '🥗';
  if (s.includes('десерт')) return '🍰';
  if (s.includes('суп')) return '🥣';
  return '🍽️';
}

function main() {
  if (tg) {
    tg.ready();
    tg.expand();

    const theme = tg.themeParams || {};
    if (theme.bg_color) document.documentElement.style.setProperty('--bg', theme.bg_color);
    if (theme.text_color) document.documentElement.style.setProperty('--text', theme.text_color);
    if (theme.hint_color) document.documentElement.style.setProperty('--muted', theme.hint_color);
    if (theme.button_color) document.documentElement.style.setProperty('--btn', theme.button_color);
    if (theme.button_text_color) document.documentElement.style.setProperty('--btnText', theme.button_text_color);
  }

  const subtitleEl = document.getElementById('subtitle');
  const tabsEl = document.getElementById('tabs');
  const gridEl = document.getElementById('grid');
  const menuViewEl = document.getElementById('menuView');
  const orderViewEl = document.getElementById('orderView');
  const orderListEl = document.getElementById('orderList');
  const viewOrderBtn = document.getElementById('viewOrderBtn');
  const payBtn = document.getElementById('payBtn');
  const editBtn = document.getElementById('editBtn');
  const nameInput = document.getElementById('nameInput');
  const phoneInput = document.getElementById('phoneInput');
  const addressInput = document.getElementById('addressInput');
  const commentInput = document.getElementById('commentInput');

  const cart = new Map(); // key -> {category,title,price,qty}
  let currentCategory = null;
  let menu = null;
  let view = 'menu'; // 'menu' | 'order'

  function cartEntries() {
    return Array.from(cart.values()).filter(x => x.qty > 0);
  }

  function cartTotal() {
    return cartEntries().reduce((s, x) => s + x.price * x.qty, 0);
  }

  function hasItems() {
    return cartEntries().length > 0;
  }

  function setView(next) {
    view = next;
    if (view === 'menu') {
      menuViewEl?.classList.remove('hidden');
      orderViewEl?.classList.add('hidden');
      if (subtitleEl) subtitleEl.textContent = 'Выберите блюда и количество';
    } else {
      menuViewEl?.classList.add('hidden');
      orderViewEl?.classList.remove('hidden');
      if (subtitleEl) subtitleEl.textContent = 'Проверьте заказ и заполните доставку';
    }
    updateFooter();
  }

  function updateFooter() {
    const total = cartTotal();
    if (view === 'menu') {
      payBtn?.classList.add('hidden');
      if (hasItems()) {
        viewOrderBtn?.classList.remove('hidden');
        viewOrderBtn.textContent = `Посмотреть заказ · ${rub(total)}`;
        viewOrderBtn.disabled = false;
      } else {
        viewOrderBtn?.classList.add('hidden');
        viewOrderBtn.disabled = true;
      }
      return;
    }

    viewOrderBtn?.classList.add('hidden');
    payBtn?.classList.remove('hidden');
    payBtn.textContent = `Оформить · ${rub(total)}`;
    payBtn.disabled = !isFormValid();
  }

  function isFormValid() {
    if (!hasItems()) return false;
    const name = (nameInput?.value || '').trim();
    const phone = (phoneInput?.value || '').trim();
    const address = (addressInput?.value || '').trim();
    if (name.length < 2) return false;
    if (phone.length < 6) return false;
    if (address.length < 6) return false;
    return true;
  }

  function wireValidation() {
    const onChange = () => {
      updateFooter();
    };
    nameInput?.addEventListener('input', onChange);
    phoneInput?.addEventListener('input', onChange);
    addressInput?.addEventListener('input', onChange);
    commentInput?.addEventListener('input', onChange);
  }

  function setQty(category, item, qty) {
    const k = keyOf(category.name, item.title);
    const prev = cart.get(k) || { category: category.name, title: item.title, price: item.price, qty: 0 };
    prev.qty = Math.max(0, qty);
    cart.set(k, prev);
    renderMenu();
    renderOrder();
    updateFooter();
  }

  function qtyOf(category, item) {
    const k = keyOf(category.name, item.title);
    return cart.get(k)?.qty || 0;
  }

  function renderMenu() {
    gridEl.innerHTML = '';
    const category = menu.categories.find(c => c.name === currentCategory);
    if (!category) return;

    for (const item of category.items) {
      const q = qtyOf(category, item);

      const tile = createEl('div', 'tile');
      const top = createEl('div', 'tile-top');
      const emoji = createEl('div', 'tile-emoji', emojiFor(category.name));
      top.appendChild(emoji);

      if (q > 0) {
        top.appendChild(createEl('div', 'badge', String(q)));
      }

      const title = createEl('div', 'tile-title', item.title);
      const price = createEl('div', 'tile-price', rub(item.price));
      const actions = createEl('div', 'tile-actions');

      if (q <= 0) {
        const addBtn = createEl('button', 'add-btn', 'ADD');
        addBtn.type = 'button';
        addBtn.addEventListener('click', () => {
          setQty(category, item, 1);
        });
        actions.appendChild(addBtn);
      } else {
        const pm = createEl('div', 'pm');
        const dec = createEl('button', 'pm-btn', '−');
        const inc = createEl('button', 'pm-btn', '+');
        dec.type = 'button';
        inc.type = 'button';
        dec.addEventListener('click', () => {
          setQty(category, item, q - 1);
        });
        inc.addEventListener('click', () => {
          setQty(category, item, q + 1);
        });
        pm.appendChild(dec);
        pm.appendChild(inc);
        actions.appendChild(pm);
      }

      tile.appendChild(top);
      tile.appendChild(title);
      tile.appendChild(price);
      tile.appendChild(actions);

      gridEl.appendChild(tile);
    }
  }

  function renderOrder() {
    if (!orderListEl) return;
    orderListEl.innerHTML = '';

    const entries = cartEntries();
    if (entries.length === 0) {
      orderListEl.appendChild(createEl('div', 'tile', 'Корзина пуста'));
      return;
    }

    for (const x of entries) {
      const row = createEl('div', 'order-row');
      row.appendChild(createEl('div', 'order-emoji', emojiFor(x.category)));

      const center = createEl('div');
      center.appendChild(createEl('div', 'order-name', `${x.title} ×${x.qty}`));
      center.appendChild(createEl('div', 'order-sub', x.category));
      row.appendChild(center);

      row.appendChild(createEl('div', 'order-price', rub(x.price * x.qty)));
      orderListEl.appendChild(row);
    }
  }

  function renderTabs() {
    tabsEl.innerHTML = '';
    for (const c of menu.categories) {
      const btn = createEl('button', 'tab', c.name);
      if (c.name === currentCategory) btn.classList.add('active');
      btn.addEventListener('click', () => {
        currentCategory = c.name;
        renderTabs();
        renderMenu();
      });
      tabsEl.appendChild(btn);
    }
  }

  viewOrderBtn?.addEventListener('click', () => {
    if (!hasItems()) return;
    renderOrder();
    setView('order');
    nameInput?.focus();
  });

  editBtn?.addEventListener('click', () => {
    setView('menu');
  });

  payBtn?.addEventListener('click', () => {
    if (!isFormValid()) return;

    const items = Array.from(cart.values())
      .filter(x => x.qty > 0)
      .map(x => ({ category: x.category, title: x.title, qty: x.qty }));

    if (items.length === 0) return;

    const name = (nameInput?.value || '').trim();
    const phone = (phoneInput?.value || '').trim();
    const address = (addressInput?.value || '').trim();
    const comment = (commentInput?.value || '').trim();

    const payload = JSON.stringify({ name, phone, address, comment, items });

    if (tg) {
      tg.sendData(payload);
      tg.close();
    } else {
      alert(payload);
    }
  });

  loadMenu()
    .then((m) => {
      menu = m;
      currentCategory = menu.categories[0]?.name || null;
      renderTabs();
      renderMenu();
      renderOrder();
      wireValidation();
      setView('menu');
    })
    .catch((err) => {
      console.error('Failed to load menu', err);
      document.getElementById('subtitle').textContent = 'Не удалось загрузить меню';
    });
}

document.addEventListener('DOMContentLoaded', main);
