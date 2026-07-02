# truss auth
Source: https://docs.baseten.co/reference/cli/truss/auth

Manage authentication with Baseten remotes.

```sh theme={"system"}
truss auth [COMMAND] [OPTIONS]
```

The `truss auth` command group manages how the Truss CLI authenticates with a Baseten [remote](#remotes). Use it to log in with an API key or through browser-based OAuth, view the active credential for a remote, and log out.

## Authentication methods

The CLI supports two authentication methods, and a single trussrc can mix both, one per remote.

* **API key**: paste a long-lived [API key](/organization/api-keys). Best for CI/CD, scripts, and any non-interactive context.
* **Browser (OAuth)**: complete an [OAuth 2.0 device flow](https://datatracker.ietf.org/doc/html/rfc8628) by approving the request in your browser. The CLI attempts to open your browser automatically and prints the verification URL and code as a fallback. Best for laptops where you don't want a long-lived secret on disk.

OAuth tokens refresh automatically before each request, so you don't have to re-authenticate while the refresh token is valid.

### Where credentials are stored

Truss stores credentials in your operating system's keyring under the service name `baseten-truss` whenever a usable backend is available (macOS Keychain, GNOME Keyring, and Windows Credential Manager). Keyring storage works for both API keys and OAuth tokens.

If no keyring backend is available (for example, a headless Linux container), Truss falls back to writing the secret inline to `~/.trussrc` and prints a one-line warning. To force the inline path silently, set `BASETEN_TRUSS_AUTH_KEYRING_DISABLED=1`.

<Note>
  On macOS, the first read or write triggers a one-time Keychain prompt. Click **Always Allow** to make subsequent calls silent.
</Note>

Existing plaintext `[remote] api_key = ...` entries in `~/.trussrc` continue to work without changes; there's no auto-migration.

## Remotes

A *remote* is a named entry in `~/.trussrc` that points at a Baseten workspace and stores its credential. The default remote is `baseten`. You can configure additional remotes (for staging environments, multiple workspaces, and so on) and select one with `--remote` on most CLI commands.

`truss auth status` and `truss auth logout` both accept `--remote NAME`. When only one remote is configured, the flag is optional.

***

## login

Log in to a Baseten remote.

```sh theme={"system"}
truss auth login [OPTIONS]
```

With no flags, the command prompts you to choose between pasting an API key and logging in through your browser. In non-interactive contexts, pass `--browser` or `--api-key` explicitly.

`truss login` is an alias and accepts the same flags.

### Options

<ParamField>
  Log in through your browser using the OAuth device flow. Mutually exclusive with `--api-key`.
</ParamField>

<ParamField type="TEXT">
  Authenticate with a Baseten [API key](/organization/api-keys). Mutually exclusive with `--browser`.
</ParamField>

<ParamField type="TEXT">
  Name of the remote to create or update in `~/.trussrc`. Defaults to `baseten`.
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Logging verbosity. `humanfriendly` (default) is pretty-printed; `INFO`, `DEBUG`, `WARNING` produce structured logs.
</ParamField>

<ParamField>
  Disable interactive prompts. Use in CI/automated contexts where stdin isn't a TTY.
</ParamField>

### Examples

Log in interactively and choose a method when prompted:

```bash theme={"system"}
truss auth login
# or with uvx:
uvx truss auth login
```

You should see:

```
💻 Let's add a Baseten remote!
? How would you like to authenticate?
  Paste an API key
> Log in via browser (OAuth)
```

Log in non-interactively with an API key:

```bash theme={"system"}
truss auth login --api-key $BASETEN_API_KEY
# or with uvx:
uvx truss auth login --api-key $BASETEN_API_KEY
```

Log in through your browser:

```bash theme={"system"}
truss auth login --browser
# or with uvx:
uvx truss auth login --browser
```

The CLI opens your browser to the verification page with your user code pre-filled. Approve the request, and the CLI automatically stores the OAuth tokens and prints:

```
🔓 Logged in to remote `baseten`.
```

Add a non-default remote (for example, a staging workspace):

```bash theme={"system"}
truss auth login --browser --remote staging
# or with uvx:
uvx truss auth login --browser --remote staging
```

***

## logout

Log out of a Baseten remote and remove it from `~/.trussrc`. For OAuth remotes, this also revokes the refresh token on the backend.

```sh theme={"system"}
truss auth logout [OPTIONS]
```

### Options

<ParamField type="TEXT">
  Remote name to log out of. Inferred when only one remote is configured.
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Logging verbosity. `humanfriendly` (default) is pretty-printed; `INFO`, `DEBUG`, `WARNING` produce structured logs.
</ParamField>

<ParamField>
  Disable interactive prompts. Use in CI/automated contexts where stdin isn't a TTY.
</ParamField>

### Examples

Log out of the only configured remote:

```sh theme={"system"}
truss auth logout
```

Log out of a specific remote:

```sh theme={"system"}
truss auth logout --remote staging
```

You should see:

```
👋 Logged out of remote `staging`.
```

***

## status

Show the active authentication for a remote: the URL it points at, which method it uses, and where the credential is stored.

```sh theme={"system"}
truss auth status [OPTIONS]
```

### Options

<ParamField type="TEXT">
  Remote name to inspect. Inferred when only one remote is configured.
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Logging verbosity. `humanfriendly` (default) is pretty-printed; `INFO`, `DEBUG`, `WARNING` produce structured logs.
</ParamField>

<ParamField>
  Disable interactive prompts. Use in CI/automated contexts where stdin isn't a TTY.
</ParamField>

### Examples

Inspect a remote:

```sh theme={"system"}
truss auth status --remote baseten
```

You should see:

```
remote: baseten
remote_url: https://app.baseten.co
auth_type: api_key
source: keyring
```

The `source` field is one of:

* `keyring`: the credential is stored in the OS keyring.
* `trussrc-inline`: the credential is stored as plaintext inside `~/.trussrc`.

The `auth_type` field is `api_key`, `oauth`, or `api_key (legacy plaintext)` for entries written by older Truss versions.

***

## Environment variables

<ParamField type="TEXT">
  API key used as a fallback when the active remote has no credentials in `~/.trussrc`. Recommended for CI/CD, where setting the env var avoids running `truss login` before each job.
</ParamField>

<ParamField type="FLAG">
  Set to `1` to skip the OS keyring and write credentials inline to `~/.trussrc` without printing a warning. Useful in containers and headless environments where no keyring backend is available.
</ParamField>
