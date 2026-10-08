<script>let email = ''; let name = '';</script>
<h1>Settings</h1>
<label><input type="checkbox" /> Email me updates</label>
<input placeholder="Display name" bind:value={name} />
<input placeholder="Email" bind:value={email} />
<button>Save</button>
<button style="color:red;font-size:11px">Delete account</button>
