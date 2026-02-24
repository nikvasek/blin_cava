/* global Telegram */

const tg = window.Telegram?.WebApp;

function rub(n) {
  return `${n} ₽`;
}

function keyOf(category, title) {
  return `${category}||${title}`;
}

async function loadMenu() {
  const res = await fetch('../menu.json', { cache: 'no-store' });
  if (!res.ok) throw new Error('menu.json not found');
  return await res.json();
}

function createEl(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
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

  const tabsEl = document.getElementById('tabs');
  const listEl = document.getElementById('list');
  const cartItemsEl = document.getElementById('cartItems');
  const cartTotalEl = document.getElementById('cartTotal');
  const sendBtn = document.getElementById('sendBtn');

  const cart = new Map(); // key -> {category,title,price,qty}
  let currentCategory = null;
  let menu = null;

  function renderCart() {
    const entries = Array.from(cart.values()).filter(x => x.qty > 0);
    if (entries.length === 0) {
      cartItemsEl.textContent = 'Пусто';
      cartTotalEl.textContent = rub(0);
      sendBtn.disabled = true;
      return;
    }

    const total = entries.reduce((s, x) => s + x.price * x.qty, 0);
    cartTotalEl.textContent = rub(total);
    cartItemsEl.textContent = entries.map(x => `${x.title} ×${x.qty}`).join(' · ');
    sendBtn.disabled = false;
  }

  function setQty(category, item, qty) {
    const k = keyOf(category.name, item.title);
    const prev = cart.get(k) || { category: category.name, title: item.title, price: item.price, qty: 0 };
    prev.qty = Math.max(0, qty);
    cart.set(k, prev);
    renderCart();
  }

  function qtyOf(category, item) {
    const k = keyOf(category.name, item.title);
    return cart.get(k)?.qty || 0;
  }

  function renderList() {
    listEl.innerHTML = '';
    const category = menu.categories.find(c => c.name === currentCategory);
    if (!category) return;

    for (const item of category.items) {
      const card = createEl('div', 'card');
      const row = createEl('div', 'row');

      const left = createEl('div');
      const title = createEl('div', 'item-title', item.title);
      left.appendChild(title);

      const price = createEl('div', 'item-price', rub(item.price));

      row.appendChild(left);
      row.appendChild(price);
      card.appendChild(row);

      if (item.description) {
        card.appendChild(createEl('div', 'item-desc', item.description));
      }

      const controls = createEl('div', 'controls');
      const counter = createEl('div', 'counter');
      const dec = createEl('button', 'icon-btn', '−');
      const qty = createEl('div', 'qty', String(qtyOf(category, item)));
      const inc = createEl('button', 'icon-btn', '+');

      dec.addEventListener('click', () => {
        const next = qtyOf(category, item) - 1;
        setQty(category, item, next);
        qty.textContent = String(qtyOf(category, item));
      });

      inc.addEventListener('click', () => {
        const next = qtyOf(category, item) + 1;
        setQty(category, item, next);
        qty.textContent = String(qtyOf(category, item));
      });

      counter.appendChild(dec);
      counter.appendChild(qty);
      counter.appendChild(inc);
      controls.appendChild(counter);
      card.appendChild(controls);

      listEl.appendChild(card);
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
        renderList();
      });
      tabsEl.appendChild(btn);
    }
  }

  sendBtn.addEventListener('click', () => {
    const items = Array.from(cart.values())
      .filter(x => x.qty > 0)
      .map(x => ({ category: x.category, title: x.title, qty: x.qty }));

    if (items.length === 0) return;

    const payload = JSON.stringify({ items });

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
      renderList();
      renderCart();
    })
    .catch(() => {
      document.getElementById('subtitle').textContent = 'Не удалось загрузить меню';
    });
}

document.addEventListener('DOMContentLoaded', main);
