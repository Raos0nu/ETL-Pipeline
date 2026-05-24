import React, { useState, useCallback } from 'react';
import './AddDataForm.css';

// ── Validation rules ──────────────────────────────────────────────────────────
const validators = {
  order_id: (v) => {
    const n = Number(v);
    if (v === '' || v === null || v === undefined) return 'Order ID is required';
    if (!Number.isInteger(n) || n <= 0) return 'Must be a positive integer';
    if (n > 9_999_999) return 'Maximum value is 9,999,999';
    return null;
  },
  product: (v) => {
    if (!v?.trim()) return 'Product name is required';
    if (v.trim().length < 2) return 'Minimum 2 characters';
    if (v.trim().length > 200) return 'Maximum 200 characters';
    return null;
  },
  quantity: (v) => {
    const n = Number(v);
    if (v === '' || v === null || v === undefined) return 'Quantity is required';
    if (!Number.isInteger(n) || n <= 0) return 'Must be a positive integer';
    if (n > 999_999) return 'Maximum value is 999,999';
    return null;
  },
  price: (v) => {
    const n = Number(v);
    if (v === '' || v === null || v === undefined) return 'Price is required';
    if (isNaN(n) || n <= 0) return 'Must be a positive number';
    if (n > 9_999_999) return 'Maximum value is 9,999,999';
    return null;
  },
};

const INITIAL = { order_id: '', product: '', quantity: '', price: '' };

// ── Field component ───────────────────────────────────────────────────────────
function Field({ id, label, type = 'text', value, error, touched, hint, maxLength, onChange, onBlur, placeholder, prefix }) {
  const hasError = touched && !!error;
  const isValid  = touched && !error && value !== '';

  return (
    <div className={`field ${hasError ? 'field-error' : isValid ? 'field-valid' : ''}`}>
      <label className="field-label" htmlFor={id}>
        {label} <span className="field-required">*</span>
      </label>
      <div className="field-input-wrap">
        {prefix && <span className="field-prefix">{prefix}</span>}
        <input
          id={id}
          type={type}
          className={`input field-input ${prefix ? 'has-prefix' : ''}`}
          value={value}
          placeholder={placeholder}
          maxLength={maxLength}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          step={type === 'number' ? '0.01' : undefined}
          min={type === 'number' ? '1' : undefined}
          aria-describedby={hasError ? `${id}-error` : undefined}
          aria-invalid={hasError ? 'true' : 'false'}
        />
        {(hasError || isValid) && (
          <span className={`field-status-icon ${hasError ? 'err' : 'ok'}`}>
            {hasError ? '✕' : '✓'}
          </span>
        )}
      </div>
      {hasError && <p className="field-error-msg" id={`${id}-error`} role="alert">{error}</p>}
      {hint && !hasError && <p className="field-hint">{hint}</p>}
      {maxLength && <p className="field-counter">{(value || '').length}/{maxLength}</p>}
    </div>
  );
}

