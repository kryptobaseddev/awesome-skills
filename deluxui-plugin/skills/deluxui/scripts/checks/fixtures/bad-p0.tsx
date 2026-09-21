"use client";
import { useEffect, useState } from "react";
import { generateText } from "ai";

export function Checkout({ password, apiKey, plan }) {
  const [ok, setOk] = useState(false);
  useEffect(() => { Notification.requestPermission(); }, []);
  useEffect(() => {
    localStorage.setItem("draft-compose", JSON.stringify({ body: "" }));
  }, []);
  const pay = async () => {
    console.log("charging", password, apiKey);
    fetch("/api/charge", { method: "POST", body: JSON.stringify({ plan }) });
    setOk(true);
  };
  const save = () => fetch(`/api/u?token=${apiKey}&email=${plan.email}`, { method: "PUT" });
  const retry = () => fetch("/api/charge", { method: "POST" });
  const gen = () => generateText({ prompt: "write it" });
  return (
    <div>
      <p>Trusted by 12,000+ customers — 99.9% uptime</p>
      <input type="checkbox" defaultChecked name="marketing-consent" /> Send me offers
      <input type="text" name="password" onChange={() => password.toLowerCase()} />
      <button onClick={pay}>Pay now</button>
      <button onClick={retry}>Retry</button>
      <button onClick={save}>Save</button>
      <button onClick={gen}>Draft</button>
      {ok && <p>Saved</p>}
    </div>
  );
}
