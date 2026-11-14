# Entwicklungsprozess

## Branch-Modell

```
feature/*, fix/*  ──PR (squash)──▶  dev  ──PR (merge)──▶  test  ──PR (merge)──▶  main  ──Tag vX.Y.Z──▶  Release
```

| Branch | Zweck | Zulässige Quelle für PRs | Merge-Methode |
| --- | --- | --- | --- |
| `dev` | Integrationsstand der Entwicklung (Default-Branch) | `feature/*`, `fix/*`, `chore/*`, `docs/*` | Squash |
| `test` | Abnahme / fachlicher Test | ausschließlich `dev` | Merge-Commit |
| `main` | Produktiver Stand, Basis für Releases | ausschließlich `test` | Merge-Commit |

Alle drei Branches sind über GitHub-Rulesets geschützt:

- Kein direkter Push – Änderungen nur per Pull Request
- Kein Force-Push, kein Löschen
- Pflicht-Checks: `backend`, `frontend`, `promotion-path`
- Keine Ausnahme (Bypass) – auch nicht für Administratoren

Der Check `promotion-path` (Workflow `promotion-guard.yml`) erzwingt den Weg
`dev → test → main`. Ein PR nach `test` aus einem anderen Branch als `dev`
schlägt fehl, ebenso ein PR nach `main` aus einem anderen Branch als `test`.

### Warum Squash nach `dev`, aber Merge-Commits nach `test`/`main`?

Feature-Branches werden zu einem sauberen Commit pro Änderung zusammengefasst.
Bei der Promotion `dev → test → main` würde Squash dagegen die Historien
auseinanderlaufen lassen (gleicher Inhalt, andere Commits) und bei jeder
weiteren Promotion Scheinkonflikte erzeugen. Merge-Commits halten die
Historien kompatibel.

## Typischer Ablauf

```bash
git switch dev && git pull
git switch -c feature/einlagerung-mehrfach
# … entwickeln, testen, committen …
git push -u origin feature/einlagerung-mehrfach
gh pr create --base dev
# nach grünen Checks: Squash-Merge, Branch löschen

# Promotion zur Abnahme
gh pr create --base test --head dev --title "Promotion: dev → test"
# Promotion in Produktion
gh pr create --base main --head test --title "Promotion: test → main"
```

## Releases

Releases entstehen ausschließlich aus `main` über ein Tag nach
[Semantic Versioning](https://semver.org/lang/de/):

```bash
gh release create v0.1.0 --target main --generate-notes
```

Der Workflow `release.yml` baut daraufhin die Container-Images und
veröffentlicht sie in der GitHub Container Registry (`ghcr.io`). Er bricht ab,
wenn das Tag nicht auf einen Commit in `main` zeigt.

## Commit-Konventionen

[Conventional Commits](https://www.conventionalcommits.org/de/) werden empfohlen
(`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`), damit die
automatisch erzeugten Release-Notes lesbar bleiben.

## Hotfixes

Auch Hotfixes gehen den regulären Weg `fix/* → dev → test → main`. Das hält alle
drei Branches konsistent und vermeidet Rück-Merges.
