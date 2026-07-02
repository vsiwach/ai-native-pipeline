# baseten auth
Source: https://docs.baseten.co/reference/cli/baseten/auth

Manage authentication

Log in, log out, and manage Baseten credentials.

Each set of credentials is stored as a named profile. Select a profile per command with `--profile` or the `BASETEN_PROFILE` environment variable, or set the default with `baseten auth switch`. Credentials are stored in the system keyring when available, with a plaintext fallback in the config directory.

## login

```sh theme={"system"}
baseten auth login [OPTIONS]
```

Log in to Baseten through your browser (OAuth device flow) or API key, storing a named profile.

By default, opens a browser for interactive login. Use `--web` to skip prompts (suitable for non-TTY environments). Use `--with-api-key` to provide an API key (reads from stdin, or prompts interactively if TTY).

Browser logins name the profile after your email; API key logins require an explicit `--profile` name. The new profile becomes current unless `--no-switch` is given.

### Options

<ParamField type="BOOL">
  Store credentials in plain text instead of system keyring
</ParamField>

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="BOOL">
  Store the profile without making it the current profile
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="TEXT">
  Baseten remote URL for this profile (default [https://app.baseten.co](https://app.baseten.co))
</ParamField>

<ParamField type="BOOL">
  Use browser login without interactive prompts
</ParamField>

<ParamField type="BOOL">
  Read API key from stdin
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

Browser-based login (OAuth device flow)

```sh theme={"system"}
baseten auth login --web
```

Provide an API key on stdin under a named profile

```sh theme={"system"}
echo $API_KEY | baseten auth login --with-api-key --profile <profile>
```

### Filter output with `--jq`

Print just the new profile name

```sh theme={"system"}
baseten auth login --web --jq '.profile'
```

### Output

**Text mode (`--output text`):** Prints "Logged in as `email` (`workspace`) as profile `profile`" to stdout on success.

**JSON mode (`--output json`):** payload type `cmd.AuthLoginResult`.

## logout

```sh theme={"system"}
baseten auth logout [OPTIONS]
```

Remove a stored profile and its credentials. Defaults to the current profile; pass `--profile` to choose another. For OAuth credentials, also revokes the session.

### Options

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

Log out the current profile

```sh theme={"system"}
baseten auth logout
```

Log out a specific profile

```sh theme={"system"}
baseten auth logout --profile <profile>
```

### Filter output with `--jq`

Print just the logged-out profile name

```sh theme={"system"}
baseten auth logout --jq '.profile'
```

### Output

**Text mode (`--output text`):** Prints "Logged out `profile`" to stdout on success.

**JSON mode (`--output json`):** payload type `cmd.AuthLogoutResult`.

## switch

```sh theme={"system"}
baseten auth switch [OPTIONS]
```

Set the current profile used when no profile is selected with `--profile` or `BASETEN_PROFILE`.

### Options

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

Switch to a specific profile non-interactively

```sh theme={"system"}
baseten auth switch --profile <profile>
```

### Filter output with `--jq`

Print just the new current profile

```sh theme={"system"}
baseten auth switch --profile <profile> --jq '.profile'
```

### Output

**Text mode (`--output text`):** Prints "Switched to `profile`" to stdout on success.

**JSON mode (`--output json`):** payload type `cmd.AuthSwitchResult`.

## status

```sh theme={"system"}
baseten auth status [OPTIONS]
```

Show the resolved authentication state, including the profile, remote, and auth type.

### Options

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

Show the current auth status

```sh theme={"system"}
baseten auth status
```

### Filter output with `--jq`

Print just the auth type

```sh theme={"system"}
baseten auth status --jq '.auth_type'
```

### Output

**Text mode (`--output text`):** Summary of the resolved profile: profile name, remote URL, and auth type.

**JSON mode (`--output json`):** payload type `cmd.AuthStatusResult`.
