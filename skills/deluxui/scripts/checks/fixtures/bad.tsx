import { useState } from "react";
import { Canvas } from "@react-three/fiber";
import Shiny from "shiny-ui-kit";

export function BadPanel({ items, onDeleteThing }) {
  const [q, setQ] = useState("");
  const rows = fetch("/api/rows").then((r) => r.json());
  const handleDeleteThing = () => onDeleteThing();
  return (
    <div className="min-h-screen bg-surface p-[13px]">
      <h1 className="text-2xl">Dashboard 🚀</h1>
      <h3 className="text-xl">Elevate your workflow</h3>
      <div onClick={() => setQ("")} className="cursor-pointer">Reset</div>
      <a href="#" onClick={handleDeleteThing}>Delete</a>
      <div className="fixed bottom-0 left-0 w-full">Bar</div>
      <input placeholder="Email" />
      <input type="text" name="phone" />
      <button className="focus:outline-none h-5 w-5"><svg viewBox="0 0 1 1" /></button>
      <button className="opacity-0 group-hover:opacity-100 animate-pulse">Edit</button>
      <p className="text-faint-400 bg-surface">Subtle</p>
      <img src="/a.png" />
      <span style={{ color: "#3355aa" }}>x</span>
      <table><tbody><tr><td>1</td></tr></tbody></table>
      <div role="dialog" className="fixed inset-0">Confirm</div>
      <Canvas />
      <video src="/v.mp4" controls />
      <p>Something went wrong.</p>
      <ul>{items.map((i) => <li key={i.id} tabIndex={3}>{i.name}</li>)}</ul>
      <Shiny.Chart />
    </div>
  );
}
