class NRWRailCard extends HTMLElement {
  set hass(hass) {
    if (!this.content) {
      this.innerHTML = `
        <ha-card header="🚆 NRW Rail Status">
          <div class="card-content" id="nrw-container"></div>
        </ha-card>
      `;
      this.content = this.querySelector("#nrw-container");
    }

    const entityId = this.config.entity || "sensor.nrw_rail_status";
    const stateObj = hass.states[entityId];

    if (!stateObj) {
      this.content.innerHTML = `<ha-alert alert-type="error">Entität ${entityId} nicht gefunden!</ha-alert>`;
      return;
    }

    const messages = stateObj.attributes.messages || [];

    if (messages.length === 0) {
      this.content.innerHTML = `
        <ha-alert alert-type="success">Keine aktuellen Störungen auf deinen ausgewählten Linien.</ha-alert>
      `;
      return;
    }

    let html = `<div style="display: flex; flex-direction: column; gap: 12px;">`;

    messages.forEach((msg) => {
      const lines = msg.products 
        ? msg.products.map(p => `<span class="line-badge">${p.name}</span>`).join(" ") 
        : "";
      
      html += `
        <div class="disruption-item">
          <div class="disruption-header">
            <strong>${msg.title}</strong>
          </div>
          <div class="disruption-lines">${lines}</div>
          <div class="disruption-text">${msg.text || "Keine weiteren Details verfügbar."}</div>
        </div>
      `;
    });

    html += `</div>
      <style>
        .disruption-item {
          border-left: 4px solid var(--warning-color, #ff9800);
          background: var(--card-background-color, #fff);
          padding: 12px;
          border-radius: 0 8px 8px 0;
          box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        }
        .disruption-header {
          font-size: 1em;
          margin-bottom: 6px;
        }
        .disruption-lines {
          margin-bottom: 8px;
        }
        .line-badge {
          background: var(--primary-color, #03a9f4);
          color: white;
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 0.8em;
          font-weight: bold;
          display: inline-block;
          margin-right: 4px;
        }
        .disruption-text {
          font-size: 0.9em;
          color: var(--secondary-text-color, #666);
          white-space: pre-line;
        }
      </style>
    `;

    this.content.innerHTML = html;
  }

  setConfig(config) {
    this.config = config;
  }

  getCardSize() {
    return 3;
  }
}

customElements.define("nrw-rail-card", NRWRailCard);
