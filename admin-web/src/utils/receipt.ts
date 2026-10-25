import { Bill, RestaurantSettings } from '@/types/api';
import { settingsAuditApi } from '@/api/settingsAuditApi';

export type PaperWidth = '58' | '80';

const KEY_AUTO = 'hms.receipt.autoPrint';
const KEY_PAPER = 'hms.receipt.paper';

export const receiptPrefs = {
  getAutoPrint(): boolean {
    try {
      return localStorage.getItem(KEY_AUTO) !== '0';
    } catch {
      return true;
    }
  },
  setAutoPrint(on: boolean) {
    try {
      localStorage.setItem(KEY_AUTO, on ? '1' : '0');
    } catch {
      /* storage unavailable */
    }
  },
  getPaper(): PaperWidth {
    try {
      return localStorage.getItem(KEY_PAPER) === '58' ? '58' : '80';
    } catch {
      return '80';
    }
  },
  setPaper(w: PaperWidth) {
    try {
      localStorage.setItem(KEY_PAPER, w);
    } catch {
      /* storage unavailable */
    }
  },
};

const KEY_SETTINGS_CACHE = 'hms.receipt.settingsCache';

let inMemorySettings: RestaurantSettings | null = null;
try {
  const cached = localStorage.getItem(KEY_SETTINGS_CACHE);
  if (cached) {
    inMemorySettings = JSON.parse(cached);
  }
} catch {
  // Ignore storage error
}

let settingsPromise: Promise<RestaurantSettings | null> | null = null;
export const loadSettings = (): Promise<RestaurantSettings | null> => {
  if (inMemorySettings) {
    // Revalidate in background if not already fetching
    if (!settingsPromise) {
      settingsPromise = settingsAuditApi
        .getSettings()
        .then((s) => {
          inMemorySettings = s;
          try {
            localStorage.setItem(KEY_SETTINGS_CACHE, JSON.stringify(s));
          } catch {}
          return s;
        })
        .catch(() => inMemorySettings);
    }
    return Promise.resolve(inMemorySettings);
  }

  if (!settingsPromise) {
    settingsPromise = settingsAuditApi
      .getSettings()
      .then((s) => {
        inMemorySettings = s;
        try {
          localStorage.setItem(KEY_SETTINGS_CACHE, JSON.stringify(s));
        } catch {}
        return s;
      })
      .catch(() => {
        settingsPromise = null;
        return null;
      });
  }
  return settingsPromise;
};

// Eagerly prefetch settings so they are warm in memory before the user clicks Generate Bill
void loadSettings();

const esc = (v: unknown) =>
  String(v ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');

const money = (v: string | number | null | undefined) => {
  const n = Number(v);
  return (Number.isFinite(n) ? n : 0).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
};

const istStamp = (iso: string) =>
  new Date(iso).toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata',
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });

