import { Button } from '../../components/ui/Button'
export function AccountSettings() {
  return (
    <div className="p-6">
      <h1>Settings</h1>
      <label><input type="checkbox" /> Email me deals</label>
      <label><input type="checkbox" /> Dark mode</label>
      <input placeholder="Display name" />
      <input placeholder="Email" />
      <Button onClick={() => {}}>Save</Button>
      <button className="text-red-500 text-[11px]">Delete account</button>
    </div>
  )
}
