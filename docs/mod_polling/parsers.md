# Parsers

Parsers are methods on `ModPoller` that fetch version information for a mod from an external source. Each mod in `mods.json` specifies which parser to use via the `"parser"` key.

## Dispatch

When a mod is polled, `check_mod()` calls:

```python
getattr(self, "check_" + self.mods[mod]["parser"])(mod, document=document)
```

So `"parser": "cfwidget"` dispatches to `check_cfwidget()`, `"parser": "forge_json"` dispatches to `check_forge_json()`, and so on.

## Return formats

Parsers can return either of two dict formats. The **multi-version** format (preferred) maps Minecraft versions to version info:

```python
{
    "1.12.2": {"version": "1.5.0"},
    "1.16.5": {"version": "2.0.0", "dev": "2.1.0-beta"},
}
```

The **legacy** format returns a single version:

```python
{"version": "1.2.3", "mc": "1.12.2"}
# or
{"version": "1.2.3", "dev": "1.3.0-beta", "mc": "1.12.2", "change": "Fixed bug"}
```

Legacy results are automatically converted to multi-version format by `check_mod()`. If a legacy result omits `"mc"`, the mod's top-level `"mc"` key in `mods.json` is used as the default.

## Regex capture groups

Several parsers rely on a regex defined in the mod's `mods.json` entry. The regex is compiled at startup by `compile_regex()`, which searches the mod's data dict recursively for a `"regex"` key.

Common named capture groups:

| Group | Meaning | Used by |
|---|---|---|
| `version` | The mod version string | `jenkins`, `html`, `cfwidget`, `github_release` |
| `mc` | The Minecraft version | `html`, `cfwidget` (optional) |

## Common `mods.json` keys

These keys can appear on any mod entry regardless of parser:

