import "./ipp-printer-editor.js";

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

customElements.define("ipp-printer-card", IPPPrinterCard);

