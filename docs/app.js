"use strict";

const money = value => value === null || value === undefined ? "Unknown" : new Intl.NumberFormat("en-AU", {style: "currency", currency: "AUD"}).format(value);
const node = (tag, text, className) => { const el = document.createElement(tag); el.textContent = text; if (className) el.className = className; return el; };

function offerLine(offer, rejected) {
  if (!offer) return "No observed offer";
  const reasons = rejected && offer.rejection_reasons.length ? ` — rejected: ${offer.rejection_reasons.join(", ")}` : "";
  return `${money(offer.effective_price_aud)} at ${offer.retailer} (${offer.condition}, ${offer.stock_status})${reasons}`;
}

fetch("data/dashboard.json", {cache: "no-store"}).then(response => {
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}).then(data => {
  const status = document.getElementById("status");
  status.textContent = `Generated ${data.generated_at_utc}; last successful collection: ${data.last_successful_collection_utc || "none"}`;
  const models = document.getElementById("models");
  data.models.forEach(item => {
    const card = node("article", "", "card");
    card.append(node("h2", item.model));
    card.append(node("p", `Lowest qualified: ${offerLine(item.lowest_qualified, false)}`));
    card.append(node("p", `Lowest rejected: ${offerLine(item.lowest_rejected, true)}`));
    card.append(node("p", `Target: ${money(item.threshold.buy_price_aud)} (${item.threshold.approved ? "approved" : "provisional — alerts disabled"})`, item.threshold.approved ? "" : "warning"));
    card.append(node("p", `Score: ${item.score.total ?? "Unknown"}/100; confidence ${(Number(item.score.confidence) * 100).toFixed(0)}%`));
    const facts = Object.entries(item.specifications.facts).map(([key, value]) => `${key}: ${value}`).join(" · ");
    card.append(node("p", facts || "Strict specifications unknown; awaiting cited evidence."));
    const sources = node("ul", "");
    item.specifications.evidence.forEach(evidence => { const li = node("li", ""); const link = node("a", evidence.source_type); link.href = evidence.source_url; link.rel = "noopener noreferrer"; li.append(link, document.createTextNode(` — captured ${evidence.captured_at_utc}`)); sources.append(li); });
    card.append(sources);
    models.append(card);
  });
  const health = document.getElementById("health");
  health.textContent = data.collector_health.length ? data.collector_health.map(item => `${item.retailer}: ${item.status}`).join(" · ") : "No collection run recorded.";
}).catch(error => { document.getElementById("status").textContent = `Dashboard data unavailable: ${error.message}`; });
