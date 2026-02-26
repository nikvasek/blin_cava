/* global Telegram */

const tg = window.Telegram?.WebApp;

const SHEET_CSV_URL =
  'https://docs.google.com/spreadsheets/d/e/2PACX-1vRKkNaFq35qpbgc5eI__DJwKFSn3iIZIld1xHIyEBol4DPqTOQz4E5ofZER07gaHU27ngCrKAToU-Cl/pub?gid=1187582404&single=true&output=csv';

function rub(n) {
  const val = Number(n);
  if (!Number.isFinite(val)) return '0.00 Br';
  return `${val.toFixed(2)} Br`;
}

function keyOf(category, title) {
  return `${category}||${title}`;
}

function parseCsvRow(row) {
  const cells = [];
  let cur = '';
  let inQuotes = false;

  for (let i = 0; i < row.length; i += 1) {
    const ch = row[i];
    if (ch === '"') {
      if (inQuotes && row[i + 1] === '"') {
        cur += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (ch === ',' && !inQuotes) {
      cells.push(cur);
      cur = '';
      continue;
    }

    cur += ch;
  }

  cells.push(cur);
  return cells.map(c => c.trim());
}

function parseCsv(text) {
  const rowsText = [];
  let cur = '';
  let inQuotes = false;

  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];

    if (ch === '\r') {
      continue;
    }

    if (ch === '"') {
      if (inQuotes && next === '"') {
        cur += '"';
        i += 1;
        continue;
      }
      inQuotes = !inQuotes;
      cur += ch;
      continue;
    }

    if (ch === '\n' && !inQuotes) {
      if (cur.trim()) rowsText.push(cur);
      cur = '';
      continue;
    }

    cur += ch;
  }

  if (cur.trim()) rowsText.push(cur);
  if (rowsText.length === 0) return [];

  const header = parseCsvRow(rowsText[0]);
  const rows = [];
  for (let i = 1; i < rowsText.length; i += 1) {
    const values = parseCsvRow(rowsText[i]);
    const row = {};
    for (let j = 0; j < header.length; j += 1) {
      row[header[j]] = values[j] ?? '';
    }
    rows.push(row);
  }
  return rows;
}

function rowsToMenu(rows) {
  const byCat = new Map();

  for (const r of rows) {
    const category = String(r.category || '').trim();
    const title = String(r.title || '').trim();
    const description = String(r.description || '').trim();
    const image = String(r.image || '').trim();
    const isActiveRaw = String(r.is_active || '1').trim().toLowerCase();

    if (!category || !title) continue;
    if (['0', 'false', 'no'].includes(isActiveRaw)) continue;

    const priceRaw = String(r.price || '').replace(',', '.');
    const price = Number(priceRaw);
    if (!Number.isFinite(price)) continue;

    if (!byCat.has(category)) byCat.set(category, []);
    byCat.get(category).push({
      title,
      description,
      price,
      image,
    });
  }

  const categories = [];
  for (const [name, items] of byCat.entries()) {
    categories.push({ name, items });
  }

  return { categories };
}

