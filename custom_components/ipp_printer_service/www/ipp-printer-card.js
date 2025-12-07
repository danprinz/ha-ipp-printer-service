class IPPPrinterCard extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (!this.content) {
      this.innerHTML = `
        <ha-card header="IPP Printer">
          <div class="card-content">
            <input type="file" id="file-upload" accept=".pdf" style="display: block; margin-bottom: 16px;" />
            <mwc-button id="print-btn" raised>Print PDF</mwc-button>
            <div id="status" style="margin-top: 16px;"></div>
          </div>
        </ha-card>
      `;
      this.content = this.querySelector(".card-content");
      this.querySelector("#print-btn").addEventListener("click", this._printFile.bind(this));
    }
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("You need to define an entity");
    }
    this.config = config;
  }

  async _printFile() {
    const fileInput = this.querySelector("#file-upload");
    const statusDiv = this.querySelector("#status");
    const file = fileInput.files[0];

    if (!file) {
      statusDiv.innerText = "Please select a PDF file.";
      return;
    }

    statusDiv.innerText = "Uploading...";

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("/api/ipp_printer_service/upload", {
        method: "POST",
        body: formData,
        headers: {
          "Authorization": `Bearer ${this._hass.auth.data.access_token}`
        }
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const data = await response.json();
      const filePath = data.file_path;

      statusDiv.innerText = "Printing...";

      await this._hass.callService("ipp_printer_service", "print_pdf", {
        entity_id: this.config.entity,
        file_path: filePath
      });

      statusDiv.innerText = "Print job sent successfully!";
      fileInput.value = ""; // Clear input

    } catch (error) {
      statusDiv.innerText = `Error: ${error.message}`;
      console.error(error);
    }
  }

  getCardSize() {
    return 3;
  }

  static getConfigElement() {
    return document.createElement("ipp-printer-card-editor");
  }

  static getStubConfig() {
    return { entity: "" };
  }
}

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

customElements.define("ipp-printer-card", IPPPrinterCard);

if (!customElements.get("ipp-printer-card-editor")) {
  customElements.define("ipp-printer-card-editor", IPPPrinterCardEditor);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "ipp-printer-card",
  name: "IPP Printer Card",
  preview: true,
  description: "A card to upload and print PDF files via IPP",
});