// ── Live preview ──────────────────────────────────────────────────────────────
function OrderPreview({ values }) {
  const qty   = Number(values.quantity) || 0;
  const price = Number(values.price)    || 0;
  const total = (qty * price).toFixed(2);
  const fmtUSD = (n) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n);

  return (
    <div className="order-preview card">
      <div className="preview-header">Live Preview</div>
      <div className="preview-rows">
        {[
          { k: 'Order ID', v: values.order_id || '—' },
          { k: 'Product',  v: values.product.trim() || '—' },
          { k: 'Qty × Price', v: qty > 0 && price > 0 ? `${qty} × ${fmtUSD(price)}` : '—' },
        ].map(({ k, v }) => (
          <div className="preview-row" key={k}>
            <span className="preview-key">{k}</span>
            <span className="preview-val">{v}</span>
          </div>
        ))}
        <div className="preview-divider" />
        <div className="preview-row preview-total-row">
          <span className="preview-key">Total</span>
          <span className="preview-total-val">
            {qty > 0 && price > 0 ? fmtUSD(total) : '—'}
          </span>
        </div>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function AddDataForm({ onAdd }) {
  const [values,     setValues]     = useState(INITIAL);
  const [touched,    setTouched]    = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [success,    setSuccess]    = useState(false);

  const errors = Object.fromEntries(
    Object.entries(validators).map(([k, fn]) => [k, fn(values[k])])
  );
  const isFormValid = Object.values(errors).every((e) => e === null);

  const handleChange = useCallback((field) => (val) => {
    setValues((v) => ({ ...v, [field]: val }));
    setSuccess(false);
  }, []);

  const handleBlur = useCallback((field) => () => {
    setTouched((t) => ({ ...t, [field]: true }));
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setTouched({ order_id: true, product: true, quantity: true, price: true });
    if (!isFormValid) return;

    setSubmitting(true);
    try {
      const ok = await onAdd({
        order_id: Number(values.order_id),
        product:  values.product.trim(),
        quantity: Number(values.quantity),
        price:    parseFloat(Number(values.price).toFixed(2)),
      });
      if (ok) {
        setSuccess(true);
        setValues(INITIAL);
        setTouched({});
        setTimeout(() => setSuccess(false), 4500);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="add-form-page animate-slide-up">
      <div className="section-header">
        <div>
          <h1 className="section-title">Add Record</h1>
          <p className="section-subtitle">Create a new sales entry in the pipeline</p>
        </div>
      </div>

      <div className="add-form-layout">
        {/* ── Form card ── */}
        <div className="card add-form-card">
          {success && (
            <div className="success-banner" role="status">
              <span>✓</span> Record created successfully! Pipeline data has been updated.
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            <div className="form-grid">
              <Field id="order_id" label="Order ID" type="number"
                value={values.order_id} error={errors.order_id} touched={touched.order_id}
                hint="Unique positive integer identifier" placeholder="e.g. 1042"
                onChange={handleChange('order_id')} onBlur={handleBlur('order_id')} />

              <Field id="product" label="Product Name"
                value={values.product} error={errors.product} touched={touched.product}
                hint="Name of the product or SKU" placeholder="e.g. Wireless Headphones"
                maxLength={200}
                onChange={handleChange('product')} onBlur={handleBlur('product')} />

              <Field id="quantity" label="Quantity" type="number"
                value={values.quantity} error={errors.quantity} touched={touched.quantity}
                hint="Units sold (1 – 999,999)" placeholder="e.g. 5"
                onChange={handleChange('quantity')} onBlur={handleBlur('quantity')} />

              <Field id="price" label="Unit Price" type="number"
                value={values.price} error={errors.price} touched={touched.price}
                hint="Price per unit in USD" placeholder="e.g. 49.99"
                prefix="$"
                onChange={handleChange('price')} onBlur={handleBlur('price')} />
            </div>

            {/* Validation summary */}
            {Object.keys(touched).length > 0 && !isFormValid && (
              <div className="validation-summary" role="alert">
                {Object.entries(errors)
                  .filter(([k, v]) => v && touched[k])
                  .map(([k, v]) => (
                    <div key={k} className="val-item">
                      <span className="val-dot" /> {v}
                    </div>
                  ))}
              </div>
            )}

            <div className="form-actions">
              <button type="button" className="btn btn-secondary"
                onClick={() => { setValues(INITIAL); setTouched({}); setSuccess(false); }}
                disabled={submitting}>
                ↺ Clear
              </button>
              <button type="submit"
                className={`btn btn-primary ${submitting ? 'loading' : ''}`}
                disabled={submitting}>
                {submitting
                  ? <><span className="spinner" /> Saving…</>
                  : <><span>+</span> Add Record</>}
              </button>
            </div>
          </form>
        </div>

        {/* ── Aside ── */}
        <div className="add-form-aside">
          <OrderPreview values={values} />

          <div className="card tip-card">
            <div className="tip-header">Tips</div>
            <ul className="tip-list">
              <li>Order IDs must be unique positive integers.</li>
              <li>Product names support letters, numbers, and symbols.</li>
              <li>Prices are rounded to 2 decimal places.</li>
              <li>Total is calculated as Qty × Unit Price.</li>
              <li>Use the Import CSV button on the Data Table page to bulk-upload records.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