| Key | Type | Description |
|---|---|---|
| `parser` | string | **(required)** Parser name (dispatched as `check_` + name) |
| `active` | boolean | Whether this mod should be polled |
| `name` | string | NEM display name (defaults to the JSON key) |
| `mc` | string | Default Minecraft version (fallback when a legacy parser doesn't return one) |
| `category` | string | Organizational category (e.g. `"forge"`) |
| `changelog` | string | Static changelog URL (suppresses per-poll changelog from parsers) |
| `document_group` | object | See [Document groups](#document-groups) below |

---

## Parser reference

### `cfwidget`

Fetches mod info from the CurseForge CFWidget API.

**Method:** `check_cfwidget`
**Return format:** multi-version

**How it works:**
1. Fetches `https://api.cfwidget.com/{curse.id}` as JSON.
2. Sorts files by ID (descending = newest first).
3. For each file, iterates its `versions` list, skipping non-MC-version strings (e.g. "Forge", "Java 17").
4. Matches the regex against the file's `name` (or `display` if `curse.field` is set).
5. If the regex doesn't match the *latest* file, raises an error (regex is outdated). Older non-matching files are skipped.
6. Release type determines whether the version is stored as `"version"` (release) or `"dev"` (anything else).

**Required keys:**

```json
{
    "parser": "cfwidget",
    "curse": {
        "id": "228756",
        "regex": "ironchest-[0-9.]+-(?:(?:neo)?forge-)?(?P<version>[0-9]+(?:\\.[0-9]+)+)\\.jar"
    }
}
```

| Key | Type | Required | Description |
|---|---|---|---|
| `curse.id` | string | yes | CurseForge project ID |
| `curse.regex` | string | yes | Regex with a `version` group; optionally `mc` |
| `curse.field` | string | no | File field to match against: `"name"` (default) or `"display"` |

**Example with `mc` capture:**

```json
{
    "parser": "cfwidget",
    "curse": {
        "id": "268560",
        "regex": "Mekanism-(?P<mc>.+?)-(?P<version>[0-9]+(?:\\.[0-9]+)+)\\.jar"
    }
}
```

When the regex captures `mc`, that value is used instead of the file's `versions` list for MC version assignment.

---

### `forge_json`

Parses the Forge-style `update.json` format (used by Forge's built-in update checker).

**Method:** `check_forge_json`
**Return format:** multi-version

**How it works:**
1. Fetches the JSON from `forgejson.url`.
2. Iterates the `"promos"` dict. Each key has the format `"<mc_version>-latest"` or `"<mc_version>-recommended"`.
3. `latest` maps to `"dev"`, `recommended` maps to `"version"`.
4. If `dev` equals `version` for a given MC version, `dev` is removed (no point reporting both).
5. Skips the special `"reserved"` promo key.

**Required keys:**

```json
{
    "parser": "forge_json",
    "forgejson": {
        "url": "https://raw.githubusercontent.com/Ferdzz/PlaceableItems/master/update.json"
    }
}
```

| Key | Type | Required | Description |
|---|---|---|---|
| `forgejson.url` | string | yes | URL to the Forge update JSON |

No regex is needed.

---

### `mcforge_v2`

Fetches version info from MinecraftForge's promotions JSON. Has two sub-modes: **slim** and **non-slim**.

**Method:** `check_mcforge_v2`
**Return format:** multi-version (slim) or legacy (non-slim)

#### Slim mode

Parses a promotions_slim.json where promo keys are `"<mc>-latest"` / `"<mc>-recommended"` and values are bare version strings.

```json
{
    "parser": "mcforge_v2",
    "mcforge": {
        "url": "https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json",
        "slim": true
    }
}
```

#### Non-slim mode

Looks up a specific promo key whose value is an object with `"version"` and `"mcversion"` fields. Returns a legacy result.

```json
{
    "parser": "mcforge_v2",
    "mcforge": {
        "url": "https://example.com/forge.json",
        "promo": "recommended",
        "promoType": "version"
    }
}
```

| Key | Type | Required | Description |
|---|---|---|---|
| `mcforge.url` | string | yes | URL to the promotions JSON |
| `mcforge.slim` | boolean | no | `true` for slim mode (default `false`) |
| `mcforge.promo` | string | non-slim only | Promo key to look up (e.g. `"recommended"`) |
| `mcforge.promoType` | string | non-slim only | Version type for the result: `"version"` or `"dev"` |

No regex is needed.

---

### `jenkins`

Fetches the latest build from a Jenkins CI server and extracts the version from an artifact filename.

**Method:** `check_jenkins`
**Return format:** legacy

**How it works:**
1. Fetches `{jenkins.url}?tree=changeSet[items[msg]],artifacts[fileName]` as JSON.
2. Picks the artifact at index `jenkins.item` and gets its `fileName`.
3. Matches the mod's regex against the filename.
4. Returns the regex's named groups plus `"change"` from the first changelog entry (if any).

**Required keys:**

```json
{
    "parser": "jenkins",
    "jenkins": {
        "url": "https://ci.example.com/job/Mod/lastBuild",
        "item": 0
    },
    "curse": {
        "regex": "Mod-(?P<version>[0-9.]+)\\.jar"
    }
}
```

| Key | Type | Required | Description |
|---|---|---|---|
| `jenkins.url` | string | yes | Jenkins build API URL (without query string) |
| `jenkins.item` | integer | yes | Index into the `artifacts` array |
| regex (anywhere) | string | yes | Must capture `version`; may capture `mc` |

Note: the regex can live under any key (here `curse.regex`); `compile_regex()` finds it recursively.

---

### `html`

Scrapes a web page and extracts versions using regex.

**Method:** `check_html`
**Return format:** multi-version

**How it works:**
1. Fetches the page at `html.url` as text.
2. Runs `finditer` with the mod's regex over the full page.
3. For each match, records `mc` -> `version`. By default, the *first* match per MC version wins.
4. If `reverse` is `true`, the *last* match per MC version wins instead.
5. Versions are stored under `"version"` by default, or under `"dev"` if `version_type` is `"dev"`.

**Required keys:**

```json
{
    "parser": "html",
    "html": {
        "url": "https://flansmod.com/download",
        "regex": "(?P<version>[0-9]+(?:\\.[0-9]+)+) for(?: MC)? (?P<mc>[0-9]+(\\.[0-9]+)+)"
    }
}
```

| Key | Type | Required | Description |
|---|---|---|---|
| `html.url` | string | yes | URL to fetch |
| `html.regex` | string | yes | Must capture `version` and `mc` |
| `html.reverse` | boolean | no | `true` to prefer the last match per MC version |
| `html.version_type` | string | no | `"version"` (default) or `"dev"` |

---

### `github_release`

Fetches releases from the GitHub API. Supports two sub-types: **asset** and **tag**.

**Method:** `check_github_release`
**Return format:** legacy

**How it works (asset type):**
1. Fetches `https://api.github.com/repos/{github.repo}/releases`.
2. Iterates releases and their assets. Matches the regex against each asset's `name`.
3. Returns on the first match. Pre-releases store the version under `"dev"` instead of `"version"`.

**How it works (tag type):**
1. Takes the first (newest) release's `tag_name`.
2. If a regex is provided, matches it against the tag. Otherwise uses the raw tag.
3. Pre-releases store the version under `"dev"`.

**Required keys (asset):**

```json
{
    "parser": "github_release",
    "github": {
        "repo": "owner/repo",
        "type": "asset",
        "regex": "GHMod-(?P<version>[0-9.]+)\\.jar"
    }
}
```

**Required keys (tag, no regex):**

```json
{
    "parser": "github_release",
    "github": {
        "repo": "owner/repo",
        "type": "tag"
    }
}
```

| Key | Type | Required | Description |
|---|---|---|---|
| `github.repo` | string | yes | GitHub `owner/repo` |
| `github.type` | string | no | `"asset"` (default) or `"tag"` |
| `github.regex` | string | asset: yes, tag: no | Must capture `version` |

GitHub API authentication (`client_id`/`client_secret`) is read from `config.yml` if present.

---

### `buildcraft`

A hardcoded parser for BuildCraft specifically. Takes no configuration.

**Method:** `check_buildcraft`
**Return format:** legacy

**How it works:**
1. Fetches `https://raw.githubusercontent.com/BuildCraft/BuildCraft/master/buildcraft_resources/versions.txt`.
2. Parses the last non-empty line as `mc:mod_name:version`.
3. Returns `{"mc": mc, "version": version}`.

**Required keys:**

```json
{
    "parser": "buildcraft"
}
```

No additional configuration or regex needed.

---

## Document groups

Document groups let multiple mods share a single HTTP fetch. This is useful when several mods publish their versions on the same page or JSON endpoint.

### How it works

1. At startup, `build_mod_dict()` collects all mods with a `"document_group"` key and groups them by `document_group.id`.
2. When polling, `check_mods()` is called instead of `check_mod()`:
   - It verifies all mods in the group use the same parser.
   - It calls the parser once to fetch the document.
   - It then calls `check_mod()` for each mod in the group, passing the fetched document via the `document` parameter.
3. Each mod's own regex is applied individually to the shared document.

### `mods.json` format

```json
{
    "ModA": {
        "parser": "html",
        "html": {
            "url": "https://example.com/versions",
            "regex": "ModA-(?P<version>[0-9.]+) for (?P<mc>[0-9.]+)"
        },
        "document_group": {
            "id": "example-versions-page"
        }
    },
    "ModB": {
        "parser": "html",
        "html": {
            "url": "https://example.com/versions",
            "regex": "ModB-(?P<version>[0-9.]+) for (?P<mc>[0-9.]+)"
        },
        "document_group": {
            "id": "example-versions-page"
        }
    }
}
```

All mods sharing a `document_group.id` **must** use the same parser. The URL only needs to match on the mod that triggers the initial fetch (in practice they should all have the same URL).
