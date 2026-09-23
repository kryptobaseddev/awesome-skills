// An order email. <table> is the only layout primitive every mail client honours,
// colours must be literal (no client resolves a custom property), and there is no
// breakpoint to switch to cards at. From the 5.25.0 field report, where 21 of
// S-RESP-TABLE's 44 matches were templates like this one.
import { Html, Body } from "@react-email/components";

export default function OrderConfirmation({ items }: { items: { id: string }[] }) {
  return (
    <Html>
      <Body style={{ backgroundColor: "#f4f4f5", color: "#18181b" }}>
        <table role="presentation" width="600" cellPadding={0} cellSpacing={0}>
          <tr><td style={{ color: "#3f3f46" }}>Your order has shipped.</td></tr>
        </table>
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead><tr>
              <th>Item</th><th>SKU</th><th>Lot</th><th>Qty</th><th>Unit</th>
              <th>Price</th><th>Tax</th><th>Total</th>
            </tr></thead>
            <tbody>{items.map((i) => <tr key={i.id}><td>{i.id}</td></tr>)}</tbody>
          </table>
        </div>
      </Body>
    </Html>
  );
}
