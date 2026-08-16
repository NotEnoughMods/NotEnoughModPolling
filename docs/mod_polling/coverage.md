# Polling coverage policy

This policy defines when a Not Enough Mods entry should receive, retain, or lose an automated poller.

## Coverage requirements

Minecraft 1.20 and newer is mandatory coverage. Every published NEM entry in that range must map by primary name or alias
to exactly one active polling entry. A mapped poller must also return data for every Minecraft version its configured source
claims to support.

Minecraft versions older than 1.20 are maintained selectively. Missing legacy entries are a backlog, not an instruction to
add every historical mod.

## Adding a legacy poller

Add a legacy poller only when all of these are true:

- An authoritative or project-controlled source exposes the target Minecraft version.
- The source is machine-readable or has stable structure already supported by a parser.
- The Minecraft and mod versions can be extracted deterministically.
- The entry does not duplicate an active poller under another NEM name or alias.
- The upstream project has activity within the five-year retention window, or a maintained successor publishes compatible
  releases.
- The source and filename contracts can be covered by deterministic tests.

Prioritize qualifying candidates in this order:

1. Libraries referenced as dependencies by the most NEM entries.
2. Mods missing from more than one maintained legacy list.
3. Projects with a working CurseForge/API source.
4. Foundational libraries before leaf mods.

Add legacy pollers in reviewed batches. Each batch must record its target NEM lists, source evidence, expected versions, and
maintenance cost.

## Retaining or removing a poller

Measure staleness from upstream project activity, not only from the configured polling feed. A frozen feed can indicate a
source migration rather than an abandoned project.

Remove a poller when all of these are true:

- The upstream project and any maintained successor have had no release or repository activity for at least five years.
- No supported modern NEM list still requires the entry.
- The configured source is dead or permanently frozen.
- The removal date and evidence are recorded in the commit message.

If upstream remains active but the configured feed is stale, migrate the poller to the current authoritative source instead
of removing it.

## Audit procedure

1. Fetch every published NEM list in scope.
2. Match entries through primary names and aliases; reject ambiguous mappings.
3. Poll every active source and compare returned Minecraft-version channels with NEM.
4. Classify each gap as a missing poller, source omission, regex rejection, release-channel omission, or invalid NEM record.
5. Fix parser and source defects before considering new legacy pollers.
6. Re-run the name, source-version, and collision checks after every batch.

## Initial deferred legacy batch

These candidates have the highest observed inbound NEM dependency counts. They remain deferred until a separate batch
validates their sources against this policy.

| Mod | NEM lists | Dependency references | Known source hint |
|---|---|---:|---|
| K4Lib | 1.7.10, 1.12.2 | 8 | CurseForge |
| LunatriusCore | 1.7.10, 1.12.2 | 8 | Repository |
| Baubles | 1.7.10, 1.12.2 | 6 | None recorded |
| D3Core | 1.7.10, 1.12.2 | 6 | None recorded |
| BDLib | 1.7.10, 1.12.2 | 5 | CurseForge |
| ElecCore | 1.7.10, 1.12.2 | 5 | CurseForge |
| MrTJPCore | 1.7.10, 1.12.2 | 5 | None recorded |
| IvToolkit | 1.7.10, 1.12.2 | 4 | None recorded |
| NotEnoughItems | 1.7.10, 1.12.2 | 4 | None recorded |
| RFTools | 1.7.10, 1.12.2 | 3 | CurseForge |
