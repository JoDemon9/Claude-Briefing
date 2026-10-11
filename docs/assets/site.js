/* Theme preference and keyboard isolation shared by public pages. */
(() => {
 'use strict';
 const root = document.documentElement;
 let theme;
 try { theme = localStorage.getItem('oracle-theme') || localStorage.getItem('oracle-black-label-theme'); } catch (_) {}
 if (!['light','dark'].includes(theme)) theme = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
 function apply(value) {
  root.dataset.theme = value;
  try { localStorage.setItem('oracle-theme', value); } catch (_) {}
  document.querySelectorAll('[data-theme-toggle]').forEach(button => button.setAttribute('aria-pressed', String(value === 'dark')));
 }
 apply(theme);
 document.querySelectorAll('[data-theme-toggle]').forEach(button => button.addEventListener('click', () => apply(root.dataset.theme === 'dark' ? 'light' : 'dark')));
 const overlay = document.getElementById('searchOverlay');
 if (!overlay) return;
 const dialog = overlay.querySelector('[role=dialog]');
 const previous = new Map();
 let opener;
 function controls() { return [...dialog.querySelectorAll('a[href],button,input,[tabindex="0"]')].filter(e => !e.disabled && e.getClientRects().length); }
 function update() {
  if (!overlay.hidden) {
   opener = document.activeElement;
   for (const child of document.body.children) {
    if (child === overlay || child.contains(overlay) || ['SCRIPT','STYLE'].includes(child.tagName)) continue;
    previous.set(child, child.inert); child.inert = true;
   }
   controls()[0]?.focus();
  } else {
   for (const [element, value] of previous) element.inert = value;
   previous.clear();
   (opener?.isConnected ? opener : document.getElementById('searchBtn'))?.focus();
  }
 }
 new MutationObserver(update).observe(overlay, {attributes:true,attributeFilter:['hidden']});
 document.addEventListener('keydown', event => {
  if (overlay.hidden || event.key !== 'Tab') return;
  const items = controls(); if (!items.length) return;
  const index = items.indexOf(document.activeElement);
  if (event.shiftKey && index <= 0) { event.preventDefault(); items.at(-1).focus(); }
  if (!event.shiftKey && (index < 0 || index === items.length-1)) { event.preventDefault(); items[0].focus(); }
 });
 document.addEventListener('focusin', event => { if (!overlay.hidden && !dialog.contains(event.target)) controls()[0]?.focus(); });
})();
