import { useState } from 'react'
import { Modal } from '../../components/ui/Modal'
import { TextInput } from '../../components/ui/TextInput'
export function CheckoutForm() {
  const [err, setErr] = useState('')
  const submit = (e: any) => { e.preventDefault(); if (!e.target.email.value.includes('@')) setErr('An error occurred') }
  return (
    <form onSubmit={submit} className="space-y-4">
      <TextInput label="First name" name="first" />
      <TextInput label="Last name" name="last" />
      <TextInput label="Email" name="email" />
      <TextInput label="Phone" name="phone" />
      <input name="address1" placeholder="Address" className="border text-[13px]" />
      <input name="address2" placeholder="Address 2" className="border text-[13px]" />
      <input name="city" placeholder="City" />
      <select name="state"><option>CA</option></select>
      <input name="zip" placeholder="Zip" />
      <input name="card" placeholder="Card number" maxLength={16} />
      <input name="exp" placeholder="MM/YY" />
      <input name="cvc" placeholder="CVC" />
      <div className="flex gap-2">
        <button type="submit" className="bg-indigo-600 text-white px-3 py-1 text-[12px]">Submit</button>
        <button type="button" className="bg-purple-600 text-white px-3 py-1 text-[12px]">Cancel</button>
      </div>
      <Modal open={!!err} title="Error" onClose={() => setErr('')}><p>{err}</p></Modal>
    </form>
  )
}
