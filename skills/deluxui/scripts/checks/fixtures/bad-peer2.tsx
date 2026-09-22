// S-STATE-DUPE: a real unguarded mutation. Nothing here stops a second activation.
import { useMutation } from "@tanstack/react-query";

export function UnguardedSubmit() {
  const send = useMutation({ mutationFn: (v) => fetch("/api/jobs", { method: "POST", body: v }) });
  return <button type="button" onClick={() => send.mutate({})}>Submit job</button>;
}
