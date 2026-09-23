// A certificate rendered to PDF. The HTML is a document for paper, not a screen:
// nothing reflows, so neither a scroll box nor a card layout means anything here.
import puppeteer from "puppeteer";

export async function renderCertificate(rows: string[][]) {
  const body = rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("");
  const html = `<div class="overflow-auto"><table class="w-full">
    <thead><tr><th>Sample</th><th>Product</th><th>Target</th><th>Method</th><th>Result</th>
    <th>Limit</th><th>Unit</th><th>Analyst</th><th>Action</th></tr></thead>
    <tbody>${body}</tbody></table></div>`;
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.setContent(html);
  return page.pdf({ format: "A4" });
}