async function loadMenu() {
  const url = new URL(SHEET_CSV_URL);
  url.searchParams.set('v', String(Date.now()));
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error('sheet csv not доступен');
  const text = await res.text();
  const rows = parseCsv(text);
  return rowsToMenu(rows);
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
    // Keep brand red buttons even if Telegram theme provides button colors.
  }

  const subtitleEl = document.getElementById('subtitle');
  const tabsEl = document.getElementById('tabs');
  const gridEl = document.getElementById('grid');
  const homeViewEl = document.getElementById('homeView');
  const menuViewEl = document.getElementById('menuView');
  const searchViewEl = document.getElementById('searchView');
  const cartViewEl = document.getElementById('cartView');
  const orderViewEl = document.getElementById('orderView');
  const categoryGridEl = document.getElementById('categoryGrid');
  const searchInput = document.getElementById('searchInput');
  const searchResultsEl = document.getElementById('searchResults');
  const cartListEl = document.getElementById('cartList');
  const cartTotalEl = document.getElementById('cartTotal');
  const orderListEl = document.getElementById('orderList');
  const checkoutBtn = document.getElementById('checkoutBtn');
  const payBtn = document.getElementById('payBtn');
  const editBtn = document.getElementById('editBtn');
  const navHomeBtn = document.getElementById('navHome');
  const navMenuBtn = document.getElementById('navMenu');
  const navSearchBtn = document.getElementById('navSearch');
  const navCartBtn = document.getElementById('navCart');
  const cartBadgeEl = document.getElementById('cartBadge');
  const typeDeliveryBtn = document.getElementById('typeDelivery');
  const typePickupBtn = document.getElementById('typePickup');
  const addressField = document.getElementById('addressField');
  const addressTitle = document.getElementById('addressTitle');
  const addressLabel = document.getElementById('addressLabel');
  const deliveryTimeField = document.getElementById('deliveryTimeField');
  const deliveryTimeInput = document.getElementById('deliveryTimeInput');
  const nameInput = document.getElementById('nameInput');
  const phoneInput = document.getElementById('phoneInput');
  const addressInput = document.getElementById('addressInput');
  const commentInput = document.getElementById('commentInput');

  const cart = new Map(); // key -> {category,title,price,qty}
  let currentCategory = null;
  let menu = null;
  let view = 'home'; // 'home' | 'menu' | 'search' | 'cart' | 'order'
  let orderType = 'delivery'; // 'delivery' | 'pickup'

  function cartEntries() {
    return Array.from(cart.values()).filter(x => x.qty > 0);
  }

  function cartTotal() {
    return cartEntries().reduce((s, x) => s + x.price * x.qty, 0);
  }

  function hasItems() {
    return cartEntries().length > 0;
  }

  function cartCount() {
    return cartEntries().reduce((s, x) => s + x.qty, 0);
  }

  function setNavActive(key) {
    navHomeBtn?.classList.toggle('active', key === 'home');
    navMenuBtn?.classList.toggle('active', key === 'menu');
    navSearchBtn?.classList.toggle('active', key === 'search');
    navCartBtn?.classList.toggle('active', key === 'cart');
  }

  function setView(next) {
    view = next;
    homeViewEl?.classList.toggle('hidden', view !== 'home');
    menuViewEl?.classList.toggle('hidden', view !== 'menu');
    searchViewEl?.classList.toggle('hidden', view !== 'search');
    cartViewEl?.classList.toggle('hidden', view !== 'cart');
    orderViewEl?.classList.toggle('hidden', view !== 'order');
    tabsEl?.classList.toggle('hidden', view !== 'menu');

    if (subtitleEl) {
      if (view === 'home') subtitleEl.textContent = 'Выберите категорию';
      if (view === 'menu') subtitleEl.textContent = 'Выберите блюда и количество';
      if (view === 'search') subtitleEl.textContent = 'Поиск по названию блюда';
      if (view === 'cart') subtitleEl.textContent = 'Ваш выбор';
      if (view === 'order') subtitleEl.textContent = 'Проверьте заказ и заполните доставку';
    }

    setNavActive(view === 'order' ? 'cart' : view);
    updateCartTotals();
    updatePayBtn();
  }

  function updateCartBadge() {
    if (!cartBadgeEl) return;
    const count = cartCount();
    cartBadgeEl.textContent = String(count);
    cartBadgeEl.classList.toggle('hidden', count === 0);
  }

  function updateCartTotals() {
    const total = cartTotal();
    if (cartTotalEl) cartTotalEl.textContent = rub(total);
    if (checkoutBtn) {
      checkoutBtn.textContent = hasItems() ? `Оформить · ${rub(total)}` : 'Оформить';
      checkoutBtn.disabled = !hasItems();
    }
  }

  function updatePayBtn() {
    if (!payBtn) return;
    payBtn.textContent = `Оформить · ${rub(cartTotal())}`;
    payBtn.disabled = !isFormValid();
  }

  function isFormValid() {
    if (!hasItems()) return false;
    const name = (nameInput?.value || '').trim();
    const phone = (phoneInput?.value || '').trim();
    if (name.length < 2) return false;
    if (phone.length < 6) return false;
    if (orderType === 'delivery') {
      const deliveryTime = (deliveryTimeInput?.value || '').trim();
      const address = (addressInput?.value || '').trim();
      if (deliveryTime.length < 2) return false;
      if (address.length < 6) return false;
    } else {
      const pickupTime = (addressInput?.value || '').trim();
      if (pickupTime.length < 2) return false;
    }
    return true;
  }

  function setOrderType(next) {
    orderType = next;
    const isDelivery = orderType === 'delivery';
    document.documentElement.dataset.orderType = orderType;
    if (typeDeliveryBtn) typeDeliveryBtn.classList.toggle('active', isDelivery);
    if (typePickupBtn) typePickupBtn.classList.toggle('active', !isDelivery);
    if (addressField) addressField.classList.toggle('hidden', false);
    if (addressTitle) addressTitle.textContent = isDelivery ? 'Доставка' : 'Самовывоз';
    if (addressLabel) addressLabel.textContent = isDelivery ? 'Адрес доставки' : 'Время самовывоза';
    if (addressInput) {
      addressInput.placeholder = isDelivery ? 'Улица, дом, кв.' : 'Например: 18:30';
      addressInput.autocomplete = isDelivery ? 'street-address' : 'off';
    }
    if (deliveryTimeField) {
      deliveryTimeField.classList.toggle('hidden', !isDelivery);
      deliveryTimeField.toggleAttribute('hidden', !isDelivery);
      if (isDelivery) {
        deliveryTimeField.style.removeProperty('display');
      } else {
        deliveryTimeField.style.setProperty('display', 'none', 'important');
      }
    }
    if (!isDelivery && deliveryTimeInput) deliveryTimeInput.value = '';
    updatePayBtn();
  }

  function wireValidation() {
    const onChange = () => {
      updatePayBtn();
    };
    nameInput?.addEventListener('input', onChange);
    phoneInput?.addEventListener('input', onChange);
    addressInput?.addEventListener('input', onChange);
    deliveryTimeInput?.addEventListener('input', onChange);
    commentInput?.addEventListener('input', onChange);
  }

  function setQty(category, item, qty) {
    const k = keyOf(category.name, item.title);
    const prev = cart.get(k) || {
      category: category.name,
      title: item.title,
      price: item.price,
      qty: 0,
      image: item.image || '',
      description: item.description || '',
    };
    prev.qty = Math.max(0, qty);
    cart.set(k, prev);
    renderMenu();
    renderSearch();
    renderCart();
    renderOrder();
    updateCartBadge();
    updateCartTotals();
    updatePayBtn();
  }

  function qtyOf(category, item) {
    const k = keyOf(category.name, item.title);
    return cart.get(k)?.qty || 0;
  }

  function categoryImage(category) {
    const withImage = category.items.find(x => x.image);
    return withImage?.image || '';
  }

  function buildMenuCard(category, item, showCategory) {
    const q = qtyOf(category, item);

    const card = createEl('div', 'menu-card');

    const media = createEl('div', 'menu-media');
    if (item.image) {
      const img = createEl('img', 'menu-img');
      img.alt = item.title;
      img.loading = 'lazy';
      img.src = item.image;
      media.appendChild(img);
    } else {
      const emoji = createEl('div', 'menu-emoji', emojiFor(category.name));
      media.appendChild(emoji);
    }

    const body = createEl('div', 'menu-body');
    body.appendChild(createEl('div', 'menu-name', item.title));
    if (showCategory) {
      body.appendChild(createEl('div', 'menu-meta', category.name));
    }
    if (item.description) {
      body.appendChild(createEl('div', 'menu-desc', item.description));
    }

    const right = createEl('div', 'menu-right');
    right.appendChild(createEl('div', 'price-pill', rub(item.price)));

    const actions = createEl('div', 'menu-actions');
    if (q <= 0) {
      const addBtn = createEl('button', 'add-pill', 'Добавить');
      addBtn.type = 'button';
      addBtn.addEventListener('click', () => {
        setQty(category, item, 1);
      });
      actions.appendChild(addBtn);
    } else {
      const pm = createEl('div', 'qty-row');
      const dec = createEl('button', 'qty-btn', '−');
      const qty = createEl('div', 'qty-num', String(q));
      const inc = createEl('button', 'qty-btn', '+');
      dec.type = 'button';
      inc.type = 'button';
      dec.addEventListener('click', () => {
        setQty(category, item, q - 1);
      });
      inc.addEventListener('click', () => {
        setQty(category, item, q + 1);
      });
      pm.appendChild(dec);
      pm.appendChild(qty);
      pm.appendChild(inc);
      actions.appendChild(pm);
    }

    right.appendChild(actions);

    card.appendChild(media);
    card.appendChild(body);
    card.appendChild(right);
    return card;
  }

  function renderCategories() {
    if (!categoryGridEl) return;
    categoryGridEl.innerHTML = '';

    for (const category of menu.categories) {
      const btn = createEl('button', 'category-card');
      btn.type = 'button';
      const media = createEl('div', 'category-media');
      const imgUrl = categoryImage(category);
      if (imgUrl) {
        const img = createEl('img', 'category-img');
        img.alt = category.name;
        img.loading = 'lazy';
        img.src = imgUrl;
        media.appendChild(img);
      } else {
        media.appendChild(createEl('div', 'menu-emoji', emojiFor(category.name)));
      }
      btn.appendChild(media);
      btn.appendChild(createEl('div', 'category-name', category.name));
      btn.addEventListener('click', () => {
        currentCategory = category.name;
        renderTabs();
        renderMenu();
        setView('menu');
      });
      categoryGridEl.appendChild(btn);
    }
  }

  function renderSearch() {
    if (!searchResultsEl) return;
    const q = (searchInput?.value || '').trim().toLowerCase();
    searchResultsEl.innerHTML = '';

    if (!q) {
      searchResultsEl.appendChild(createEl('div', 'tile', 'Введите запрос для поиска'));
      return;
    }

    const matches = [];
    for (const category of menu.categories) {
      for (const item of category.items) {
        if (String(item.title).toLowerCase().includes(q)) {
          matches.push({ category, item });
        }
      }
    }

    if (matches.length === 0) {
      searchResultsEl.appendChild(createEl('div', 'tile', 'Ничего не найдено'));
      return;
    }

    for (const entry of matches) {
      searchResultsEl.appendChild(buildMenuCard(entry.category, entry.item, true));
    }
  }

  function renderCart() {
    if (!cartListEl) return;
    cartListEl.innerHTML = '';

    const entries = cartEntries();
    if (entries.length === 0) {
      cartListEl.appendChild(createEl('div', 'tile', 'Корзина пуста'));
      return;
    }

    for (const x of entries) {
      const row = createEl('div', 'order-row');
      if (x.image) {
        const media = createEl('div', 'order-emoji');
        const img = createEl('img', 'order-img');
        img.alt = x.title;
        img.loading = 'lazy';
        img.src = x.image;
        media.appendChild(img);
        row.appendChild(media);
      } else {
        row.appendChild(createEl('div', 'order-emoji', emojiFor(x.category)));
      }

      const center = createEl('div');
      center.appendChild(createEl('div', 'order-name', `${x.title} ×${x.qty}`));
      center.appendChild(createEl('div', 'order-sub', x.category));
      row.appendChild(center);

      row.appendChild(createEl('div', 'order-price', rub(x.price * x.qty)));
      cartListEl.appendChild(row);
    }
  }

  function renderMenu() {
    gridEl.innerHTML = '';
    const category = menu.categories.find(c => c.name === currentCategory);
    if (!category) return;

    for (const item of category.items) {
      gridEl.appendChild(buildMenuCard(category, item, false));
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
      if (x.image) {
        const media = createEl('div', 'order-emoji');
        const img = createEl('img', 'order-img');
        img.alt = x.title;
        img.loading = 'lazy';
        img.src = x.image;
        media.appendChild(img);
        row.appendChild(media);
      } else {
        row.appendChild(createEl('div', 'order-emoji', emojiFor(x.category)));
      }

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

  editBtn?.addEventListener('click', () => {
    setView('menu');
  });

  navHomeBtn?.addEventListener('click', () => {
    setView('home');
  });

  navMenuBtn?.addEventListener('click', () => {
    setView('menu');
  });

  navSearchBtn?.addEventListener('click', () => {
    setView('search');
    searchInput?.focus();
    renderSearch();
  });

  navCartBtn?.addEventListener('click', () => {
    renderCart();
    setView('cart');
  });

  checkoutBtn?.addEventListener('click', () => {
    if (!hasItems()) return;
    renderOrder();
    setView('order');
    nameInput?.focus();
  });

  typeDeliveryBtn?.addEventListener('click', () => {
    setOrderType('delivery');
  });

  typePickupBtn?.addEventListener('click', () => {
    setOrderType('pickup');
  });

  payBtn?.addEventListener('click', () => {
    if (!isFormValid()) return;

    const items = Array.from(cart.values())
      .filter(x => x.qty > 0)
      .map(x => ({
        category: x.category,
        title: x.title,
        description: x.description || '',
        price: x.price,
        qty: x.qty,
      }));

    if (items.length === 0) return;

    const name = (nameInput?.value || '').trim();
    const phone = (phoneInput?.value || '').trim();
    const address = (addressInput?.value || '').trim();
    const deliveryTime = (deliveryTimeInput?.value || '').trim();
    const comment = (commentInput?.value || '').trim();

    const payload = JSON.stringify({
      order_type: orderType,
      name,
      phone,
      address: orderType === 'delivery' ? address : '',
      delivery_time: orderType === 'delivery' ? deliveryTime : '',
      pickup_time: orderType === 'pickup' ? address : '',
      comment,
      items,
    });

    if (tg) {
      tg.sendData(payload);
      tg.close();
    } else {
      alert(payload);
    }
  });

  searchInput?.addEventListener('input', () => {
    renderSearch();
  });

  loadMenu()
    .then((m) => {
      menu = m;
      currentCategory = menu.categories[0]?.name || null;
      renderTabs();
      renderMenu();
      renderCategories();
      renderSearch();
      renderCart();
      renderOrder();
      wireValidation();
      updateCartBadge();
      setView('home');
      setOrderType('delivery');
    })
    .catch((err) => {
      console.error('Failed to load menu', err);
      document.getElementById('subtitle').textContent = 'Не удалось загрузить меню';
    });
}

document.addEventListener('DOMContentLoaded', main);
