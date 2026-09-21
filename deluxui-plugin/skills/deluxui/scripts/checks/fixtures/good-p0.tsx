"use client";
import { useState } from "react";

export function Checkout({ plan, user }) {
  const [status, setStatus] = useState<"idle" | "pending" | "done">("idle");
  const [error, setError] = useState<string | null>(null);
  const askNotifications = () => Notification.requestPermission();
  const pay = async () => {
    setStatus("pending");
    const res = await fetch("/api/charge", {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify({ planId: plan.id }),
    });
    if (res.ok) { setStatus("done"); return; }
    setStatus("idle");
    setError("We could not take the payment. Nothing was charged — try again?");
  };
  return (
    <form>
      <p>
        Total {new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" })
          .format(plan.amount)} per month, renews automatically. Cancel any time.
      </p>
      <p>Billing account: {user.workspace}</p>
      <label htmlFor="pw">Password</label>
      <input id="pw" type="password" autoComplete="current-password" />
      <label><input type="checkbox" name="marketing-consent" /> Send me offers</label>
      <button type="button" onClick={askNotifications}>Enable reminders</button>
      <a href="/checkout/review">Review your order before paying</a>
      <button type="submit" onClick={pay} disabled={status === "pending"}>
        Pay now
      </button>
      {error && <p role="alert">{error}</p>}
      {status === "done" && <p role="status">Payment confirmed</p>}
    </form>
  );
}
