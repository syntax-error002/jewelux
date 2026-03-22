/* ═══════════════════════════════════════════════════════════════
   JEWELUX — Main JavaScript
   ═══════════════════════════════════════════════════════════════ */

'use strict';

// ─── Toast System ─────────────────────────────────────────────
const Toast = {
  container: null,
  init() {
    this.container = document.createElement('div');
    this.container.className = 'toast-container';
    document.body.appendChild(this.container);
  },
  show(message, type = 'info', duration = 3500) {
    const icons = { success: '✓', error: '✕', info: '◆' };
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span>${icons[type] || icons.info}</span><span>${message}</span>`;
    this.container.appendChild(toast);
    setTimeout(() => {
      toast.classList.add('hiding');
      toast.addEventListener('animationend', () => toast.remove());
    }, duration);
  }
};

// ─── Flash auto-dismiss ────────────────────────────────────────
function initFlash() {
  document.querySelectorAll('.flash').forEach(el => {
    const btn = el.querySelector('.flash-close');
    if (btn) btn.addEventListener('click', () => el.remove());
    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transform = 'translateX(120%)';
      setTimeout(() => el.remove(), 400);
    }, 5000);
  });
}

// ─── Header scroll behaviour ───────────────────────────────────
function initHeader() {
  const header = document.querySelector('.header');
  if (!header) return;
  const isSolid = header.classList.contains('solid');
  if (isSolid) return;
  const check = () => {
    if (window.scrollY > 60) header.classList.add('scrolled');
    else header.classList.remove('scrolled');
  };
  window.addEventListener('scroll', check, { passive: true });
  check();
}

// ─── Mobile Menu ───────────────────────────────────────────────
function initMobileMenu() {
  const btn = document.getElementById('hamburger');
  const menu = document.getElementById('mobile-menu');
  if (!btn || !menu) return;
  btn.addEventListener('click', () => {
    btn.classList.toggle('open');
    menu.classList.toggle('open');
    document.body.style.overflow = menu.classList.contains('open') ? 'hidden' : '';
  });
  document.addEventListener('click', e => {
    if (!btn.contains(e.target) && !menu.contains(e.target)) {
      btn.classList.remove('open');
      menu.classList.remove('open');
      document.body.style.overflow = '';
    }
  });
}

// ─── Search ─────────────────────────────────────────────────────
function initSearch() {
  const openBtn = document.getElementById('search-open');
  const closeBtn = document.getElementById('search-close');
  const wrap = document.getElementById('search-wrap');
  const input = document.getElementById('search-input');
  const dropdown = document.getElementById('search-dropdown');
  if (!openBtn) return;

  let debounceTimer;

  openBtn.addEventListener('click', () => {
    wrap.classList.add('active');
    input?.focus();
  });
  closeBtn?.addEventListener('click', () => {
    wrap.classList.remove('active');
    dropdown.classList.remove('active');
    if (input) input.value = '';
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      wrap.classList.remove('active');
      dropdown.classList.remove('active');
      if (input) input.value = '';
    }
  });

  if (!input || !dropdown) return;
  input.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const q = input.value.trim();
    if (q.length < 2) { dropdown.classList.remove('active'); return; }
    debounceTimer = setTimeout(() => doSearch(q), 280);
  });

  async function doSearch(q) {
    try {
      const res = await fetch(`/search?q=${encodeURIComponent(q)}`);
      const data = await res.json();
      renderSearchResults(data);
    } catch (err) {
      console.error('Search error:', err);
    }
  }

  function renderSearchResults(results) {
    if (!results.length) {
      dropdown.innerHTML = '<p class="search-no-results">No results found.</p>';
      dropdown.classList.add('active');
      return;
    }
    dropdown.innerHTML = results.map(r => `
      <a href="${r.url}" class="search-result-item">
        <img class="search-result-img"
             src="${r.image && !r.image.startsWith('placeholder') ? '/static/uploads/products/' + r.image : ''}"
             alt="${r.name}"
             onerror="this.style.background='var(--black-mid)';this.removeAttribute('src')">
        <div>
          <div class="search-result-cat">${r.category || ''}</div>
          <div class="search-result-name">${r.name}</div>
          <div class="search-result-price">${formatINR(r.price)}</div>
        </div>
      </a>
    `).join('');
    dropdown.classList.add('active');
  }
}

// ─── Cart counter update ───────────────────────────────────────
function updateCartBadge(count) {
  document.querySelectorAll('.cart-badge').forEach(el => {
    el.textContent = count;
    el.style.display = count > 0 ? 'flex' : 'none';
  });
}

// ─── Add to Cart ─────────────────────────────────────────────
function initAddToCart() {
  document.querySelectorAll('.add-to-cart-btn').forEach(btn => {
    btn.addEventListener('click', async function () {
      const productId = this.dataset.productId;
      const qtyEl = document.getElementById('qty-display');
      const quantity = qtyEl ? parseInt(qtyEl.textContent) : 1;

      this.disabled = true;
      const orig = this.innerHTML;
      this.innerHTML = '<span class="spinner"></span>';

      try {
        const res = await fetch('/cart/add', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ product_id: productId, quantity })
        });
        const data = await res.json();
        if (data.success) {
          Toast.show(data.message || 'Added to cart!', 'success');
          updateCartBadge(data.cart_count);
        } else {
          Toast.show(data.message || 'Failed to add to cart.', 'error');
        }
      } catch {
        Toast.show('Network error. Please try again.', 'error');
      } finally {
        this.innerHTML = orig;
        this.disabled = false;
      }
    });
  });
}

// ─── Quantity selector ─────────────────────────────────────────
function initQtySelector() {
  const display = document.getElementById('qty-display');
  const decreBtn = document.getElementById('qty-decr');
  const increBtn = document.getElementById('qty-incr');
  if (!display) return;

  decreBtn?.addEventListener('click', () => {
    const v = parseInt(display.textContent);
    if (v > 1) display.textContent = v - 1;
  });
  increBtn?.addEventListener('click', () => {
    const v = parseInt(display.textContent);
    const max = parseInt(display.dataset.max || 99);
    if (v < max) display.textContent = v + 1;
  });
}

// ─── Product Gallery ──────────────────────────────────────────
function initGallery() {
  const mainImg = document.getElementById('gallery-main-img');
  const thumbs = document.querySelectorAll('.gallery-thumb');
  if (!mainImg || !thumbs.length) return;
  thumbs.forEach(thumb => {
    thumb.addEventListener('click', function () {
      const src = this.dataset.src;
      mainImg.style.opacity = '0';
      setTimeout(() => {
        mainImg.src = src;
        mainImg.style.opacity = '1';
      }, 200);
      thumbs.forEach(t => t.classList.remove('active'));
      this.classList.add('active');
    });
  });
  mainImg.style.transition = 'opacity .2s ease';
}

// ─── Cart Page AJAX ────────────────────────────────────────────
function initCart() {
  // Update quantity
  document.querySelectorAll('.cart-qty-btn').forEach(btn => {
    btn.addEventListener('click', async function () {
      const cartId = this.dataset.cartId;
      const action = this.dataset.action;
      const display = document.getElementById(`qty-${cartId}`);
      let qty = parseInt(display.textContent);
      qty = action === 'inc' ? qty + 1 : qty - 1;
      if (qty < 1) return;

      this.disabled = true;
      try {
        const res = await fetch('/cart/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ cart_id: cartId, quantity: qty })
        });
        const data = await res.json();
        if (data.success) {
          display.textContent = qty;
          updateCartBadge(data.cart_count);
          const itemTotal = document.getElementById(`item-total-${cartId}`);
          if (itemTotal) itemTotal.textContent = formatINR(data.item_total);
          updateCartSummary(data.subtotal, data.shipping, data.total);
        } else {
          Toast.show(data.message || 'Could not update quantity.', 'error');
        }
      } catch {
        Toast.show('Network error.', 'error');
      } finally {
        this.disabled = false;
      }
    });
  });

  // Remove item
  document.querySelectorAll('.cart-remove').forEach(link => {
    link.addEventListener('click', async function (e) {
      e.preventDefault();
      const cartId = this.dataset.cartId;
      const row = document.getElementById(`cart-row-${cartId}`);
      if (!confirm('Remove this item from cart?')) return;
      try {
        const res = await fetch('/cart/remove', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ cart_id: cartId })
        });
        const data = await res.json();
        if (data.success) {
          row.style.opacity = '0';
          row.style.transform = 'translateX(-20px)';
          row.style.transition = 'all .3s ease';
          setTimeout(() => {
            row.remove();
            updateCartBadge(data.cart_count);
            updateCartSummary(data.subtotal, data.shipping, data.total);
            if (data.cart_count === 0) location.reload();
          }, 300);
        }
      } catch {
        Toast.show('Network error.', 'error');
      }
    });
  });
}

function updateCartSummary(subtotal, shipping, total) {
  const sub = document.getElementById('cart-subtotal');
  const shi = document.getElementById('cart-shipping');
  const tot = document.getElementById('cart-total');
  if (sub) sub.textContent = formatINR(subtotal);
  if (shi) shi.textContent = shipping === 0 ? 'FREE' : formatINR(shipping);
  if (tot) tot.textContent = formatINR(total);
}

// ─── Wishlist Toggle ──────────────────────────────────────────
function initWishlist() {
  document.querySelectorAll('.wishlist-btn').forEach(btn => {
    btn.addEventListener('click', async function (e) {
      e.preventDefault();
      e.stopPropagation();
      const productId = this.dataset.productId;
      try {
        const res = await fetch('/wishlist/toggle', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ product_id: productId })
        });
        const data = await res.json();
        if (data.success) {
          this.classList.toggle('active', data.in_wishlist);
          this.innerHTML = data.in_wishlist ? '♥' : '♡';
          Toast.show(data.in_wishlist ? 'Added to wishlist!' : 'Removed from wishlist', 'info');
        }
      } catch {
        Toast.show('Please login to use wishlist.', 'error');
      }
    });
  });
}

// ─── Shop Filters ─────────────────────────────────────────────
function initShopFilters() {
  document.querySelectorAll('.filter-option').forEach(opt => {
    opt.addEventListener('click', function () {
      const filterType = this.dataset.filterType;
      document.querySelectorAll(`[data-filter-type="${filterType}"]`).forEach(o => o.classList.remove('active'));
      this.classList.add('active');
    });
  });

  const priceForm = document.getElementById('price-filter-form');
  if (priceForm) {
    priceForm.addEventListener('submit', function (e) {
      e.preventDefault();
      const min = document.getElementById('min-price').value;
      const max = document.getElementById('max-price').value;
      const url = new URL(window.location.href);
      if (min) url.searchParams.set('min_price', min);
      else url.searchParams.delete('min_price');
      if (max) url.searchParams.set('max_price', max);
      else url.searchParams.delete('max_price');
      url.searchParams.delete('page');
      window.location.href = url.toString();
    });
  }
}

// ─── Admin: Image delete ───────────────────────────────────────
function initAdminImageDelete() {
  document.querySelectorAll('.delete-image-btn').forEach(btn => {
    btn.addEventListener('click', async function () {
      if (!confirm('Delete this image?')) return;
      const imageId = this.dataset.imageId;
      const wrap = this.closest('.image-preview-wrap');
      try {
        const res = await fetch(`/admin/products/image/delete/${imageId}`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          wrap.remove();
          Toast.show('Image deleted.', 'info');
        }
      } catch {
        Toast.show('Failed to delete image.', 'error');
      }
    });
  });
}

// ─── Image preview on upload ──────────────────────────────────
function initImagePreview() {
  const input = document.getElementById('image-upload');
  const preview = document.getElementById('image-preview');
  if (!input || !preview) return;

  input.addEventListener('change', function () {
    preview.innerHTML = '';
    Array.from(this.files).forEach((file, i) => {
      if (!file.type.startsWith('image/')) return;
      const reader = new FileReader();
      reader.onload = e => {
        const wrap = document.createElement('div');
        wrap.className = 'image-preview-wrap';
        wrap.innerHTML = `
          <img src="${e.target.result}" alt="Preview ${i+1}" style="width:80px;height:80px;object-fit:cover;border-radius:4px;border:1px solid rgba(201,168,76,.3);">
          <span class="text-xs text-dim" style="display:block;margin-top:.25rem">${file.name.slice(0,16)}...</span>
        `;
        preview.appendChild(wrap);
      };
      reader.readAsDataURL(file);
    });
  });
}

// ─── Smooth anchor scroll ─────────────────────────────────────
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', function (e) {
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        const offset = 96;
        window.scrollTo({ top: target.offsetTop - offset, behavior: 'smooth' });
      }
    });
  });
}

// ─── Sort select redirect ─────────────────────────────────────
function initSortSelect() {
  const sel = document.getElementById('sort-select');
  if (!sel) return;
  sel.addEventListener('change', function () {
    const url = new URL(window.location.href);
    url.searchParams.set('sort', this.value);
    url.searchParams.delete('page');
    window.location.href = url.toString();
  });
}

// ─── Utility ──────────────────────────────────────────────────
function formatINR(amount) {
  return '₹' + parseFloat(amount).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// ─── Init All ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  Toast.init();
  initFlash();
  initHeader();
  initMobileMenu();
  initSearch();
  initAddToCart();
  initQtySelector();
  initGallery();
  initCart();
  initWishlist();
  initShopFilters();
  initAdminImageDelete();
  initImagePreview();
  initSmoothScroll();
  initSortSelect();
});