export function buildReceiptHtml(
  bill: Bill,
  settings: RestaurantSettings | null,
  paper: PaperWidth = '80'
): string {
  const widthMm = paper === '58' ? 48 : 72;
  const name = settings?.restaurant_name || 'Restaurant';
  const sym = '₹';
  const items = (bill.line_items || [])
    .map((i) => {
      const variant =
        i.variant_name && i.variant_name.toUpperCase() !== 'STANDARD' ? ` (${i.variant_name})` : '';
      return `<div class="item"><div class="nm">${esc(i.item_name)}${esc(variant)}</div>
        <div class="row"><span>${i.quantity_billed} x ${money(i.unit_price_snapshot)}</span><span>${money(i.line_total)}</span></div></div>`;
    })
    .join('');

  const discount = Number(bill.discount_amount || 0);
  const pays = (bill.payments || []).filter((p) => p.status !== 'FAILED');
  const paidRows = pays
    .map((p) => {
      const cash = p.payment_method === 'CASH';
      const tendered = Number(p.amount_tendered ?? p.amount_paid);
      const change = Number(p.change_returned || 0);
      return `<div class="row"><span>Paid by ${esc(p.payment_method)}</span><span>${money(p.amount_paid)}</span></div>
        ${cash ? `<div class="row"><span>Cash received</span><span>${money(tendered)}</span></div>
        <div class="row"><span>Change returned</span><span>${money(change)}</span></div>` : ''}`;
    })
    .join('');

  return `<!doctype html><html><head><meta charset="utf-8"><title>${esc(bill.bill_number)}</title>
<style>
  @page { size: ${paper}mm auto; margin: 0; }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; background: #fff; }
  body { width: ${widthMm}mm; margin: 0 auto; padding: 3mm 0 6mm; color: #000;
         font-family: Consolas, 'Courier New', monospace; font-size: ${paper === '58' ? 10.5 : 12}px; line-height: 1.35; }
  .c { text-align: center; }
  .b { font-weight: 700; }
  .big { font-size: 1.35em; }
  .row { display: flex; justify-content: space-between; gap: 6px; }
  .hr { border-top: 1px dashed #000; margin: 5px 0; }
  .item { margin-bottom: 3px; }
  .nm { font-weight: 700; word-break: break-word; }
  .tot { font-size: 1.2em; font-weight: 700; }
</style></head><body>
  <div class="c b big">${esc(name)}</div>
  ${settings?.address ? `<div class="c">${esc(settings.address)}</div>` : ''}
  ${settings?.phone ? `<div class="c">Ph: ${esc(settings.phone)}</div>` : ''}
  ${settings?.gstin ? `<div class="c">GSTIN: ${esc(settings.gstin)}</div>` : ''}
  <div class="hr"></div>
  <div class="c b">TAX INVOICE</div>
  <div class="row"><span>Bill</span><span class="b">${esc(bill.bill_number)}</span></div>
  <div class="row"><span>Table</span><span>${esc(bill.table_number ?? '-')}</span></div>
  <div class="row"><span>Date</span><span>${esc(istStamp(bill.generated_at))}</span></div>
  ${bill.generated_by_name ? `<div class="row"><span>Cashier</span><span>${esc(bill.generated_by_name)}</span></div>` : ''}
  <div class="hr"></div>
  <div class="row b"><span>Item</span><span>Amount (${sym})</span></div>
  <div class="hr"></div>
  ${items}
  <div class="hr"></div>
  <div class="row"><span>Subtotal</span><span>${money(bill.subtotal_amount)}</span></div>
  ${discount > 0 ? `<div class="row"><span>Discount</span><span>-${money(discount)}</span></div>` : ''}
  <div class="row"><span>CGST ${Number(bill.cgst_rate_snapshot || 0)}%</span><span>${money(bill.cgst_amount)}</span></div>
  <div class="row"><span>SGST ${Number(bill.sgst_rate_snapshot || 0)}%</span><span>${money(bill.sgst_amount)}</span></div>
  ${Number(bill.service_charge_amount || 0) > 0 ? `<div class="row"><span>Service charge</span><span>${money(bill.service_charge_amount)}</span></div>` : ''}
  <div class="hr"></div>
  <div class="row tot"><span>TOTAL</span><span>${sym}${money(bill.grand_total)}</span></div>
  <div class="hr"></div>
  ${paidRows || '<div class="c b">PAYMENT PENDING</div>'}
  <div class="hr"></div>
  <div class="c">Thank you! Visit again.</div>
</body></html>`;
}

/** Prints through an off-screen iframe without changing the user's active page. */
export async function printReceipt(bill: Bill, paper: PaperWidth = receiptPrefs.getPaper()) {
  const settings = inMemorySettings || (await loadSettings());
  const html = buildReceiptHtml(bill, settings, paper);
  const frame = document.createElement('iframe');
  frame.setAttribute('aria-hidden', 'true');
  // Use 1px with 0.01 opacity off-screen: ensures Chromium's layout compositor paints it immediately
  // without throttle (visibility:hidden or 0x0 can delay layout/onload by 3-5 seconds in Chrome/Edge).
  frame.style.cssText =
    'position:fixed;right:0;bottom:0;width:1px;height:1px;opacity:0.01;pointer-events:none;border:0;';

  let printed = false;
  const cleanup = () => {
    window.setTimeout(() => {
      try {
        frame.remove();
      } catch {}
    }, 1500);
  };

  const doPrint = () => {
    if (printed) return;
    printed = true;
    try {
      const w = frame.contentWindow;
      if (!w) return cleanup();
      w.onafterprint = cleanup;
      w.focus();
      w.print();
      window.setTimeout(cleanup, 60_000);
    } catch {
      cleanup();
    }
  };

  frame.onload = () => {
    // Quick microtask to allow iframe DOM to layout
    window.setTimeout(doPrint, 40);
  };

  // Immediate fallback timer in case the browser does not fire onload for srcdoc
  window.setTimeout(doPrint, 500);

  frame.srcdoc = html;
  document.body.appendChild(frame);
}
