// S-STATE-DUPE: the import names the hook and calls nothing, so it can carry no
// in-flight guard and there is no edit that clears the finding.
import { useMutation } from "@tanstack/react-query";

export function NoSubmitHere() {
  return <p>Nothing is submitted on this screen.</p>;
}
