class IPPPrinterCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  setConfig(config) {
    this._config = config;
    if (this._hass) this._render();
  }

  configChanged(newConfig) {
    const event = new CustomEvent("config-changed", {
      bubbles: true,
      composed: true,
      detail: { config: newConfig },
    });
    this.dispatchEvent(event);
  }

  set hass(hass) {
    this._hass = hass;
    // Always attempt to update properties if we rendered already
    const selector = this.shadowRoot.querySelector("ha-selector");
    if (selector) {
      selector.hass = this._hass;
    }
  }

  _render() {
    if (!this._config) return;

    if (!this.shadowRoot.querySelector('.card-config')) {
      this.shadowRoot.innerHTML = `
        <style>
          :host {
            display: block;
          }
          .card-config {
            display: block;
          }
          .label {
            margin-bottom: 8px;
            font-weight: bold;
            display: block;
          }
          ha-selector {
            display: block;
            width: 100%;
          }
        </style>
        <div class="card-config">
          <ha-selector
            label="Printer Entity"
          ></ha-selector>
        </div>
      `;
      
      const selector = this.shadowRoot.querySelector("ha-selector");
      selector.addEventListener("value-changed", (ev) => this._valueChanged(ev));
    }
    
    // Update properties
    const selector = this.shadowRoot.querySelector("ha-selector");
    if (selector) {
      if (this._hass) selector.hass = this._hass;
      selector.value = this._config.entity;
      selector.required = true;
      selector.selector = {
        entity: {
          domain: "sensor",
          integration: "ipp_printer_service"
        }
      };
    }
  }

  _valueChanged(ev) {
    if (!this._config || !this._hass) return;
    const value = ev.detail.value;
    if (this._config.entity === value) return;
    
    this._config = {
      ...this._config,
      entity: value,
    };
    this.configChanged(this._config);
  }
}

if (!customElements.get("ipp-printer-card-editor")) {
  customElements.define("ipp-printer-card-editor", IPPPrinterCardEditor);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "ipp-printer-card",
    name: "IPP Printer Card",
    preview: true,
    description: "A card to upload and print PDF files via IPP",
  });
}
